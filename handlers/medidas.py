"""Handler conversacional para registrar medidas corporales."""

from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from db import conexion
from services.auth import obtener_usuario
from services.alertas import notificar_entrenador


# Estado
PIDIENDO_MEDIDAS = 1


async def cmd_medidas(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Inicia el registro de medidas."""

    from services.seguridad import exigir_usuario

    if not await exigir_usuario(update, context):
        return ConversationHandler.END

    context.user_data.clear()

    telegram_id = update.effective_user.id
    usuario = obtener_usuario(telegram_id)

    if not usuario:
        await update.message.reply_text(
            "Necesitas iniciar sesion primero. Escribe /start."
        )
        return ConversationHandler.END

    await update.message.reply_text(
        f"Vamos a registrar medidas para {usuario['nombre']}.\n\n"
        "Registro de MEDIDAS CORPORALES\n\n"
        "Envia los valores separados por comas en este orden:\n"
        "peso(kg), grasa(%), pecho(cm), cintura(cm), abdomen(cm),\n"
        "cadera(cm), brazo(cm), muslo(cm), pantorrilla(cm), hombros(cm)\n\n"
        "Ejemplo:\n"
        "72.5, 14.2, 100, 82, 78, 95, 38, 55, 38, 120\n\n"
        "Puedes escribir CANCELAR para salir."
    )

    return PIDIENDO_MEDIDAS


async def guardar_medidas(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Procesa las medidas y las guarda."""

    texto = update.message.text.strip()

    if texto.upper() == "CANCELAR":
        await update.message.reply_text("Cancelado.")
        return ConversationHandler.END

    telegram_id = update.effective_user.id
    usuario = obtener_usuario(telegram_id)

    if not usuario:
        await update.message.reply_text(
            "Necesitas iniciar sesion primero. /start"
        )
        return ConversationHandler.END

    partes = [p.strip() for p in texto.split(",")]

    campos = [
        "peso_kg",
        "grasa_pct",
        "pecho",
        "cintura",
        "abdomen",
        "cadera",
        "brazo",
        "muslo",
        "pantorrilla",
        "hombros",
    ]

    valores = []

    if len(partes) < 3:
        await update.message.reply_text(
            "Faltan datos.\n"
            "Necesito al menos peso, grasa y cintura."
        )
        return PIDIENDO_MEDIDAS

    try:
        for i, campo in enumerate(campos):
            if i < len(partes) and partes[i]:
                valores.append(float(partes[i]))
            else:
                valores.append(None)

    except ValueError:
        await update.message.reply_text(
            "Hay un valor que no es numero.\n"
            "Revisa los datos y vuelve a enviarlos."
        )
        return PIDIENDO_MEDIDAS

    # ---------------------------------------------------------
    # GUARDAR EN BASE DE DATOS
    # ---------------------------------------------------------

    with conexion() as conn:
        conn.execute(
            """
            INSERT INTO medidas_corporales
                (
                    usuario_id,
                    peso_kg,
                    grasa_pct,
                    pecho,
                    cintura,
                    abdomen,
                    cadera,
                    brazo,
                    muslo,
                    pantorrilla,
                    hombros
                )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                usuario["id"],
                *valores,
            ),
        )

    # ---------------------------------------------------------
    # NOTIFICAR AL ENTRENADOR
    # ---------------------------------------------------------

    if usuario["rol"] == "alumno":

        await notificar_entrenador(
            context.application,
            (
                "📏 NUEVAS MEDIDAS\n\n"
                f"Alumno: {usuario['nombre']}\n"
                f"Peso: {valores[0]} kg\n"
                f"Grasa: {valores[1]} %\n"
                f"Cintura: {valores[3]} cm"
            ),
        )

    # ---------------------------------------------------------
    # CONFIRMAR AL USUARIO
    # ---------------------------------------------------------

    resumen = (
        "Medidas guardadas\n\n"
        f"Peso: {valores[0]} kg\n"
        f"Grasa: {valores[1]} %\n"
        f"Pecho: {valores[2]} cm\n"
        f"Cintura: {valores[3]} cm\n"
        f"Abdomen: {valores[4]} cm\n"
        f"Cadera: {valores[5]} cm\n"
        f"Brazo: {valores[6]} cm\n"
        f"Muslo: {valores[7]} cm\n"
        f"Pantorrilla: {valores[8]} cm\n"
        f"Hombros: {valores[9]} cm"
    )

    await update.message.reply_text(resumen)

    return ConversationHandler.END


def handler() -> ConversationHandler:
    """Devuelve el ConversationHandler de medidas."""

    return ConversationHandler(
        entry_points=[
            CommandHandler(
                "medidas",
                cmd_medidas,
            )
        ],
        states={
            PIDIENDO_MEDIDAS: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    guardar_medidas,
                )
            ],
        },
        fallbacks=[
            CommandHandler(
                "cancel",
                lambda u, c: ConversationHandler.END,
            )
        ],
        allow_reentry=True,
    )