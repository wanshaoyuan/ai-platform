import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import settings
from app.core.scheduler import _do_backup
from app.deps import require_admin
from app.models.user import User

router = APIRouter()


@router.post("/trigger", summary="手动触发一次备份")
def trigger_backup(_: User = Depends(require_admin)):
    try:
        _do_backup()
        return {"message": "备份已触发"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", summary="列出所有备份文件")
def list_backups(_: User = Depends(require_admin)):
    backup_dir: Path = settings.BACKUP_DIR
    if not backup_dir.exists():
        return []
    files = sorted(backup_dir.glob("ai_platform_*.db"), key=lambda f: f.stat().st_mtime, reverse=True)
    return [
        {
            "filename": f.name,
            "size_bytes": f.stat().st_size,
            "created_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
        }
        for f in files
    ]
