"""Punto de entrada principal del bot IronCoach."""
import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import settings
from db import init_db
from handlers.registro import (
    cmd_start,
    recibir_codigo_invitacion,
    cancelar,
    ESPERANDO_CODIGO_INVITACION,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde al comando /help."""
    await update.message.reply_text(
        "IronCoach - Ayuda\n\n"
        "Comandos:\n"
        "  /start - Iniciar sesion o registrarse\n"
        "  /help - Ver esta ayuda\n"
        "  /cancel - Cancelar operacion en curso\n"
        "  /medidas - Registrar medidas corporales\n"
        "  /entrenamiento - Registrar entrenamiento de gym\n"
        "  /cardio - Registrar cardio / running\n"
        "  /foto - Registrar foto de progreso\n"
        "  /como_voy - Ver tu progreso\n"
        "  /alumnos - (Entrenador) Ver lista de alumnos\n"
        "  /registrar_alumno - (Entrenador) Invitar alumno\n"
        "  /ver_alumno NUM - (Entrenador) Ver ficha de alumno\n"
        "  /eliminar_alumno NUM - (Entrenador) Desactivar alumno\n"
        "  /reactivar_alumno NUM - (Entrenador) Reactivar alumno\n"
        "  /fotos_alumno NUM - Ver fotos de un alumno\n"
        "  /ver_foto_alumno ALUMNO FOTO - Ver una foto\n"
        "  /comparar_fotos - Comparar tus fotos antes/despues\n"
        "  /comparar_fotos_alumno NUM - (Entrenador) Comparar fotos de alumno\n"
        "  /alertas - Ver estado de alertas diarias\n"
        "  /activar_alertas / /desactivar_alertas\n"
        "  /hora_alerta HH:MM - Cambiar hora del mensaje\n"
    )


async def msg_no_entendido(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde a mensajes que no reconoce."""
    await update.message.reply_text(
        "No entendi tu mensaje. Escribe /start o /help."
    )


async def acciones_post_init(app) -> None:
    """Arranca el scheduler de alertas y backups al iniciar el bot."""
    from services.scheduler import configurar_scheduler
    from services.backup import configurar_backup_scheduler

    scheduler = configurar_scheduler(app, hora=settings.hora_alerta)
    scheduler.start()
    app.bot_data["scheduler"] = scheduler
    logger.info("Scheduler de alertas arrancado. Hora: %s", settings.hora_alerta)

    configurar_backup_scheduler(app, hora="23:55")


async def acciones_post_shutdown(app) -> None:
    """Detiene el scheduler al apagar el bot."""
    scheduler = app.bot_data.get("scheduler")
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler detenido.")


async def cmd_alertas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra el estado de las alertas del usuario."""
    from db import conexion
    from services.auth import obtener_usuario

    usuario = obtener_usuario(update.effective_user.id)
    if not usuario:
        await update.message.reply_text(
            "Necesitas una cuenta activa. Escribe /start."
        )
        return

    with conexion() as conn:
        row = conn.execute(
            """
            SELECT activa, hora_alerta
            FROM preferencias_alertas
            WHERE usuario_id = ?
            """,
            (usuario["id"],),
        ).fetchone()

    activa = bool(row["activa"]) if row else True
    hora = row["hora_alerta"] if row else "06:00"

    estado = "ACTIVADAS" if activa else "DESACTIVADAS"
    await update.message.reply_text(
        f"ALERTAS DIARIAS\n\n"
        f"Estado: {estado}\n"
        f"Hora: {hora}\n\n"
        "Comandos:\n"
        "/activar_alertas - Activar\n"
        "/desactivar_alertas - Desactivar\n"
        "/hora_alerta HH:MM - Cambiar hora (ej: /hora_alerta 07:30)"
    )


async def cmd_activar_alertas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from db import conexion
    from services.auth import obtener_usuario

    usuario = obtener_usuario(update.effective_user.id)
    if not usuario:
        await update.message.reply_text("Necesitas una cuenta activa. /start")
        return

    with conexion() as conn:
        conn.execute(
            """
            INSERT INTO preferencias_alertas (usuario_id, activa, hora_alerta)
            VALUES (?, 1, '06:00')
            ON CONFLICT(usuario_id) DO UPDATE SET activa = 1
            """,
            (usuario["id"],),
        )
    await update.message.reply_text("Alertas ACTIVADAS.")


async def cmd_desactivar_alertas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from db import conexion
    from services.auth import obtener_usuario

    usuario = obtener_usuario(update.effective_user.id)
    if not usuario:
        await update.message.reply_text("Necesitas una cuenta activa. /start")
        return

    with conexion() as conn:
        conn.execute(
            """
            INSERT INTO preferencias_alertas (usuario_id, activa, hora_alerta)
            VALUES (?, 0, '06:00')
            ON CONFLICT(usuario_id) DO UPDATE SET activa = 0
            """,
            (usuario["id"],),
        )
    await update.message.reply_text("Alertas DESACTIVADAS.")


async def cmd_hora_alerta(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from db import conexion
    from services.auth import obtener_usuario

    usuario = obtener_usuario(update.effective_user.id)
    if not usuario:
        await update.message.reply_text("Necesitas una cuenta activa. /start")
        return

    if not context.args:
        await update.message.reply_text(
            "Uso: /hora_alerta HH:MM (ej: /hora_alerta 07:30)"
        )
        return

    hora = context.args[0]
    if ":" not in hora or len(hora) != 5:
        await update.message.reply_text("Formato incorrecto. Usa HH:MM (ej: 07:30)")
        return

    with conexion() as conn:
        conn.execute(
            """
            INSERT INTO preferencias_alertas (usuario_id, activa, hora_alerta)
            VALUES (?, 1, ?)
            ON CONFLICT(usuario_id) DO UPDATE SET hora_alerta = ?
            """,
            (usuario["id"], hora, hora),
        )
    await update.message.reply_text(f"Hora de alerta cambiada a {hora}.")


async def cmd_backup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fuerza un backup manual (solo entrenador)."""
    from services.auth import obtener_usuario
    from services.backup import crear_backup

    usuario = obtener_usuario(update.effective_user.id)
    if not usuario or usuario["rol"] != "entrenador":
        await update.message.reply_text(
            "Solo el entrenador puede forzar backups."
        )
        return

    await update.message.reply_text("Creando backup...")
    ruta = crear_backup(forzar=True)
    if ruta:
        await update.message.reply_text(
            f"Backup creado.\n\nArchivo: {ruta.name}\nUbicacion: backups/"
        )
    else:
        await update.message.reply_text("Error creando backup. Revisa los logs.")


async def cmd_backups(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lista los backups disponibles (solo entrenador)."""
    from services.auth import obtener_usuario
    from services.backup import listar_backups

    usuario = obtener_usuario(update.effective_user.id)
    if not usuario or usuario["rol"] != "entrenador":
        await update.message.reply_text(
            "Solo el entrenador puede ver los backups."
        )
        return

    backups = listar_backups()
    if not backups:
        await update.message.reply_text(
            "No hay backups aun.\nUsa /backup para crear uno."
        )
        return

    lineas = [f"BACKUPS DISPONIBLES ({len(backups)})", ""]
    for b in backups:
        lineas.append(
            f"  - {b['nombre']}\n"
            f"    {b['tamano_mb']} MB - {b['fecha']}"
        )
    await update.message.reply_text("\n".join(lineas))


def main() -> None:
    """Arranca el bot."""
    if not settings.telegram_token:
        print("ERROR: TELEGRAM_TOKEN no esta configurado en .env")
        return

    init_db()

    app = (
        Application.builder()
        .token(settings.telegram_token)
        .post_init(acciones_post_init)
        .post_shutdown(acciones_post_shutdown)
        .build()
    )

    # Conversacion principal de login/registro
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", cmd_start)
    ],

        states={
            ESPERANDO_CODIGO_INVITACION: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    recibir_codigo_invitacion
            )
        ],
    },

    fallbacks=[
        CommandHandler("cancel", cancelar)
    ],

    allow_reentry=True,
)
    app.add_handler(conv)

    # Handlers de registro (medidas, gym, cardio)
    from handlers.medidas import handler as medidas_h
    from handlers.entrenamiento import handler as entrenamiento_h
    from handlers.cardio import handler as cardio_h
    from handlers.foto import handler as foto_h

    app.add_handler(medidas_h())
    app.add_handler(entrenamiento_h())
    app.add_handler(cardio_h())
    app.add_handler(foto_h())
    # Handler de consulta de progreso
    from handlers.consulta import registrar as registrar_consulta
    registrar_consulta(app)

    # Handlers exclusivos del entrenador
    from handlers.entrenador import registrar as registrar_entrenador
    registrar_entrenador(app)

    # Comparacion de fotos
    from handlers.comparar_fotos import registrar as registrar_comparar
    registrar_comparar(app)


    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("alertas", cmd_alertas))
    app.add_handler(CommandHandler("activar_alertas", cmd_activar_alertas))
    app.add_handler(CommandHandler("desactivar_alertas", cmd_desactivar_alertas))
    app.add_handler(CommandHandler("hora_alerta", cmd_hora_alerta))
    app.add_handler(CommandHandler("backup", cmd_backup))
    app.add_handler(CommandHandler("backups", cmd_backups))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_no_entendido))

    print("=" * 50)
    print("IronCoach esta EN LINEA")
    print(f"Entrenador: {settings.entrenador_nombre}")
    print(f"Alertas: {settings.hora_alerta}")
    print("Pulsa Ctrl+C para detener")
    print("=" * 50)

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

