from datetime import datetime
from pydantic import BaseModel, Field


# ── 账户 CRUD ──────────────────────────────────────────────────────────────────

class AccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=32)
    sort_order: int = Field(0, ge=0)


class AccountUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=32)
    sort_order: int | None = Field(None, ge=0)


class AccountRead(BaseModel):
    id: int
    name: str
    sort_order: int
    is_active: bool

    model_config = {"from_attributes": True}


# ── 月度余额快照 ───────────────────────────────────────────────────────────────

class BalanceItem(BaseModel):
    """单个账户的余额"""
    account_id: int = Field(..., ge=1)
    balance: float = Field(..., ge=0)


class MonthlyBalanceUpsert(BaseModel):
    """创建/更新某月所有账户余额（批量）"""
    month: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="格式：YYYY-MM")
    balances: list[BalanceItem] = Field(..., min_length=1)


class MonthlyBalanceRead(BaseModel):
    account_id: int
    account_name: str
    balance: float
    updated_at: datetime

    model_config = {"from_attributes": True}


class MonthlySnapshotRead(BaseModel):
    """某月全部账户余额 + 总额"""
    month: str
    total: float
    items: list[MonthlyBalanceRead]


# ── 图表统计 ───────────────────────────────────────────────────────────────────

class TrendPoint(BaseModel):
    """折线图单个数据点"""
    month: str
    value: float


class AccountTrendRead(BaseModel):
    """单个账户的余额趋势"""
    account_id: int
    account_name: str
    data: list[TrendPoint]


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str
