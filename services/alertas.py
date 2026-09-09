from telegram.ext import Application

from services.auth import obtener_usuario


async def notificar_entrenador(
    app: Application,
    mensaje: str,
):
    """
    Envía una notificación al entrenador principal.
    """

    entrenador = None

    # Buscar entrenador
    from db import conexion

    with conexion() as conn:
        row = conn.execute(
            """
            SELECT telegram_id
            FROM usuarios
            WHERE rol = 'entrenador'
              AND activo = 1
            LIMIT 1
            """
        ).fetchone()

    if not row:
        return

    entrenador = row["telegram_id"]

    if not entrenador:
        return

    try:
        await app.bot.send_message(
            chat_id=entrenador,
            text=mensaje,
        )

    except Exception as e:
        print(
            f"ERROR enviando alerta: {e}"
        )