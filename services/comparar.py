"""Logica de comparacion de fotos antes/despues."""

TIPOS_VALIDOS = [
    "frente",
    "espalda",
    "perfil_izquierdo",
    "perfil_derecho",
    "libre",
]


def obtener_extremas_por_tipo(usuario_id: int, tipo: str) -> tuple[dict | None, dict | None]:
    """Devuelve (mas_antigua, mas_reciente) de un tipo para un usuario.

    Si solo hay una foto, devuelve (None, foto_unica).
    Si no hay fotos, devuelve (None, None).
    """
    from db import conexion

    with conexion() as conn:
        rows = conn.execute(
            """
            SELECT id, usuario_id, fecha, tipo, telegram_file_id, observaciones
            FROM fotos_progreso
            WHERE usuario_id = ? AND tipo = ?
            ORDER BY fecha ASC, id ASC
            """,
            (usuario_id, tipo),
        ).fetchall()

    if not rows:
        return None, None

    if len(rows) == 1:
        return None, dict(rows[0])

    return dict(rows[0]), dict(rows[-1])


def listar_tipos_disponibles(usuario_id: int) -> list[str]:
    """Devuelve la lista de tipos de foto que tiene el usuario."""
    from db import conexion

    with conexion() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT tipo
            FROM fotos_progreso
            WHERE usuario_id = ?
            ORDER BY tipo
            """,
            (usuario_id,),
        ).fetchall()

    return [r["tipo"] for r in rows]


def dias_entre(fecha_a: str, fecha_b: str) -> int:
    """Calcula dias entre dos fechas en formato SQLite."""
    from datetime import datetime

    fmt = "%Y-%m-%d %H:%M:%S"
    try:
        a = datetime.strptime(fecha_a[:19], fmt)
        b = datetime.strptime(fecha_b[:19], fmt)
        return abs((b - a).days)
    except Exception:
        return 0