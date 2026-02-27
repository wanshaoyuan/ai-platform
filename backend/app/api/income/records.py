from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, extract
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.deps import get_current_user
from app.models.user import User
from app.models.income import IncomeRecord, IncomeSource
from app.schemas.income import (
    IncomeRecordCreate,
    IncomeRecordUpdate,
    IncomeRecordRead,
    YearlyTrendItem,
    MonthlyBreakdownItem,
)

router = APIRouter()


# ------------------------------------------------------------------ helpers --

def _record_to_read(record: IncomeRecord) -> IncomeRecordRead:
    return IncomeRecordRead(
        id=record.id,
        source_id=record.source_id,
        source_name=record.source.name if record.source else "",
        amount=record.amount,
        record_date=record.record_date,
        note=record.note,
        created_at=record.created_at,
    )


def _get_record_or_404(record_id: int, user_id: int, db: Session) -> IncomeRecord:
    record = (
        db.query(IncomeRecord)
        .options(joinedload(IncomeRecord.source))
        .filter(IncomeRecord.id == record_id, IncomeRecord.user_id == user_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return record


# ------------------------------------------------------------------- CRUD ---

@router.get("", response_model=dict)
def list_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    year: Optional[int] = None,
    month: Optional[int] = None,
    source_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = (
        db.query(IncomeRecord)
        .options(joinedload(IncomeRecord.source))
        .filter(IncomeRecord.user_id == current_user.id)
    )
    if year:
        q = q.filter(extract("year", IncomeRecord.record_date) == year)
    if month:
        q = q.filter(extract("month", IncomeRecord.record_date) == month)
    if source_id:
        q = q.filter(IncomeRecord.source_id == source_id)

    total = q.count()
    records = (
        q.order_by(IncomeRecord.record_date.desc(), IncomeRecord.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_record_to_read(r) for r in records],
    }


@router.post("", response_model=IncomeRecordRead, status_code=status.HTTP_201_CREATED)
def create_record(
    payload: IncomeRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 验证来源属于当前用户
    source = db.get(IncomeSource, payload.source_id)
    if not source or source.user_id != current_user.id:
        raise HTTPException(status_code=400, detail="收入来源不存在")

    record = IncomeRecord(user_id=current_user.id, **payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    # 重新加载关联
    record = (
        db.query(IncomeRecord)
        .options(joinedload(IncomeRecord.source))
        .filter(IncomeRecord.id == record.id)
        .first()
    )
    return _record_to_read(record)


@router.put("/{record_id}", response_model=IncomeRecordRead)
def update_record(
    record_id: int,
    payload: IncomeRecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = _get_record_or_404(record_id, current_user.id, db)
    if payload.source_id is not None:
        source = db.get(IncomeSource, payload.source_id)
        if not source or source.user_id != current_user.id:
            raise HTTPException(status_code=400, detail="收入来源不存在")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    record = (
        db.query(IncomeRecord)
        .options(joinedload(IncomeRecord.source))
        .filter(IncomeRecord.id == record.id)
        .first()
    )
    return _record_to_read(record)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = _get_record_or_404(record_id, current_user.id, db)
    db.delete(record)
    db.commit()


# --------------------------------------------------------------- 统计接口 ---

@router.get("/stats/yearly-trend", response_model=list[YearlyTrendItem])
def yearly_trend(
    year: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回指定年份 1-12 月的总收入，无数据的月份补 0。"""
    rows = (
        db.query(
            extract("month", IncomeRecord.record_date).label("month"),
            func.sum(IncomeRecord.amount).label("total"),
        )
        .filter(
            IncomeRecord.user_id == current_user.id,
            extract("year", IncomeRecord.record_date) == year,
        )
        .group_by("month")
        .all()
    )
    month_map = {int(r.month): round(r.total, 2) for r in rows}
    return [YearlyTrendItem(month=m, total=month_map.get(m, 0.0)) for m in range(1, 13)]


@router.get("/stats/monthly-breakdown", response_model=list[MonthlyBreakdownItem])
def monthly_breakdown(
    year: int,
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回指定月份各来源的金额及占比。"""
    rows = (
        db.query(
            IncomeSource.id.label("source_id"),
            IncomeSource.name.label("source_name"),
            func.sum(IncomeRecord.amount).label("total"),
        )
        .join(IncomeRecord, IncomeRecord.source_id == IncomeSource.id)
        .filter(
            IncomeRecord.user_id == current_user.id,
            extract("year", IncomeRecord.record_date) == year,
            extract("month", IncomeRecord.record_date) == month,
        )
        .group_by(IncomeSource.id, IncomeSource.name)
        .all()
    )
    grand_total = sum(r.total for r in rows) or 1  # 避免除以零
    return [
        MonthlyBreakdownItem(
            source_id=r.source_id,
            source_name=r.source_name,
            total=round(r.total, 2),
            percentage=round(r.total / grand_total * 100, 2),
        )
        for r in rows
    ]
