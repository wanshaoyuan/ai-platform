from datetime import datetime
from sqlalchemy import (
    Integer, String, Float, DateTime, ForeignKey,
    UniqueConstraint, CheckConstraint, Index, func, Boolean,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Account(Base):
    """
    用户自定义账户表。
    每个用户可以创建自己的账户（如银行卡、支付账户等）。
    """
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_account_user_name"),
        Index("idx_accounts_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(32), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="accounts")  # noqa: F821
    monthly_balances: Mapped[list["MonthlyBalance"]] = relationship(
        "MonthlyBalance", back_populates="account", cascade="all, delete-orphan"
    )


class MonthlyBalance(Base):
    """
    月度余额快照表。
    每条记录 = 某用户某月某账户的余额快照。
    同一用户同一月同一账户只允许一条记录（通过唯一约束保证）。
    """
    __tablename__ = "monthly_balances"
    __table_args__ = (
        UniqueConstraint("user_id", "month", "account_id", name="uq_balance_user_month_account"),
        CheckConstraint("balance >= 0", name="ck_balance_non_negative"),
        Index("idx_monthly_balances_user_month", "user_id", "month"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # 月份格式：YYYY-MM，如 "2025-09"
    month: Mapped[str] = mapped_column(String(7), nullable=False)
    # 账户 ID，对应 accounts 表的 id
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    # 账户名称（冗余存储，方便查询展示，即使账户被重命名历史数据仍保留原名）
    account_name: Mapped[str] = mapped_column(String(32), nullable=False)
    balance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="monthly_balances")  # noqa: F821
    account: Mapped["Account"] = relationship("Account", back_populates="monthly_balances")
