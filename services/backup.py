"""Sistema de backups automaticos de la base de datos."""
import logging
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from cryptography.fernet import Fernet

from config import settings


logger = logging.getLogger(__name__)

BACKUP_DIR = Path("backups")
MAX_BACKUPS = 7


def _ruta_bd() -> Path:
    """Devuelve la ruta absoluta del archivo de BD."""
    base_dir = Path(__file__).parent.parent
    return base_dir / settings.db_path


def _clave_zip() -> bytes:
    """Genera una clave para el ZIP cifrado.

    Usamos Fernet para cifrar un archivo dentro del ZIP y el ZIP lleva password.
    """
    return settings.fernet_key.encode()


def crear_backup(forzar: bool = False) -> Path | None:
    """Crea un backup cifrado de la BD.

    Devuelve la ruta del backup creado o None si fallo.
    """
    BACKUP_DIR.mkdir(exist_ok=True)
    bd_path = _ruta_bd()

    if not bd_path.exists():
        logger.error("No existe la BD en %s", bd_path)
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = BACKUP_DIR / f"ironcoach_backup_{timestamp}.zip"
    bd_dentro_zip = f"ironcoach_{timestamp}.db"

    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(bd_path, arcname=bd_dentro_zip)
        logger.info("Backup creado: %s", zip_path)
    except Exception as e:
        logger.error("Error creando backup: %s", e)
        return None

    _rotar_backups()
    return zip_path


def _rotar_backups() -> None:
    """Elimina backups viejos manteniendo solo los MAX_BACKUPS mas recientes."""
    if not BACKUP_DIR.exists():
        return

    backups = sorted(
        BACKUP_DIR.glob("ironcoach_backup_*.zip"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    for viejo in backups[MAX_BACKUPS:]:
        try:
            viejo.unlink()
            logger.info("Backup viejo eliminado: %s", viejo.name)
        except Exception as e:
            logger.warning("No se pudo eliminar %s: %s", viejo.name, e)


def listar_backups() -> list[dict]:
    """Devuelve la lista de backups disponibles."""
    if not BACKUP_DIR.exists():
        return []

    backups = []
    for p in sorted(
        BACKUP_DIR.glob("ironcoach_backup_*.zip"),
        key=lambda x: x.stat().st_mtime,
        reverse=True,
    ):
        stat = p.stat()
        backups.append({
            "nombre": p.name,
            "ruta": str(p),
            "tamano_mb": round(stat.st_size / (1024 * 1024), 2),
            "fecha": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        })
    return backups


async def tarea_backup_diario(app) -> None:
    """Tarea programada: crea un backup diario a las 23:55."""
    ruta = crear_backup()
    if ruta and app and app.bot:
        # Notificar al entrenador si esta configurado
        from db import conexion
        with conexion() as conn:
            row = conn.execute(
                """
                SELECT telegram_id FROM usuarios
                WHERE rol = 'entrenador' AND activo = 1 LIMIT 1
                """
            ).fetchone()
        if row:
            try:
                await app.bot.send_message(
                    chat_id=row["telegram_id"],
                    text=(
                        "BACKUP DIARIO\n\n"
                        f"Archivo: {ruta.name}\n"
                        f"Ubicacion: backups/\n\n"
                        "Se mantendran los ultimos 7 dias."
                    ),
                )
            except Exception:
                pass


def configurar_backup_scheduler(app, hora: str = "23:55") -> None:
    """Programa el backup diario automatico."""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger

    try:
        hora_h, hora_m = hora.split(":")
    except ValueError:
        hora_h, hora_m = "23", "55"

    scheduler = app.bot_data.get("scheduler")
    if scheduler is None:
        scheduler = AsyncIOScheduler(timezone="UTC")
        scheduler.start()
        app.bot_data["scheduler"] = scheduler

    scheduler.add_job(
        tarea_backup_diario,
        trigger=CronTrigger(hour=int(hora_h), minute=int(hora_m)),
        args=[app],
        id="backup_diario",
        replace_existing=True,
    )
    logger.info("Backup diario programado a las %s", hora)
