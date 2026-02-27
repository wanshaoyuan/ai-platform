from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models.user import User
from app.models.income import IncomeSource
from app.schemas.income import IncomeSourceCreate, IncomeSourceUpdate, IncomeSourceRead

router = APIRouter()


@router.get("", response_model=list[IncomeSourceRead])
def list_sources(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(IncomeSource).filter(IncomeSource.user_id == current_user.id)
    if not include_inactive:
        q = q.filter(IncomeSource.is_active == True)  # noqa: E712
    return q.order_by(IncomeSource.sort_order, IncomeSource.id).all()


@router.post("", response_model=IncomeSourceRead, status_code=status.HTTP_201_CREATED)
def create_source(
    payload: IncomeSourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = (
        db.query(IncomeSource)
        .filter(IncomeSource.user_id == current_user.id, IncomeSource.name == payload.name)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="来源名称已存在")
    source = IncomeSource(user_id=current_user.id, **payload.model_dump())
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.put("/{source_id}", response_model=IncomeSourceRead)
def update_source(
    source_id: int,
    payload: IncomeSourceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    source = _get_source_or_404(source_id, current_user.id, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(source, field, value)
    db.commit()
    db.refresh(source)
    return source


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(
    source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    source = _get_source_or_404(source_id, current_user.id, db)
    # 检查是否有关联记录
    if source.records:
        raise HTTPException(
            status_code=400,
            detail="该来源下存在收入记录，无法删除。请先删除相关记录或改用停用操作。",
        )
    db.delete(source)
    db.commit()


def _get_source_or_404(source_id: int, user_id: int, db: Session) -> IncomeSource:
    source = db.get(IncomeSource, source_id)
    if not source or source.user_id != user_id:
        raise HTTPException(status_code=404, detail="来源不存在")
    return source
