"""Handler conversacional para registrar entrenamientos de gym."""
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

from db import conexion
from services.auth import obtener_usuario
from services.alertas import notificar_entrenador


# Estados
PIDIENDO_RUTINA = 1
PIDIENDO_EJERCICIOS = 2


async def cmd_entrenamiento(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    from services.seguridad import exigir_usuario

    if not await exigir_usuario(update, context):
        return ConversationHandler.END

    """Pregunta la rutina realizada."""
    context.user_data.clear()
    context.user_data["ejercicios"] = []

    await update.message.reply_text(
        "Registro de ENTRENAMIENTO DE GIMNASIO\n\n"
        "Paso 1 de 2: Que rutina hiciste?\n"
        "Escribe el nombre o escribe LIBRE si fue a eleccion propia.\n\n"
        "Ejemplos:\n"
        "  Tren Superior\n"
        "  Tren Inferior\n"
        "  Espalda\n"
        "  Cuerpo Completo\n"
        "  LIBRE"
    )
    return PIDIENDO_RUTINA


async def pedir_ejercicios(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe la rutina y pide los ejercicios."""
    texto = update.message.text.strip()

    with conexion() as conn:
        if texto.upper() == "LIBRE":
            context.user_data["rutina_id"] = None
            context.user_data["rutina_nombre"] = "Libre"
        else:
            row = conn.execute(
                "SELECT id, nombre FROM rutinas WHERE nombre LIKE ?",
                (f"%{texto}%",),
            ).fetchone()
            if row:
                context.user_data["rutina_id"] = row["id"]
                context.user_data["rutina_nombre"] = row["nombre"]
            else:
                context.user_data["rutina_id"] = None
                context.user_data["rutina_nombre"] = texto

    await update.message.reply_text(
        f"Rutina: {context.user_data['rutina_nombre']}\n\n"
        "Paso 2 de 2: Envia tus ejercicios.\n"
        "Formato por linea: EJERCICIO | SERIES x REPS x PESO\n\n"
        "Ejemplos:\n"
        "  Sentadilla | 4x10x80\n"
        "  Press banca | 3x8x60\n"
        "  Peso muerto | 1x5x120\n\n"
        "Cuando termines escribe LISTO.\n"
        "Puedes escribir CANCELAR para salir sin guardar."
    )
    return PIDIENDO_EJERCICIOS


async def procesar_ejercicios(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe lineas de ejercicios hasta que el usuario escriba LISTO."""
    texto = update.message.text.strip()

    if texto.upper() == "CANCELAR":
        await update.message.reply_text("Cancelado.")
        return ConversationHandler.END

    if texto.upper() == "LISTO":
        return await guardar_entrenamiento(update, context)

    lineas = [l.strip() for l in texto.split("\n") if l.strip()]
    errores = []
    agregados = []

    for linea in lineas:
        if "|" not in linea:
            errores.append(linea)
            continue
        nombre_ej, resto = [p.strip() for p in linea.split("|", 1)]
        partes = [p.strip() for p in resto.lower().replace("x", " ").split()]
        try:
            if len(partes) >= 3:
                series = int(partes[0])
                reps = int(partes[1])
                peso = float(partes[2])
            elif len(partes) == 2:
                series = int(partes[0])
                reps = int(partes[1])
                peso = None
            else:
                raise ValueError
        except ValueError:
            errores.append(linea)
            continue

        context.user_data["ejercicios"].append({
            "nombre": nombre_ej,
            "series": series,
            "reps": reps,
            "peso": peso,
        })
        agregados.append(f"  {nombre_ej}: {series}x{reps} @ {peso or '-'}kg")

    if errores:
        await update.message.reply_text(
            "Lineas con formato incorrecto (ignoradas):\n"
            + "\n".join(f"  - {e}" for e in errores)
        )

    if agregados:
        await update.message.reply_text(
            "Ejercicios agregados:\n" + "\n".join(agregados)
            + "\n\nEnvia mas lineas o escribe LISTO para guardar."
        )

    return PIDIENDO_EJERCICIOS


async def guardar_entrenamiento(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda la sesion completa con sus series."""
    ejercicios = context.user_data.get("ejercicios", [])
    if not ejercicios:
        await update.message.reply_text(
            "No agregaste ejercicios. Envia al menos uno o CANCELAR."
        )
        return PIDIENDO_EJERCICIOS

    telegram_id = update.effective_user.id
    usuario = obtener_usuario(telegram_id)
    if not usuario:
        await update.message.reply_text("Necesitas iniciar sesion. /start")
        return ConversationHandler.END

    rutina_id = context.user_data.get("rutina_id")
    rutina_nombre = context.user_data.get("rutina_nombre", "Libre")

    with conexion() as conn:
        cur = conn.execute(
            "INSERT INTO sesiones (usuario_id, rutina_id) VALUES (?, ?)",
            (usuario["id"], rutina_id),
        )
        sesion_id = cur.lastrowid

        resumen_lineas = []
        for ej in ejercicios:
            # Buscar id del ejercicio (crear si no existe)
            row = conn.execute(
                "SELECT id FROM ejercicios WHERE nombre = ?",
                (ej["nombre"],),
            ).fetchone()
            if row:
                ejercicio_id = row["id"]
            else:
                cur2 = conn.execute(
                    "INSERT INTO ejercicios (nombre, categoria) VALUES (?, ?)",
                    (ej["nombre"], "fuerza"),
                )
                ejercicio_id = cur2.lastrowid

            conn.execute(
                """
                INSERT INTO sesion_series
                    (sesion_id, ejercicio_id, numero_serie, reps, peso_kg)
                VALUES (?, ?, ?, ?, ?)
                """,
                (sesion_id, ejercicio_id, ej["series"], ej["reps"], ej["peso"]),
            )
            resumen_lineas.append(
                f"  {ej['nombre']}: {ej['series']}x{ej['reps']} @ {ej['peso'] or '-'}kg"
            )

    # ---------------------------------------------------------
    # NOTIFICAR AL ENTRENADOR
    # ---------------------------------------------------------

    if usuario["rol"] == "alumno":

        await notificar_entrenador(
            context.application,
            (
                "🏋️ NUEVO ENTRENAMIENTO\n\n"
                f"Alumno: {usuario['nombre']}\n"
                f"Rutina: {rutina_nombre}\n\n"
                "Ejercicios:\n"
                + "\n".join(resumen_lineas)
            ),
        )

    resumen = (
        f"Entrenamiento guardado\n\n"
        f"Rutina: {rutina_nombre}\n\n"
        + "\n".join(resumen_lineas)
    )
    await update.message.reply_text(resumen)
    return ConversationHandler.END


def handler() -> ConversationHandler:
    """Devuelve el ConversationHandler listo para registrar en el bot."""
    return ConversationHandler(
        entry_points=[CommandHandler("entrenamiento", cmd_entrenamiento)],
        states={
            PIDIENDO_RUTINA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, pedir_ejercicios)
            ],
            PIDIENDO_EJERCICIOS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_ejercicios)
            ],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        allow_reentry=True,
    )
