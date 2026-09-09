"""Handler conversacional para registrar sesiones de cardio / running."""
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

from db import conexion
from services.auth import obtener_usuario
from services.alertas import notificar_entrenador


# Estados
PIDIENDO_DISTANCIA = 1
PIDIENDO_TIEMPO = 2
PIDIENDO_FC = 3
PIDIENDO_CADENCIA = 4


async def cmd_cardio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    from services.seguridad import exigir_usuario

    if not await exigir_usuario(update, context):
        return ConversationHandler.END

    """Inicia el registro de cardio paso a paso."""
    context.user_data.clear()
    await update.message.reply_text(
        "Registro de CARDIO / RUNNING\n\n"
        "Paso 1 de 4: Distancia\n"
        "Cuantos kilometros recorriste?\n"
        "Ejemplo: 5.0"
    )
    return PIDIENDO_DISTANCIA


async def pedir_tiempo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe la distancia y pide el tiempo."""
    texto = update.message.text.strip().replace(",", ".")
    try:
        distancia = float(texto)
        if distancia <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Numero no valido. Envialo asi: 5.0")
        return PIDIENDO_DISTANCIA

    context.user_data["distancia_km"] = distancia
    await update.message.reply_text(
        f"Distancia: {distancia} km\n\n"
        "Paso 2 de 4: Tiempo total\n"
        "Cuantos minutos tardaste?\n"
        "Ejemplo: 25 (si fueron 25 minutos)"
    )
    return PIDIENDO_TIEMPO


async def pedir_fc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el tiempo y pide la FC promedio."""
    texto = update.message.text.strip().replace(",", ".")
    try:
        tiempo = float(texto)
        if tiempo <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Numero no valido. Envialo asi: 25")
        return PIDIENDO_TIEMPO

    context.user_data["tiempo_min"] = tiempo

    # Calculo de ritmo
    distancia = context.user_data["distancia_km"]
    ritmo = tiempo / distancia
    minutos = int(ritmo)
    segundos = int((ritmo - minutos) * 60)
    context.user_data["ritmo_promedio"] = f"{minutos}:{segundos:02d} min/km"

    await update.message.reply_text(
        f"Tiempo: {tiempo} min\n"
        f"Ritmo promedio: {minutos}:{segundos:02d} min/km\n\n"
        "Paso 3 de 4: Frecuencia cardiaca\n"
        "Cual fue tu FC promedio? (y la maxima si la recuerdas)\n"
        "Ejemplo: 145, 168\n"
        "O escribe SOLO si no tienes datos."
    )
    return PIDIENDO_FC


async def pedir_cadencia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe la FC y pide cadencia."""
    texto = update.message.text.strip()
    fc_promedio = fc_max = None

    if texto.upper() != "SOLO":
        partes = [p.strip() for p in texto.split(",")]
        try:
            if len(partes) >= 1 and partes[0]:
                fc_promedio = int(partes[0])
            if len(partes) >= 2 and partes[1]:
                fc_max = int(partes[1])
        except ValueError:
            await update.message.reply_text("Numeros no validos. Intenta de nuevo.")
            return PIDIENDO_FC

    context.user_data["fc_promedio"] = fc_promedio
    context.user_data["fc_max"] = fc_max

    await update.message.reply_text(
        f"FC promedio: {fc_promedio or '-'}\n"
        f"FC maxima: {fc_max or '-'}\n\n"
        "Paso 4 de 4: Cadencia\n"
        "Pasos por minuto (spm). Si no la sabes escribe 0.\n"
        "Ejemplo: 80"
    )
    return PIDIENDO_CADENCIA


async def guardar_cardio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe cadencia, calcula VO2 estimado y guarda todo."""
    texto = update.message.text.strip()
    try:
        cadencia = int(texto) if texto and texto != "0" else None
    except ValueError:
        await update.message.reply_text("Numero no valido. Envialo asi: 80")
        return PIDIENDO_CADENCIA

    telegram_id = update.effective_user.id
    usuario = obtener_usuario(telegram_id)
    if not usuario:
        await update.message.reply_text("Necesitas iniciar sesion. /start")
        return ConversationHandler.END

    distancia = context.user_data["distancia_km"]
    tiempo = context.user_data["tiempo_min"]
    ritmo = context.user_data["ritmo_promedio"]
    fc_promedio = context.user_data["fc_promedio"]
    fc_max = context.user_data["fc_max"]

    # VO2 estimado (formula de Daniels simplificada para ritmo en min/km)
    # VO2 = -4.6 + 0.182258 * (velocidad_m/min) + 0.000104 * (velocidad_m/min)^2
    velocidad_m_min = (distancia * 1000) / tiempo
    vo2 = -4.6 + 0.182258 * velocidad_m_min + 0.000104 * (velocidad_m_min ** 2)

    with conexion() as conn:
        conn.execute(
            """
            INSERT INTO registros_cardio
                (usuario_id, distancia_km, tiempo_min, ritmo_promedio,
                 fc_promedio, fc_max, cadencia, vo2_estimado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (usuario["id"], distancia, tiempo, ritmo,
             fc_promedio, fc_max, cadencia, round(vo2, 2)),
        )

    # ---------------------------------------------------------
    # NOTIFICAR AL ENTRENADOR
    # ---------------------------------------------------------

    if usuario["rol"] == "alumno":

        await notificar_entrenador(
            context.application,
            (
                "🏃 NUEVO CARDIO\n\n"
                f"Alumno: {usuario['nombre']}\n"
                f"Distancia: {distancia} km\n"
                f"Tiempo: {tiempo} min\n"
                f"Ritmo: {ritmo}\n"
                f"FC promedio: {fc_promedio or '-'}\n"
                f"FC máxima: {fc_max or '-'}\n"
                f"Cadencia: {cadencia or '-'} spm\n"
                f"VO2 estimado: {round(vo2, 1)}"
            ),
        )

    resumen = (
        "Cardio registrado\n\n"
        f"  Distancia: {distancia} km\n"
        f"  Tiempo: {tiempo} min\n"
        f"  Ritmo: {ritmo}\n"
        f"  FC promedio: {fc_promedio or '-'}\n"
        f"  FC maxima: {fc_max or '-'}\n"
        f"  Cadencia: {cadencia or '-'} spm\n"
        f"  VO2 estimado: {round(vo2, 1)}"
    )
    await update.message.reply_text(resumen)
    return ConversationHandler.END


def handler() -> ConversationHandler:
    """Devuelve el ConversationHandler listo para registrar en el bot."""
    return ConversationHandler(
        entry_points=[CommandHandler("cardio", cmd_cardio)],
        states={
            PIDIENDO_DISTANCIA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, pedir_tiempo)
            ],
            PIDIENDO_TIEMPO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, pedir_fc)
            ],
            PIDIENDO_FC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, pedir_cadencia)
            ],
            PIDIENDO_CADENCIA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, guardar_cardio)
            ],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        allow_reentry=True,
    )
