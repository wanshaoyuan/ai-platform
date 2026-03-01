from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models.user import User
from app.models.debt import DebtItem, RepaymentSchedule
from app.schemas.debt import (
    DebtItemCreate,
    DebtItemUpdate,
    DebtItemRead,
    RepaymentScheduleRead,
    DebtSummary,
    DebtBarItem,
)
from app.core.debt_calculator import (
    generate_schedule,
    calc_monthly_payment_equal_installment,
    calc_monthly_payment_equal_principal,
)

router = APIRouter()


# ──────────────────────────────── helpers ────────────────────────────────────

def _get_debt_or_404(debt_id: int, user_id: int, db: Session) -> DebtItem:
    debt = db.query(DebtItem).filter(
        DebtItem.id == debt_id, DebtItem.user_id == user_id
    ).first()
    if not debt:
        raise HTTPException(status_code=404, detail="债务记录不存在")
    return debt


def _build_schedule(debt: DebtItem, db: Session) -> None:
    """根据 DebtItem 的参数重新生成/覆盖还款计划表。"""
    db.query(RepaymentSchedule).filter(RepaymentSchedule.debt_id == debt.id).delete()

    periods = generate_schedule(
        principal=debt.principal,
        annual_rate=debt.annual_rate,
        term_months=debt.term_months,
        repay_method=debt.repay_method,
        first_repay_date=debt.first_repay_date,
    )
    for p in periods:
        db.add(RepaymentSchedule(
            debt_id=debt.id,
            period_no=p.period_no,
            due_date=p.due_date,
            payment_amount=p.payment_amount,
            principal_amount=p.principal_amount,
            interest_amount=p.interest_amount,
            remaining_balance=p.remaining_balance,
            status="pending",
        ))


# ──────────────────────────── 统计接口（必须在 /{debt_id} 之前注册） ───────────────

@router.get("/stats/summary", response_model=DebtSummary)
def get_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回仪表盘顶部汇总数据。"""
    debts = db.query(DebtItem).filter(
        DebtItem.user_id == current_user.id, DebtItem.is_active == True
    ).all()
    total_balance = round(sum(d.current_balance for d in debts), 2)
    monthly_total = round(sum(d.monthly_payment for d in debts), 2)
    return DebtSummary(
        total_balance=total_balance,
        monthly_total_payment=monthly_total,
        active_count=len(debts),
    )


@router.get("/stats/bar-chart", response_model=list[DebtBarItem])
def get_bar_chart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回柱状图所需数据：各债务当前余额 + 月供。"""
    debts = db.query(DebtItem).filter(
        DebtItem.user_id == current_user.id, DebtItem.is_active == True
    ).order_by(DebtItem.current_balance.desc()).all()
    return [
        DebtBarItem(
            name=d.name,
            current_balance=round(d.current_balance, 2),
            monthly_payment=round(d.monthly_payment, 2),
        )
        for d in debts
    ]


# ──────────────────────────────── CRUD ───────────────────────────────────────

@router.get("", response_model=list[DebtItemRead])
def list_debts(
    active_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回当前用户的所有债务列表。"""
    q = db.query(DebtItem).filter(DebtItem.user_id == current_user.id)
    if active_only:
        q = q.filter(DebtItem.is_active == True)
    return q.order_by(DebtItem.created_at.desc()).all()


@router.post("", response_model=DebtItemRead, status_code=status.HTTP_201_CREATED)
def create_debt(
    payload: DebtItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """新增一笔贷款，后端自动计算月供并生成完整还款计划表。"""
    if payload.repay_method == "equal_installment":
        monthly = calc_monthly_payment_equal_installment(
            payload.principal, payload.annual_rate, payload.term_months
        )
    else:
        monthly = calc_monthly_payment_equal_principal(
            payload.principal, payload.annual_rate, payload.term_months
        )

    debt = DebtItem(
        user_id=current_user.id,
        name=payload.name,
        principal=payload.principal,
        annual_rate=payload.annual_rate,
        term_months=payload.term_months,
        repay_method=payload.repay_method,
        first_repay_date=payload.first_repay_date,
        monthly_repay_day=payload.monthly_repay_day,
        monthly_payment=monthly,
        current_balance=payload.principal,
        paid_periods=0,
        is_active=True,
        note=payload.note,
    )
    db.add(debt)
    db.flush()

    _build_schedule(debt, db)
    db.commit()
    db.refresh(debt)
    return debt


@router.get("/{debt_id}", response_model=DebtItemRead)
def get_debt(
    debt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_debt_or_404(debt_id, current_user.id, db)


@router.put("/{debt_id}", response_model=DebtItemRead)
def update_debt(
    debt_id: int,
    payload: DebtItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """只允许修改名称、备注、是否有效（不重新计算计划）。"""
    debt = _get_debt_or_404(debt_id, current_user.id, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(debt, field, value)
    db.commit()
    db.refresh(debt)
    return debt


@router.delete("/{debt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_debt(
    debt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    debt = _get_debt_or_404(debt_id, current_user.id, db)
    db.delete(debt)
    db.commit()


# ──────────────────────────── 还款计划表 ──────────────────────────────────────

@router.get("/{debt_id}/schedule", response_model=list[RepaymentScheduleRead])
def get_schedule(
    debt_id: int,
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回指定债务的还款计划表，可按状态筛选。"""
    _get_debt_or_404(debt_id, current_user.id, db)
    q = db.query(RepaymentSchedule).filter(RepaymentSchedule.debt_id == debt_id)
    if status_filter:
        q = q.filter(RepaymentSchedule.status == status_filter)
    return q.order_by(RepaymentSchedule.period_no.asc()).all()
