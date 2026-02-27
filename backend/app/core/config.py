from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/


class Settings(BaseSettings):
    # JWT
    SECRET_KEY: str = "change-this-to-a-long-random-secret-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 小时

    # 数据库
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/data/ai_platform.db"

    # 备份
    BACKUP_DIR: Path = BASE_DIR / "backups"
    BACKUP_RETAIN_DAYS: int = 7
    BACKUP_HOUR: int = 2    # 每天凌晨 2 点执行备份
    BACKUP_MINUTE: int = 0

    # CORS（开发环境允许前端本地端口）
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
