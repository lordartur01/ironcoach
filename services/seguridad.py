"""Controles de acceso de IronCoach."""

from telegram import Update
from telegram.ext import ContextTypes


async def exigir_alumno(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    """
    Comprueba que el usuario sea un alumno activo y vinculado.

    Devuelve True si tiene permiso.
    Devuelve False si debe detenerse el comando.
    """

    from services.auth import alumno_activo

    telegram_id = update.effective_user.id

    alumno = alumno_activo(telegram_id)

    if not alumno:
        await update.message.reply_text(
            "ACCESO NO AUTORIZADO\n\n"
            "Necesitas tener una cuenta de alumno "
            "activa y vinculada a IronCoach.\n\n"
            "Escribe /start para comenzar."
        )
        return False

    # Guardamos información del usuario para los handlers.
    context.user_data["autenticado"] = True
    context.user_data["rol"] = "alumno"
    context.user_data["usuario_id"] = alumno["id"]

    return True


async def exigir_entrenador(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    """
    Comprueba que el usuario sea el entrenador activo.
    """

    from services.auth import entrenador_activo

    telegram_id = update.effective_user.id

    entrenador = entrenador_activo(telegram_id)

    if not entrenador:
        await update.message.reply_text(
            "ACCESO NO AUTORIZADO\n\n"
            "Este comando solo puede ser utilizado "
            "por el entrenador."
        )
        return False

    context.user_data["autenticado"] = True
    context.user_data["rol"] = "entrenador"
    context.user_data["usuario_id"] = entrenador["id"]

    return True

async def exigir_usuario(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    """
    Comprueba que el usuario tenga una cuenta activa
    y vinculada a Telegram.

    Tanto entrenador como alumno pueden registrar
    sus propios datos.
    """

    from services.auth import usuario_activo

    telegram_id = update.effective_user.id

    usuario = usuario_activo(telegram_id)

    if not usuario:
        await update.message.reply_text(
            "ACCESO NO AUTORIZADO\n\n"
            "Necesitas tener una cuenta activa y "
            "vinculada a IronCoach.\n\n"
            "Escribe /start para comenzar."
        )
        return False

    context.user_data["autenticado"] = True
    context.user_data["rol"] = usuario["rol"]
    context.user_data["usuario_id"] = usuario["id"]

    return True