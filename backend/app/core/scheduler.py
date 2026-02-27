import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler(timezone="Asia/Shanghai")


def _do_backup() -> None:
    """将 SQLite 数据库文件复制到备份目录，并清理超期备份。"""
    try:
        backup_dir: Path = settings.BACKUP_DIR
        backup_dir.mkdir(parents=True, exist_ok=True)

        # 源数据库文件路径（从 DATABASE_URL 解析）
        db_path_str = settings.DATABASE_URL.replace("sqlite:///", "")
        db_path = Path(db_path_str)
        if not db_path.exists():
            logger.warning("Backup skipped: database file not found at %s", db_path)
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = backup_dir / f"ai_platform_{timestamp}.db"
        shutil.copy2(db_path, dest)
        logger.info("Backup succeeded: %s", dest)

        # 写入备份日志（延迟导入避免循环依赖）
        try:
            from app.db import SessionLocal
            from app.models.backup import BackupLog

            with SessionLocal() as session:
                log = BackupLog(
                    file_path=str(dest),
                    file_size=dest.stat().st_size,
                    status="success",
                )
                session.add(log)
                session.commit()
        except Exception as db_err:
            logger.warning("Failed to write backup log: %s", db_err)

        # 清理超期备份（保留最近 N 天）
        cutoff = datetime.now() - timedelta(days=settings.BACKUP_RETAIN_DAYS)
        for old_file in backup_dir.glob("ai_platform_*.db"):
            if old_file.stat().st_mtime < cutoff.timestamp():
                old_file.unlink()
                logger.info("Removed old backup: %s", old_file)

    except Exception as exc:
        logger.error("Backup failed: %s", exc)
        try:
            from app.db import SessionLocal
            from app.models.backup import BackupLog

            with SessionLocal() as session:
                log = BackupLog(file_path="", status="failed", message=str(exc))
                session.add(log)
                session.commit()
        except Exception:
            pass


def start_scheduler() -> None:
    scheduler.add_job(
        _do_backup,
        CronTrigger(hour=settings.BACKUP_HOUR, minute=settings.BACKUP_MINUTE),
        id="daily_backup",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler started. Daily backup at %02d:%02d",
        settings.BACKUP_HOUR,
        settings.BACKUP_MINUTE,
    )


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown()
