import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.scheduler import start_scheduler, stop_scheduler
from app.db import engine, Base
from app.models import User, IncomeSource, IncomeRecord, BackupLog  # noqa: F401 触发模型注册
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
from app.api.income.sources import router as sources_router
from app.api.income.records import router as records_router
from app.api.backup import router as backup_router

app.include_router(auth_router,    prefix="/api/auth",           tags=["认证"])
app.include_router(sources_router, prefix="/api/income/sources", tags=["收入来源"])
app.include_router(records_router, prefix="/api/income/records", tags=["收入记录"])
app.include_router(backup_router,  prefix="/api/backup",         tags=["数据备份"])


# ---------- 生命周期 ----------
@app.on_event("startup")
def on_startup() -> None:
    # 建表
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured.")

    # 初始化默认管理员账号
    from app.db import SessionLocal
    with SessionLocal() as db:
        existing = db.query(User).filter(User.username == "admin").first()
        if not existing:
            admin = User(
                username="admin",
                hashed_password=hash_password("admin123"),
                role="admin",
                is_active=True,
            )
            db.add(admin)

            # 为 admin 创建默认收入来源
            db.flush()  # 获取 admin.id
            from app.models.income import IncomeSource as IS
            defaults = [("银行卡", "💳", 0), ("微信", "💚", 1), ("股票", "📈", 2)]
            for name, icon, order in defaults:
                db.add(IS(user_id=admin.id, name=name, icon=icon, sort_order=order))
            db.commit()
            logger.info("Default admin account and income sources created.")

    # 启动定时备份
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown() -> None:
    stop_scheduler()


@app.get("/api/health", tags=["系统"])
def health():
    return {"status": "ok"}
