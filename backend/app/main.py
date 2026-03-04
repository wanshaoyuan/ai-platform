import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.scheduler import start_scheduler, stop_scheduler
from app.db import engine, Base
from app.models import User, Account, MonthlyBalance, BackupLog, DebtItem, RepaymentSchedule  # noqa: F401 触发模型注册
from app.core.security import hash_password

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI 中台", version="1.0.0", docs_url="/api/docs", redoc_url=None)

# ---------- CORS ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- 路由注册 ----------
from app.api.auth import router as auth_router
from app.api.income.balances import router as balances_router
from app.api.backup import router as backup_router
from app.api.debt.debts import router as debts_router

app.include_router(auth_router,     prefix="/api/auth",    tags=["认证"])
app.include_router(balances_router, prefix="/api/income",  tags=["余额管理"])
app.include_router(backup_router,   prefix="/api/backup",  tags=["数据备份"])
app.include_router(debts_router,    prefix="/api/debt",    tags=["债务管理"])


# ---------- 生命周期 ----------
@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured.")

    from app.db import SessionLocal
    from app.models.income import Account, MonthlyBalance
    from app.api.income.balances import DEFAULT_ACCOUNTS

    with SessionLocal() as db:
        # 确保 admin 用户存在
        existing = db.query(User).filter(User.username == "admin").first()
        if not existing:
            admin = User(
                username="admin",
                hashed_password=hash_password("admin123"),
                role="admin",
                is_active=True,
            )
            db.add(admin)
            db.commit()
            logger.info("Default admin account created.")
            existing = admin

        # 数据迁移：若 monthly_balances 中有 account_id 1-6 但 accounts 表为空，
        # 则自动创建默认账户并修正 account_id FK（SQLite 不强制 FK，但需保持一致）
        acc_count = db.query(Account).filter(Account.user_id == existing.id).count()
        if acc_count == 0:
            old_balance_count = db.query(MonthlyBalance).filter(
                MonthlyBalance.user_id == existing.id
            ).count()
            if old_balance_count > 0:
                # 旧数据：account_id 为 1-6，创建对应的 Account 行并修正 FK
                old_accs = []
                for i, name in enumerate(DEFAULT_ACCOUNTS):
                    a = Account(user_id=existing.id, name=name, sort_order=i)
                    db.add(a)
                    old_accs.append(a)
                db.flush()
                # 将旧 monthly_balances.account_id (1-6) 映射到新 accounts.id
                old_id_to_new = {i + 1: a.id for i, a in enumerate(old_accs)}
                old_name_map = {i + 1: name for i, name in enumerate(DEFAULT_ACCOUNTS)}
                for bal in db.query(MonthlyBalance).filter(
                    MonthlyBalance.user_id == existing.id
                ).all():
                    new_id = old_id_to_new.get(bal.account_id)
                    if new_id:
                        bal.account_id = new_id
                        bal.account_name = old_name_map.get(
                            list(old_id_to_new.keys())[list(old_id_to_new.values()).index(new_id)],
                            bal.account_name
                        )
                db.commit()
                logger.info("Migrated existing monthly_balances to new accounts table.")

    start_scheduler()


@app.on_event("shutdown")
def on_shutdown() -> None:
    stop_scheduler()


@app.get("/api/health", tags=["系统"])
def health():
    return {"status": "ok"}
