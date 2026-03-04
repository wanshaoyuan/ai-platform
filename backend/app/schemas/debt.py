from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, Field


RepayMethod = Literal["equal_installment", "equal_principal"]
RepayStatus = Literal["pending", "paid", "overdue"]


# ─────────────────────────────── DebtItem ────────────────────────────────────

class DebtItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    principal: float = Field(..., gt=0, description="贷款总额（本金）")
    annual_rate: float = Field(..., gt=0, description="年化利率，如 3.85 表示 3.85%")
    term_months: int = Field(..., gt=0, description="贷款总期数（月）")
    repay_method: RepayMethod = "equal_installment"
    first_repay_date: date = Field(..., description="首期还款日期")
    monthly_repay_day: int = Field(..., ge=1, le=31, description="每月约定还款日")
    note: str | None = Field(None, max_length=256)


class DebtItemUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=64)
    note: str | None = Field(None, max_length=256)
    is_active: bool | None = None


class DebtItemRead(BaseModel):
    id: int
    name: str
    principal: float
    annual_rate: float
    term_months: int
    repay_method: str
    first_repay_date: date
    monthly_repay_day: int
    monthly_payment: float
    current_balance: float
    paid_periods: int
    is_active: bool
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────── RepaymentSchedule ───────────────────────────

class RepaymentScheduleRead(BaseModel):
    id: int
    debt_id: int
    period_no: int
    due_date: date
    payment_amount: float
    principal_amount: float
    interest_amount: float
    remaining_balance: float
    status: str
    paid_at: datetime | None

    model_config = {"from_attributes": True}


# ─────────────────────────────── 统计 ────────────────────────────────────────

class DebtSummary(BaseModel):
    """仪表盘顶部数据卡片所需的汇总数据"""
    total_balance: float        # 所有有效债务的当前剩余本金之和
    monthly_total_payment: float  # 每月总月供（所有有效债务月供之和）
    active_count: int           # 有效债务笔数


class DebtBarItem(BaseModel):
    """柱状图单条数据"""
    name: str
    current_balance: float
    monthly_payment: float
