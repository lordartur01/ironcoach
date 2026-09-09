"""Scheduler que envia mensajes motivacionales diarios."""
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from db import conexion
from services.mensajes import variante_diaria


logger = logging.getLogger(__name__)


async def tarea_alertas_diarias(app) -> None:
    """Envia el mensaje motivacional del dia a todos los usuarios activos."""
    with conexion() as conn:
        rows = conn.execute(
            """
            SELECT u.id, u.telegram_id, u.nombre, u.rol,
                   COALESCE(p.activa, 1) as activa,
                   COALESCE(p.hora_alerta, '06:00') as hora_alerta
            FROM usuarios u
            LEFT JOIN preferencias_alertas p ON p.usuario_id = u.id
            WHERE u.activo = 1
            """
        ).fetchall()

    if not rows:
        return

    dia = datetime.now().timetuple().tm_yday

    enviados = 0
    for row in rows:
        if not row["activa"]:
            continue
        if row["rol"] == "alumno":
            texto = f"Hola {row['nombre']}.\n\n{variante_diaria(dia)}"
        else:
            texto = f"Buenos dias entrenador {row['nombre']}.\n\n{variante_diaria(dia)}"

        try:
            await app.bot.send_message(chat_id=row["telegram_id"], text=texto)
            enviados += 1
        except Exception as e:
            logger.warning(
                "No se pudo enviar alerta a %s (%s): %s",
                row["nombre"], row["telegram_id"], e,
            )

    logger.info("Alertas diarias enviadas: %d", enviados)


def configurar_scheduler(app, hora: str = "06:00") -> AsyncIOScheduler:
    """Crea y arranca el scheduler con la tarea diaria."""
    try:
        hora_h, hora_m = hora.split(":")
    except ValueError:
        hora_h, hora_m = "6", "0"

    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        tarea_alertas_diarias,
        trigger=CronTrigger(hour=int(hora_h), minute=int(hora_m)),
        args=[app],
        id="alertas_diarias",
        replace_existing=True,
    )
    return scheduler
