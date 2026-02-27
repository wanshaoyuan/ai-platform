from datetime import date, datetime
from pydantic import BaseModel, Field


# ---------- IncomeSource ----------

class IncomeSourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    icon: str | None = None
    sort_order: int = 0


class IncomeSourceUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=64)
    icon: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class IncomeSourceRead(BaseModel):
    id: int
    name: str
    icon: str | None
    is_active: bool
    sort_order: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- IncomeRecord ----------

class IncomeRecordCreate(BaseModel):
    source_id: int
    amount: float = Field(..., gt=0)
    record_date: date
    note: str | None = Field(None, max_length=512)


class IncomeRecordUpdate(BaseModel):
    source_id: int | None = None
    amount: float | None = Field(None, gt=0)
    record_date: date | None = None
    note: str | None = Field(None, max_length=512)


class IncomeRecordRead(BaseModel):
    id: int
    source_id: int
    source_name: str
    amount: float
    record_date: date
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- 统计聚合 ----------

class YearlyTrendItem(BaseModel):
    month: int          # 1-12
    total: float


class MonthlyBreakdownItem(BaseModel):
    source_id: int
    source_name: str
    total: float
    percentage: float   # 0-100
