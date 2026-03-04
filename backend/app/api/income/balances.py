"""
余额管理 API
- GET    /api/income/accounts             返回当前用户的自定义账户列表
- POST   /api/income/accounts             创建账户
- PUT    /api/income/accounts/{id}        更新账户名称/排序
- DELETE /api/income/accounts/{id}        删除账户（软删除，标记 is_active=False）
- GET    /api/income/balances             返回所有月份的快照列表（月份倒序）
- GET    /api/income/balances/{month}     返回指定月份的全部账户余额
- POST   /api/income/balances             创建或更新某月的账户余额（upsert）
- DELETE /api/income/balances/{month}     删除指定月份的全部记录
- GET    /api/income/stats/trend          返回各账户+总资产的趋势数据（用于折线图）
- GET    /api/income/export/csv           导出所有月份余额为 CSV
- POST   /api/income/import/csv           导入 CSV 文件（覆盖式 upsert）
"""
import csv
import io
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models.user import User
from app.models.income import Account, MonthlyBalance
from app.schemas.income import (
    AccountCreate,
    AccountUpdate,
    AccountRead,
    MonthlyBalanceUpsert,
    MonthlyBalanceRead,
    MonthlySnapshotRead,
    AccountTrendRead,
    TrendPoint,
)

router = APIRouter()

# ── 默认账户（仅在用户首次使用时初始化） ──────────────────────────────────────

DEFAULT_ACCOUNTS = ["微众银行", "招商银行", "工商银行", "微信", "证券", "腾讯股票"]


def _get_or_init_accounts(db: Session, user: User) -> list[Account]:
    """
    获取用户的账户列表（按 sort_order + id 排序）。
    若用户尚无账户，则自动用默认值初始化。
    """
    accs = (
        db.query(Account)
        .filter(Account.user_id == user.id, Account.is_active == True)  # noqa: E712
        .order_by(Account.sort_order, Account.id)
        .all()
    )
    if not accs:
        new_accs = []
        for i, name in enumerate(DEFAULT_ACCOUNTS):
            a = Account(user_id=user.id, name=name, sort_order=i)
            new_accs.append(a)
        db.add_all(new_accs)
        db.commit()
        for a in new_accs:
            db.refresh(a)
        accs = new_accs
    return accs


# ── 账户管理 ───────────────────────────────────────────────────────────────────

@router.get("/accounts", response_model=list[AccountRead])
def list_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回用户的账户列表（按排序）。首次访问时自动初始化默认账户。"""
    return _get_or_init_accounts(db, current_user)


@router.post("/accounts", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: AccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = db.query(Account).filter(
        Account.user_id == current_user.id,
        Account.name == payload.name,
        Account.is_active == True,  # noqa: E712
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="账户名称已存在")
    acc = Account(
        user_id=current_user.id,
        name=payload.name,
        sort_order=payload.sort_order,
    )
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc


@router.put("/accounts/{account_id}", response_model=AccountRead)
def update_account(
    account_id: int,
    payload: AccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    acc = db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == current_user.id,
        Account.is_active == True,  # noqa: E712
    ).first()
    if not acc:
        raise HTTPException(status_code=404, detail="账户不存在")
    if payload.name is not None:
        dup = db.query(Account).filter(
            Account.user_id == current_user.id,
            Account.name == payload.name,
            Account.id != account_id,
            Account.is_active == True,  # noqa: E712
        ).first()
        if dup:
            raise HTTPException(status_code=409, detail="账户名称已存在")
        acc.name = payload.name
    if payload.sort_order is not None:
        acc.sort_order = payload.sort_order
    db.commit()
    db.refresh(acc)
    return acc


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    acc = db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == current_user.id,
    ).first()
    if not acc:
        raise HTTPException(status_code=404, detail="账户不存在")
    acc.is_active = False
    db.commit()


# ── 月份列表 ───────────────────────────────────────────────────────────────────

@router.get("/balances", response_model=list[MonthlySnapshotRead])
def list_months(
    limit: int = Query(24, ge=1, le=120, description="返回最近 N 个月，默认 24"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回有记录的月份列表（倒序），每月包含各账户余额和总额。"""
    months = (
        db.query(MonthlyBalance.month)
        .filter(MonthlyBalance.user_id == current_user.id)
        .distinct()
        .order_by(MonthlyBalance.month.desc())
        .limit(limit)
        .all()
    )
    result = []
    for (month,) in months:
        items = (
            db.query(MonthlyBalance)
            .filter(
                MonthlyBalance.user_id == current_user.id,
                MonthlyBalance.month == month,
            )
            .order_by(MonthlyBalance.account_id)
            .all()
        )
        total = round(sum(i.balance for i in items), 2)
        result.append(MonthlySnapshotRead(
            month=month,
            total=total,
            items=[MonthlyBalanceRead.model_validate(i) for i in items],
        ))
    return result


# ── 单月详情 ───────────────────────────────────────────────────────────────────

@router.get("/balances/{month}", response_model=MonthlySnapshotRead)
def get_month(
    month: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = (
        db.query(MonthlyBalance)
        .filter(
            MonthlyBalance.user_id == current_user.id,
            MonthlyBalance.month == month,
        )
        .order_by(MonthlyBalance.account_id)
        .all()
    )
    if not items:
        raise HTTPException(status_code=404, detail="该月份暂无记录")
    total = round(sum(i.balance for i in items), 2)
    return MonthlySnapshotRead(
        month=month,
        total=total,
        items=[MonthlyBalanceRead.model_validate(i) for i in items],
    )


# ── 创建/更新某月余额（upsert） ────────────────────────────────────────────────

@router.post("/balances", response_model=MonthlySnapshotRead, status_code=status.HTTP_200_OK)
def upsert_balances(
    payload: MonthlyBalanceUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    创建或更新指定月份的账户余额。
    若该月该账户已有记录则更新，否则插入。
    """
    accs = db.query(Account).filter(
        Account.user_id == current_user.id,
        Account.is_active == True,  # noqa: E712
    ).all()
    acc_map = {a.id: a.name for a in accs}

    for item in payload.balances:
        if item.account_id not in acc_map:
            raise HTTPException(status_code=400, detail=f"无效的账户 ID: {item.account_id}")

        existing = db.query(MonthlyBalance).filter(
            MonthlyBalance.user_id == current_user.id,
            MonthlyBalance.month == payload.month,
            MonthlyBalance.account_id == item.account_id,
        ).first()

        if existing:
            existing.balance = item.balance
            existing.account_name = acc_map[item.account_id]
        else:
            db.add(MonthlyBalance(
                user_id=current_user.id,
                month=payload.month,
                account_id=item.account_id,
                account_name=acc_map[item.account_id],
                balance=item.balance,
            ))

    db.commit()
    return get_month(payload.month, db, current_user)


# ── 删除某月全部记录 ───────────────────────────────────────────────────────────

@router.delete("/balances/{month}", status_code=status.HTTP_204_NO_CONTENT)
def delete_month(
    month: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = db.query(MonthlyBalance).filter(
        MonthlyBalance.user_id == current_user.id,
        MonthlyBalance.month == month,
    ).delete()
    if not deleted:
        raise HTTPException(status_code=404, detail="该月份暂无记录")
    db.commit()


# ── 趋势统计（折线图） ─────────────────────────────────────────────────────────

@router.get("/stats/trend", response_model=list[AccountTrendRead])
def get_trend(
    months: int = Query(12, ge=1, le=60, description="最近 N 个月"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    返回各账户余额趋势 + 总资产趋势。
    结果末尾附加一条「总资产」合计折线（account_id=0）。
    """
    month_rows = (
        db.query(MonthlyBalance.month)
        .filter(MonthlyBalance.user_id == current_user.id)
        .distinct()
        .order_by(MonthlyBalance.month.desc())
        .limit(months)
        .all()
    )
    if not month_rows:
        return []

    sorted_months = sorted(m for (m,) in month_rows)

    records = (
        db.query(MonthlyBalance)
        .filter(
            MonthlyBalance.user_id == current_user.id,
            MonthlyBalance.month.in_(sorted_months),
        )
        .all()
    )

    accs = (
        db.query(Account)
        .filter(Account.user_id == current_user.id, Account.is_active == True)  # noqa: E712
        .order_by(Account.sort_order, Account.id)
        .all()
    )

    data: dict[int, dict[str, float]] = {a.id: {} for a in accs}
    for r in records:
        if r.account_id in data:
            data[r.account_id][r.month] = r.balance

    result: list[AccountTrendRead] = []

    for acc in accs:
        points = [
            TrendPoint(month=m, value=round(data[acc.id].get(m, 0.0), 2))
            for m in sorted_months
        ]
        result.append(AccountTrendRead(
            account_id=acc.id,
            account_name=acc.name,
            data=points,
        ))

    total_points = [
        TrendPoint(
            month=m,
            value=round(sum(data[a.id].get(m, 0.0) for a in accs), 2),
        )
        for m in sorted_months
    ]
    result.append(AccountTrendRead(
        account_id=0,
        account_name="总资产",
        data=total_points,
    ))

    return result


# ── 年度趋势统计（折线图） ─────────────────────────────────────────────────────

@router.get("/stats/trend/yearly", response_model=list[AccountTrendRead])
def get_trend_yearly(
    years: int = Query(5, ge=1, le=20, description="最近 N 年"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    返回各账户余额的年度趋势 + 总资产趋势。
    每年取该年最后一个有记录的月份的余额作为年末值。
    结果末尾附加一条「总资产」合计折线（account_id=0）。
    """
    from sqlalchemy import func as sqlfunc

    # 取最近 N 年有数据的年份（升序）
    all_months_q = (
        db.query(MonthlyBalance.month)
        .filter(MonthlyBalance.user_id == current_user.id)
        .distinct()
        .order_by(MonthlyBalance.month.desc())
        .all()
    )
    if not all_months_q:
        return []

    all_months_list = sorted(m for (m,) in all_months_q)

    # 提取年份并限制到最近 N 年
    all_years_set = sorted({m[:4] for m in all_months_list}, reverse=True)[:years]
    selected_years = sorted(all_years_set)

    # 每年取最后一个月
    year_to_last_month: dict[str, str] = {}
    for month in reversed(all_months_list):
        year = month[:4]
        if year in selected_years and year not in year_to_last_month:
            year_to_last_month[year] = month

    sorted_year_months = [year_to_last_month[y] for y in selected_years if y in year_to_last_month]

    records = (
        db.query(MonthlyBalance)
        .filter(
            MonthlyBalance.user_id == current_user.id,
            MonthlyBalance.month.in_(sorted_year_months),
        )
        .all()
    )

    accs = (
        db.query(Account)
        .filter(Account.user_id == current_user.id, Account.is_active == True)  # noqa: E712
        .order_by(Account.sort_order, Account.id)
        .all()
    )

    # account_id → {month → balance}
    data: dict[int, dict[str, float]] = {a.id: {} for a in accs}
    for r in records:
        if r.account_id in data:
            data[r.account_id][r.month] = r.balance

    # X 轴用年份标签，但数据点用对应的最后月份取值
    x_labels = [m[:4] for m in sorted_year_months]

    result: list[AccountTrendRead] = []

    for acc in accs:
        points = [
            TrendPoint(month=x_labels[i], value=round(data[acc.id].get(m, 0.0), 2))
            for i, m in enumerate(sorted_year_months)
        ]
        result.append(AccountTrendRead(
            account_id=acc.id,
            account_name=acc.name,
            data=points,
        ))

    total_points = [
        TrendPoint(
            month=x_labels[i],
            value=round(sum(data[a.id].get(m, 0.0) for a in accs), 2),
        )
        for i, m in enumerate(sorted_year_months)
    ]
    result.append(AccountTrendRead(
        account_id=0,
        account_name="总资产",
        data=total_points,
    ))

    return result


# ── CSV 导出 ───────────────────────────────────────────────────────────────────

@router.get("/export/csv")
def export_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    导出所有月份余额数据为 CSV 文件（UTF-8 with BOM，Excel 可直接打开）。
    格式：月份,账户1,账户2,...,总资产
    """
    accs = (
        db.query(Account)
        .filter(Account.user_id == current_user.id, Account.is_active == True)  # noqa: E712
        .order_by(Account.sort_order, Account.id)
        .all()
    )

    months_q = (
        db.query(MonthlyBalance.month)
        .filter(MonthlyBalance.user_id == current_user.id)
        .distinct()
        .order_by(MonthlyBalance.month.asc())
        .all()
    )
    all_months = [m for (m,) in months_q]

    records = (
        db.query(MonthlyBalance)
        .filter(MonthlyBalance.user_id == current_user.id)
        .all()
    )
    bal_map: dict[str, dict[int, float]] = {}
    for r in records:
        bal_map.setdefault(r.month, {})[r.account_id] = r.balance

    output = io.StringIO()
    writer = csv.writer(output)

    header = ["月份"] + [a.name for a in accs] + ["总资产"]
    writer.writerow(header)

    for month in all_months:
        month_data = bal_map.get(month, {})
        row = [month]
        total = 0.0
        for a in accs:
            v = month_data.get(a.id, 0.0)
            row.append(v)
            total += v
        row.append(round(total, 2))
        writer.writerow(row)

    # UTF-8 with BOM so Excel opens correctly
    csv_bytes = ("\ufeff" + output.getvalue()).encode("utf-8")
    filename = f"balance_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ── CSV 导入 ───────────────────────────────────────────────────────────────────

_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
# 兼容 "YYYY/M/D"、"YYYY/MM/DD"、"YYYY-M-D" 等日期格式 → 提取 YYYY-MM
_DATE_RE = re.compile(r"^(\d{4})[/\-](\d{1,2})[/\-]\d{1,2}$")

# 总计列（导入时忽略）
_TOTAL_COLS = {"月份", "总资产", "总额", ""}


def _normalize_month(raw: str) -> str:
    """
    将各种日期/月份格式统一转为 YYYY-MM。
    支持：YYYY-MM、YYYY/M/D、YYYY-M-D 等。
    无法识别时原样返回。
    """
    s = raw.strip()
    if _MONTH_RE.match(s):
        return s
    m = _DATE_RE.match(s)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}"
    return s


@router.post("/import/csv", status_code=status.HTTP_200_OK)
def import_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    导入 CSV 文件覆盖余额数据。
    期望格式：月份,账户1,账户2,...（与导出格式一致，忽略「总资产」列）。
    未识别的账户名称将自动创建。
    """
    content = file.file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("gbk", errors="replace")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV 文件为空或格式不正确")

    acc_columns = [f for f in reader.fieldnames if f not in _TOTAL_COLS]

    # 确保账户名称都存在（不存在则自动创建）
    acc_map: dict[str, Account] = {}
    for a in db.query(Account).filter(Account.user_id == current_user.id).all():
        acc_map[a.name] = a

    for col in acc_columns:
        if col not in acc_map or not acc_map[col].is_active:
            if col in acc_map and not acc_map[col].is_active:
                acc_map[col].is_active = True
            else:
                new_acc = Account(
                    user_id=current_user.id,
                    name=col,
                    sort_order=len([a for a in acc_map.values() if a.is_active]),
                )
                db.add(new_acc)
                db.flush()
                acc_map[col] = new_acc

    inserted = 0
    updated = 0
    skipped = 0

    for row in reader:
        month = _normalize_month(row.get("月份") or "")
        if not _MONTH_RE.match(month):
            skipped += 1
            continue

        for col in acc_columns:
            raw = (row.get(col) or "").strip()
            if not raw:
                continue
            try:
                balance = float(raw.replace(",", ""))
            except ValueError:
                skipped += 1
                continue

            if balance < 0:
                skipped += 1
                continue

            acc = acc_map[col]
            existing = db.query(MonthlyBalance).filter(
                MonthlyBalance.user_id == current_user.id,
                MonthlyBalance.month == month,
                MonthlyBalance.account_id == acc.id,
            ).first()

            if existing:
                existing.balance = balance
                existing.account_name = acc.name
                updated += 1
            else:
                db.add(MonthlyBalance(
                    user_id=current_user.id,
                    month=month,
                    account_id=acc.id,
                    account_name=acc.name,
                    balance=balance,
                ))
                inserted += 1

    db.commit()
    return {"inserted": inserted, "updated": updated, "skipped": skipped}
