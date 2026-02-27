from datetime import date, datetime
from sqlalchemy import (
    Integer, String, Boolean, Float, Date, DateTime,
    ForeignKey, UniqueConstraint, CheckConstraint, func, Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class IncomeSource(Base):
    __tablename__ = "income_sources"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_source_user_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="income_sources")  # noqa: F821
    records: Mapped[list["IncomeRecord"]] = relationship(
        "IncomeRecord", back_populates="source"
    )


class IncomeRecord(Base):
    __tablename__ = "income_records"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_amount_positive"),
        Index("idx_income_records_user_date", "user_id", "record_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("income_sources.id", ondelete="RESTRICT"), nullable=False,
        index=True,
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    note: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="income_records")  # noqa: F821
    source: Mapped["IncomeSource"] = relationship("IncomeSource", back_populates="records")
