import csv
import io
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
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
    AnnualTotalItem,
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


@router.get("/stats/annual-totals", response_model=list[AnnualTotalItem])
def annual_totals(
    years: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回近 N 年每年的总余额，无数据的年份补 0。"""
    current_year = date.today().year
    rows = (
        db.query(
            extract("year", IncomeRecord.record_date).label("year"),
            func.sum(IncomeRecord.amount).label("total"),
        )
        .filter(
            IncomeRecord.user_id == current_user.id,
            extract("year", IncomeRecord.record_date) >= current_year - years + 1,
        )
        .group_by("year")
        .all()
    )
    year_map = {int(r.year): round(r.total, 2) for r in rows}
    return [
        AnnualTotalItem(year=y, total=year_map.get(y, 0.0))
        for y in range(current_year - years + 1, current_year + 1)
    ]


@router.get("/export/csv")
def export_csv(
    year: Optional[int] = None,
    month: Optional[int] = None,
    source_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """导出当前筛选条件下的记录为 CSV 文件。"""
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
    records = q.order_by(IncomeRecord.record_date.desc(), IncomeRecord.id.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["日期", "来源", "金额", "备注"])
    for r in records:
        # 统一输出 YYYY-MM-DD 格式，避免因数据库驱动差异产生 YYYY/M/D
        rd = r.record_date
        if isinstance(rd, date):
            date_str = rd.strftime("%Y-%m-%d")
        else:
            date_str = str(rd).replace("/", "-")
        writer.writerow([
            date_str,
            r.source.name if r.source else "",
            f"{r.amount:.2f}",
            r.note or "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue().encode("utf-8-sig")]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=records.csv"},
    )


@router.post("/import/csv")
async def import_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """从 CSV 文件导入余额记录。CSV 列：日期,来源,金额,备注"""
    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("gbk", errors="replace")

    reader = csv.DictReader(io.StringIO(text))

    # 构建来源名称 -> source 对象的映射
    sources = (
        db.query(IncomeSource)
        .filter(IncomeSource.user_id == current_user.id, IncomeSource.is_active == True)
        .all()
    )
    source_map = {s.name: s for s in sources}

    imported = 0
    errors: list[str] = []

    for i, row in enumerate(reader, start=2):  # 从第2行开始（第1行是表头）
        date_str = (row.get("日期") or "").strip()
        source_name = (row.get("来源") or "").strip()
        amount_str = (row.get("金额") or "").strip()
        note = (row.get("备注") or "").strip() or None

        if not date_str or not source_name or not amount_str:
            errors.append(f"第{i}行：缺少必要字段")
            continue

        try:
            # 兼容 YYYY-MM-DD、YYYY/MM/DD、YYYY/M/D 等格式
            parts = date_str.replace("/", "-").split("-")
            if len(parts) == 3:
                normalized = f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
            else:
                normalized = date_str
            record_date = date.fromisoformat(normalized)
        except ValueError:
            errors.append(f"第{i}行：日期格式错误 ({date_str})")
            continue

        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError
        except ValueError:
            errors.append(f"第{i}行：金额无效 ({amount_str})")
            continue

        source = source_map.get(source_name)
        if not source:
            errors.append(f"第{i}行：来源「{source_name}」不存在，已跳过")
            continue

        # 查找日期 + 来源 + 金额完全相同的已有记录
        existing = (
            db.query(IncomeRecord)
            .filter(
                IncomeRecord.user_id == current_user.id,
                IncomeRecord.source_id == source.id,
                IncomeRecord.record_date == record_date,
                IncomeRecord.amount == amount,
            )
            .first()
        )
        if existing:
            existing.note = note
        else:
            db.add(IncomeRecord(
                user_id=current_user.id,
                source_id=source.id,
                amount=amount,
                record_date=record_date,
                note=note,
            ))
        imported += 1

    db.commit()
    return {"imported": imported, "skipped": len(errors), "errors": errors}
