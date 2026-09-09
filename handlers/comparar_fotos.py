"""Handlers para comparar fotos antes/despues."""
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from services.auth import obtener_usuario
from services.usuarios import obtener_alumno_por_id
from services.comparar import (
    TIPOS_VALIDOS,
    obtener_extremas_por_tipo,
    listar_tipos_disponibles,
    dias_entre,
)


ESPERANDO_TIPO = 1


def _tipo_bonito(tipo: str) -> str:
    return tipo.replace("_", " ").title()


async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Cancelado.")
    context.user_data.clear()
    return ConversationHandler.END


async def cmd_comparar_fotos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia la comparacion para el alumno actual."""
    usuario = obtener_usuario(update.effective_user.id)
    if not usuario:
        await update.message.reply_text(
            "Necesitas una cuenta activa. Escribe /start."
        )
        return ConversationHandler.END

    context.user_data.clear()
    context.user_data["objetivo_usuario_id"] = usuario["id"]
    context.user_data["es_entrenador"] = False

    tipos = listar_tipos_disponibles(usuario["id"])
    if not tipos:
        await update.message.reply_text(
            "Aun no tienes fotos registradas.\n"
            "Usa /foto para subir la primera."
        )
        return ConversationHandler.END

    listado = "\n".join(f"  - {t}" for t in tipos)
    await update.message.reply_text(
        "COMPARACION DE FOTOS\n\n"
        f"Tus tipos disponibles:\n{listado}\n\n"
        "Escribe cual quieres comparar:"
    )
    return ESPERANDO_TIPO


async def cmd_comparar_fotos_alumno(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia la comparacion para un alumno concreto (solo entrenador)."""
    entrenador = obtener_usuario(update.effective_user.id)
    if not entrenador or entrenador["rol"] != "entrenador":
        await update.message.reply_text("Solo el entrenador puede usar este comando.")
        return ConversationHandler.END

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            "Uso: /comparar_fotos_alumno NUM (ej: /comparar_fotos_alumno 1)"
        )
        return ConversationHandler.END

    alumno = obtener_alumno_por_id(int(context.args[0]))
    if not alumno:
        await update.message.reply_text("No existe ese alumno.")
        return ConversationHandler.END

    context.user_data.clear()
    context.user_data["objetivo_usuario_id"] = alumno["id"]
    context.user_data["es_entrenador"] = True
    context.user_data["alumno_nombre"] = alumno["nombre"]

    tipos = listar_tipos_disponibles(alumno["id"])
    if not tipos:
        await update.message.reply_text(
            f"{alumno['nombre']} aun no tiene fotos registradas."
        )
        return ConversationHandler.END

    listado = "\n".join(f"  - {t}" for t in tipos)
    await update.message.reply_text(
        f"COMPARACION DE FOTOS DE {alumno['nombre'].upper()}\n\n"
        f"Tipos disponibles:\n{listado}\n\n"
        "Escribe cual quieres comparar:"
    )
    return ESPERANDO_TIPO


async def recibir_tipo_y_comparar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el tipo y envia la comparacion."""
    tipo = update.message.text.strip().lower()

    if tipo not in TIPOS_VALIDOS:
        await update.message.reply_text(
            f"Tipo no valido. Opciones: {', '.join(TIPOS_VALIDOS)}"
        )
        return ESPERANDO_TIPO

    usuario_id = context.user_data["objetivo_usuario_id"]
    es_entrenador = context.user_data["es_entrenador"]

    antigua, reciente = obtener_extremas_por_tipo(usuario_id, tipo)

    if not antigua and not reciente:
        await update.message.reply_text(
            f"No hay fotos de tipo '{tipo}'."
        )
        return ConversationHandler.END

    if not antigua:
        await update.message.reply_text(
            f"Solo hay 1 foto de tipo '{tipo}'.\n"
            "Necesitas al menos 2 para comparar.\n"
            "Usa /foto para subir otra."
        )
        return ConversationHandler.END

    tipo_bonito = _tipo_bonito(tipo)
    dias = dias_entre(antigua["fecha"], reciente["fecha"])

    cabecera = (
        f"COMPARACION: {tipo_bonito}\n\n"
        f"ANTIGUA: {antigua['fecha'][:10]}\n"
        f"RECIENTE: {reciente['fecha'][:10]}\n"
        f"Diferencia: {dias} dias\n\n"
        "Antigua:"
    )

    await update.message.reply_photo(
        photo=antigua["telegram_file_id"],
        caption=cabecera,
    )

    await update.message.reply_photo(
        photo=reciente["telegram_file_id"],
        caption=(
            f"Reciente: {reciente['fecha'][:10]}\n"
            f"({dias} dias despues)"
        ),
    )

    return ConversationHandler.END


def registrar(app):
    """Registra los handlers de comparacion en la aplicacion."""
    # Comparacion del alumno sobre sus propias fotos
    app.add_handler(CommandHandler("comparar_fotos", cmd_comparar_fotos))

    # Comparacion del entrenador sobre fotos de un alumno
    app.add_handler(CommandHandler("comparar_fotos_alumno", cmd_comparar_fotos_alumno))