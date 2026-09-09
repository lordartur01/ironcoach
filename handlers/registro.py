"""Handlers de inicio y vinculación de alumnos mediante invitación."""

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from services.auth import (
    es_pin_maestro,
    registrar_entrenador,
    usuario_existe,
    obtener_usuario,
)
from services.usuarios import vincular_invitacion


# Estados de la conversación
ESPERANDO_CODIGO_INVITACION = 1
ESPERANDO_PIN_ENTRENADOR = 2


async def cmd_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Punto de entrada principal de IronCoach."""

    telegram_id = update.effective_user.id

    # Limpiamos datos temporales de conversaciones anteriores.
    context.user_data.clear()

    # ---------------------------------------------------------
    # 1. Usuario ya registrado
    # ---------------------------------------------------------

    if usuario_existe(telegram_id):

        usuario = obtener_usuario(telegram_id)

        if not usuario:
            await update.message.reply_text(
                "No pude recuperar los datos de tu cuenta."
            )
            return ConversationHandler.END

        nombre = usuario["nombre"]
        rol = usuario["rol"]

        if rol == "entrenador":
            await update.message.reply_text(
                f"Bienvenido entrenador {nombre}.\n\n"
                "Comandos disponibles:\n"
                "/alumnos - Ver alumnos\n"
                "/registrar_alumno - Invitar alumno\n"
                "/ver_alumno NUM - Ver ficha\n"
                "/resetear_pin NUM - Cambiar PIN\n"
                "/como_voy - Ver tu progreso"
            )

        else:
            await update.message.reply_text(
                f"Hola {nombre}, bienvenido de vuelta.\n\n"
                "Comandos disponibles:\n"
                "/entrenamiento - Registrar gym\n"
                "/cardio - Registrar running\n"
                "/medidas - Registrar medidas\n"
                "/como_voy - Ver tu progreso"
            )

        return ConversationHandler.END

    # ---------------------------------------------------------
    # 2. Usuario nuevo
    # ---------------------------------------------------------

    await update.message.reply_text(
        "BIENVENIDO A IRONCOACH\n\n"
        "Para comenzar necesitas un código de invitación "
        "proporcionado por tu entrenador.\n\n"
        "Escribe el código de invitación:"
    )

    return ESPERANDO_CODIGO_INVITACION


async def recibir_codigo_invitacion(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Recibe y valida el código de invitación."""

    codigo = update.message.text.strip()

    # Permitir cancelar.
    if codigo.upper() == "CANCELAR":
        await update.message.reply_text(
            "Operación cancelada.\n\n"
            "Escribe /start cuando quieras intentarlo nuevamente."
        )
        context.user_data.clear()
        return ConversationHandler.END

    if not codigo:
        await update.message.reply_text(
            "El código no puede estar vacío.\n\n"
            "Escribe el código de invitación:"
        )
        return ESPERANDO_CODIGO_INVITACION

    telegram_id = update.effective_user.id

    # Intentar vincular la invitación.
    alumno = vincular_invitacion(
        codigo=codigo,
        telegram_id=telegram_id,
    )

    if not alumno:
        await update.message.reply_text(
            "CÓDIGO NO VÁLIDO\n\n"
            "El código no existe, ya fue utilizado "
            "o no está disponible.\n\n"
            "Solicita un nuevo código a tu entrenador."
        )
        return ESPERANDO_CODIGO_INVITACION

    # Vinculación correcta.
    context.user_data["autenticado"] = True
    context.user_data["rol"] = "alumno"
    context.user_data["usuario_id"] = alumno["id"]

    await update.message.reply_text(
        f"¡Bienvenido a IronCoach, {alumno['nombre']}!\n\n"
        "Tu cuenta ha sido vinculada correctamente.\n\n"
        "Ya puedes comenzar a registrar tus entrenamientos.\n\n"
        "Usa /help para ver los comandos disponibles."
    )

    context.user_data.clear()

    return ConversationHandler.END


async def recibir_pin_entrenador(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Este estado queda reservado para el acceso inicial
    del entrenador mediante PIN maestro.
    """

    texto = update.message.text.strip()

    if texto.upper() == "CANCELAR":
        await update.message.reply_text(
            "Operación cancelada."
        )
        return ConversationHandler.END

    if not es_pin_maestro(texto):
        await update.message.reply_text(
            "PIN incorrecto.\n\n"
            "Inténtalo nuevamente o escribe CANCELAR."
        )
        return ESPERANDO_PIN_ENTRENADOR

    telegram_id = update.effective_user.id

    if not usuario_existe(telegram_id):

        registrar_entrenador(
            telegram_id=telegram_id,
            nombre=update.effective_user.first_name or "Entrenador",
            pin_texto=texto,
        )

        await update.message.reply_text(
            "Entrenador registrado correctamente.\n\n"
            "Bienvenido a IronCoach."
        )

    else:
        await update.message.reply_text(
            "Bienvenido entrenador."
        )

    context.user_data["autenticado"] = True
    context.user_data["rol"] = "entrenador"

    return ConversationHandler.END


async def cancelar(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Cancela cualquier conversación activa."""

    await update.message.reply_text(
        "Operación cancelada.\n\n"
        "Escribe /start cuando quieras comenzar."
    )

    context.user_data.clear()

    return ConversationHandler.END

