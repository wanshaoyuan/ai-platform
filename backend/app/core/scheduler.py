import shutil
import logging
from datetime import datetime, timedelta, date
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


def _do_auto_repay() -> None:
    """
    全自动债务扣减任务（方案 A）。
    每天 00:05（Asia/Shanghai）运行一次。

    触发条件：
    - due_date 的「日」== 今天的「日」（即今天是该账单约定的每月还款日）
    - due_date <= today（月份已到期，含历史补扣）
    - status = 'pending'

    设计要点：
    - 不做全量扫描，只处理今天是还款日的账单，精准对应用户设置的 monthly_repay_day。
    - 使用 due_date <= today 而非 == today，确保服务在还款日停机后，
      次日/次月同日重启仍可补扣漏跑的历史账单。
    - 每笔账单独立 commit，单条失败不影响其他账单继续处理。
    """
    try:
        from app.db import SessionLocal
        from app.models.debt import DebtItem, RepaymentSchedule
        from sqlalchemy import extract, and_

        today = date.today()
        with SessionLocal() as session:
            pending_bills = (
                session.query(RepaymentSchedule)
                .filter(
                    and_(
                        # 只处理今天是约定还款日的账单（日匹配）
                        extract("day", RepaymentSchedule.due_date) == today.day,
                        # 月份已到期（含历史漏扣补偿）
                        RepaymentSchedule.due_date <= today,
                        RepaymentSchedule.status == "pending",
                    )
                )
                .all()
            )

            if not pending_bills:
                logger.info("Auto-repay: no pending bills for %s", today)
                return

            logger.info("Auto-repay: processing %d bill(s) for %s", len(pending_bills), today)

            for bill in pending_bills:
                try:
                    debt = session.get(DebtItem, bill.debt_id)
                    if not debt or not debt.is_active:
                        # 债务已关闭，仅标记账单状态
                        bill.status = "paid"
                        bill.paid_at = datetime.now()
                        session.commit()
                        continue

                    # 扣减剩余本金（不低于 0，防止浮点误差）
                    debt.current_balance = round(
                        max(0.0, debt.current_balance - bill.principal_amount), 2
                    )
                    debt.paid_periods += 1

                    # 全部还清时标记债务为非活跃
                    if debt.paid_periods >= debt.term_months:
                        debt.is_active = False
                        debt.current_balance = 0.0
                        logger.info(
                            "Auto-repay: debt %d '%s' fully paid off.", debt.id, debt.name
                        )

                    bill.status = "paid"
                    bill.paid_at = datetime.now()
                    session.commit()
                    logger.info(
                        "Auto-repay: debt_id=%d period=%d principal=%.2f new_balance=%.2f",
                        debt.id, bill.period_no, bill.principal_amount, debt.current_balance,
                    )
                except Exception as row_err:
                    session.rollback()
                    logger.error(
                        "Auto-repay: failed on schedule_id=%d: %s", bill.id, row_err
                    )

    except Exception as exc:
        logger.error("Auto-repay task crashed: %s", exc)


def start_scheduler() -> None:
    scheduler.add_job(
        _do_backup,
        CronTrigger(hour=settings.BACKUP_HOUR, minute=settings.BACKUP_MINUTE),
        id="daily_backup",
        replace_existing=True,
    )
    # 方案 A：全自动债务还款扣减，每天 00:05 运行
    scheduler.add_job(
        _do_auto_repay,
        CronTrigger(hour=0, minute=5),
        id="daily_auto_repay",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler started. Daily backup at %02d:%02d; auto-repay at 00:05",
        settings.BACKUP_HOUR,
        settings.BACKUP_MINUTE,
    )


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown()
