from db import conexion


def guardar_foto(
    usuario_id: int,
    tipo: str,
    telegram_file_id: str,
    observaciones: str | None = None,
):
    with conexion() as conn:
        conn.execute(
            """
            INSERT INTO fotos_progreso (
                usuario_id,
                tipo,
                telegram_file_id,
                observaciones
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                usuario_id,
                tipo,
                telegram_file_id,
                observaciones,
            ),
        )

#Obtener Historial de fotos de un usuario
def obtener_fotos_usuario(usuario_id: int):
    with conexion() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM fotos_progreso
            WHERE usuario_id = ?
            ORDER BY fecha DESC
            """,
            (usuario_id,),
        ).fetchall()

    return [dict(r) for r in rows]


#OBTENER FOTO POR ID
def obtener_foto_por_id(
    foto_id: int,
    usuario_id: int,
):
    with conexion() as conn:
        row = conn.execute(
            """
            SELECT
                id,
                usuario_id,
                fecha,
                tipo,
                telegram_file_id,
                observaciones
            FROM fotos_progreso
            WHERE id = ?
              AND usuario_id = ?
            """,
            (
                foto_id,
                usuario_id,
            ),
        ).fetchone()

    return dict(row) if row else None

#OBTENER FOTO ALUMNO 

def obtener_fotos_alumno(
    alumno_id: int,
):
    """Obtiene todas las fotos de un alumno."""

    with conexion() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                usuario_id,
                fecha,
                tipo,
                telegram_file_id,
                observaciones
            FROM fotos_progreso
            WHERE usuario_id = ?
            ORDER BY fecha DESC, id DESC
            """,
            (alumno_id,),
        ).fetchall()

    return [dict(r) for r in rows]


def obtener_foto_alumno(
    alumno_id: int,
    foto_id: int,
):
    """Obtiene una foto específica de un alumno."""

    with conexion() as conn:
        row = conn.execute(
            """
            SELECT
                id,
                usuario_id,
                fecha,
                tipo,
                telegram_file_id,
                observaciones
            FROM fotos_progreso
            WHERE id = ?
              AND usuario_id = ?
            """,
            (
                foto_id,
                alumno_id,
            ),
        ).fetchone()

    return dict(row) if row else None