from datetime import date, datetime
from sqlalchemy import (
    Integer, String, Boolean, Float, Date, DateTime,
    ForeignKey, CheckConstraint, Index, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class DebtItem(Base):
    """
    贷款基础配置表。
    每条记录代表一笔贷款（如：商业房贷、公积金房贷、车贷）。
    """
    __tablename__ = "debt_items"
    __table_args__ = (
        CheckConstraint("principal > 0",    name="ck_debt_principal_positive"),
        CheckConstraint("annual_rate > 0",  name="ck_debt_rate_positive"),
        CheckConstraint("term_months > 0",  name="ck_debt_term_positive"),
        CheckConstraint(
            "monthly_repay_day >= 1 AND monthly_repay_day <= 31",
            name="ck_debt_repay_day_range",
        ),
        Index("idx_debt_items_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)

    # 贷款参数
    principal: Mapped[float] = mapped_column(Float, nullable=False, comment="贷款总额（本金）")
    annual_rate: Mapped[float] = mapped_column(Float, nullable=False, comment="年化利率，如 3.85 表示 3.85%")
    term_months: Mapped[int] = mapped_column(Integer, nullable=False, comment="贷款总期数（月）")
    repay_method: Mapped[str] = mapped_column(
        String(32), nullable=False, default="equal_installment",
        comment="还款方式：equal_installment=等额本息 | equal_principal=等额本金"
    )

    # 还款日配置
    first_repay_date: Mapped[date] = mapped_column(Date, nullable=False, comment="首期还款日期")
    monthly_repay_day: Mapped[int] = mapped_column(Integer, nullable=False, comment="每月约定还款日（1-31）")

    # 计算结果（保存时由后端自动填充）
    monthly_payment: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="等额本息时：固定月供金额；等额本金时：首期月供（仅参考）"
    )

    # 实时状态
    current_balance: Mapped[float] = mapped_column(
        Float, nullable=False, comment="当前剩余未还本金，初始等于 principal"
    )
    paid_periods: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="已还期数"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否有效，还清后标记 False"
    )
    note: Mapped[str | None] = mapped_column(String(256), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="debt_items")  # noqa: F821
    schedules: Mapped[list["RepaymentSchedule"]] = relationship(
        "RepaymentSchedule", back_populates="debt", cascade="all, delete-orphan"
    )


class RepaymentSchedule(Base):
    """
    还款计划表。
    记录每笔贷款每期的应还金额、本金/利息拆分，以及还款状态。
    方案 A（全自动）：定时任务每天运行，将 due_date = today 且 status = pending 的账单
    自动标记为 paid，并在 DebtItem.current_balance 中扣减对应本金部分。
    """
    __tablename__ = "repayment_schedules"
    __table_args__ = (
        Index("idx_repay_schedule_debt_id", "debt_id"),
        Index("idx_repay_schedule_due_date_status", "due_date", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    debt_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("debt_items.id", ondelete="CASCADE"), nullable=False
    )
    period_no: Mapped[int] = mapped_column(Integer, nullable=False, comment="期数，从 1 开始")
    due_date: Mapped[date] = mapped_column(Date, nullable=False, comment="本期约定还款日期")

    # 金额拆分
    payment_amount: Mapped[float] = mapped_column(Float, nullable=False, comment="本期月供总额（本金+利息）")
    principal_amount: Mapped[float] = mapped_column(Float, nullable=False, comment="本期归还本金")
    interest_amount: Mapped[float] = mapped_column(Float, nullable=False, comment="本期归还利息")
    remaining_balance: Mapped[float] = mapped_column(Float, nullable=False, comment="还完本期后的剩余本金")

    # 状态流转：pending → paid / overdue
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending",
        comment="pending=待还 | paid=已还 | overdue=逾期"
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="自动扣减完成的时间戳"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    debt: Mapped["DebtItem"] = relationship("DebtItem", back_populates="schedules")
