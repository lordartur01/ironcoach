"""Funciones para gestionar usuarios, alumnos e invitaciones."""

import secrets

from db import conexion
from crypto import hash_pin


def listar_alumnos(solo_activos: bool = True) -> list[dict]:
    """Devuelve todos los alumnos."""
    sql = """
        SELECT id, telegram_id, nombre, edad, fecha_registro, activo
        FROM usuarios
        WHERE rol = 'alumno'
    """

    if solo_activos:
        sql += " AND activo = 1"

    sql += " ORDER BY nombre ASC"

    with conexion() as conn:
        rows = conn.execute(sql).fetchall()

    return [dict(r) for r in rows]


def obtener_alumno_por_id(alumno_id: int) -> dict | None:
    """Devuelve un alumno concreto."""

    with conexion() as conn:
        row = conn.execute(
            """
            SELECT id, telegram_id, nombre, edad, sexo, altura_cm,
                   peso_inicial_kg, grasa_inicial_pct,
                   fecha_registro, activo
            FROM usuarios
            WHERE id = ?
              AND rol = 'alumno'
            """,
            (alumno_id,),
        ).fetchone()

    return dict(row) if row else None


def buscar_alumno_por_nombre(texto: str) -> list[dict]:
    """Busca alumnos por nombre."""

    with conexion() as conn:
        rows = conn.execute(
            """
            SELECT id, telegram_id, nombre, edad, activo
            FROM usuarios
            WHERE rol = 'alumno'
              AND nombre LIKE ?
            ORDER BY nombre
            """,
            (f"%{texto}%",),
        ).fetchall()

    return [dict(r) for r in rows]


def generar_codigo_invitacion() -> str:
    """Genera un código de invitación único."""

    while True:
        codigo = secrets.token_urlsafe(6).upper()

        with conexion() as conn:
            existe = conn.execute(
                """
                SELECT 1
                FROM usuarios
                WHERE codigo_invitacion = ?
                """,
                (codigo,),
            ).fetchone()

        if not existe:
            return codigo


def crear_invitacion(
    nombre: str,
    edad: int | None = None,
    sexo: str | None = None,
    altura_cm: float | None = None,
    peso_inicial_kg: float | None = None,
    grasa_inicial_pct: float | None = None,
) -> str:
    """
    Crea un alumno pendiente de vinculación.

    El alumno todavía no tiene telegram_id.
    """

    codigo = generar_codigo_invitacion()

    with conexion() as conn:
        conn.execute(
            """
            INSERT INTO usuarios (
                telegram_id,
                nombre,
                edad,
                sexo,
                altura_cm,
                peso_inicial_kg,
                grasa_inicial_pct,
                pin_hash,
                codigo_invitacion,
                rol
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'alumno')
            """,
            (
                None,
                nombre,
                edad,
                sexo,
                altura_cm,
                peso_inicial_kg,
                grasa_inicial_pct,
                None,
                codigo,
            ),
        )

    return codigo


def vincular_invitacion(
    codigo: str,
    telegram_id: int,
) -> dict | None:
    """
    Vincula una invitación con el Telegram del alumno.
    """

    codigo = codigo.strip().upper()

    with conexion() as conn:
        alumno = conn.execute(
            """
            SELECT id, nombre, telegram_id
            FROM usuarios
            WHERE codigo_invitacion = ?
              AND rol = 'alumno'
              AND activo = 1
            """,
            (codigo,),
        ).fetchone()

        if not alumno:
            return None

        # Evitar que un Telegram ya registrado
        # sea vinculado accidentalmente.
        existente = conn.execute(
            """
            SELECT id
            FROM usuarios
            WHERE telegram_id = ?
            """,
            (telegram_id,),
        ).fetchone()

        if existente:
            return None

        conn.execute(
            """
            UPDATE usuarios
            SET telegram_id = ?,
                codigo_invitacion = NULL
            WHERE id = ?
            """,
            (telegram_id, alumno["id"]),
        )

        return {
            "id": alumno["id"],
            "nombre": alumno["nombre"],
        }


def reasignar_pin(alumno_id: int, pin_nuevo: str) -> None:
    """Cambia el PIN de un alumno."""

    pin_cifrado = hash_pin(pin_nuevo)

    with conexion() as conn:
        conn.execute(
            """
            UPDATE usuarios
            SET pin_hash = ?
            WHERE id = ?
            """,
            (pin_cifrado, alumno_id),
        )

def desactivar_alumno(alumno_id: int) -> bool:
    """Desactiva un alumno sin borrar su historial."""

    with conexion() as conn:
        cur = conn.execute(
            """
            UPDATE usuarios
            SET activo = 0,
                telegram_id = NULL,
                codigo_invitacion = NULL
            WHERE id = ?
              AND rol = 'alumno'
              AND activo = 1
            """,
            (alumno_id,),
        )

        return cur.rowcount > 0

#===========================================================
# Reactivar alumno
#===========================================================
def reactivar_alumno(alumno_id: int) -> str | None:
    """Reactiva un alumno y genera un nuevo código de invitación."""

    with conexion() as conn:
        alumno = conn.execute(
            """
            SELECT id, nombre
            FROM usuarios
            WHERE id = ?
              AND rol = 'alumno'
              AND activo = 0
            """,
            (alumno_id,),
        ).fetchone()

        if not alumno:
            return None

    codigo = generar_codigo_invitacion()

    with conexion() as conn:
        conn.execute(
            """
            UPDATE usuarios
            SET activo = 1,
                telegram_id = NULL,
                codigo_invitacion = ?
            WHERE id = ?
              AND rol = 'alumno'
              AND activo = 0
            """,
            (codigo, alumno_id),
        )

    return codigo

    # Generar nuevo código de invitación
    codigo = generar_codigo_invitacion()

    with conexion() as conn:
        conn.execute(
            """
            UPDATE usuarios
            SET activo = 1,
                telegram_id = NULL,
                codigo_invitacion = ?
            WHERE id = ?
              AND rol = 'alumno'
              AND activo = 0
            """,
            (codigo, alumno_id),
        )

    return codigo