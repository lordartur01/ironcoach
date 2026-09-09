"""Logica de autenticacion de IronCoach."""

import os

from db import conexion
from crypto import hash_pin


PIN_MAESTRO = os.getenv("ENTRENADOR_PIN")

if not PIN_MAESTRO:
    raise RuntimeError(
        "ERROR: ENTRENADOR_PIN no está configurado en el archivo .env"
    )


def es_pin_maestro(pin_texto: str) -> bool:
    """Comprueba el PIN maestro del entrenador."""
    return bool(pin_texto) and pin_texto == PIN_MAESTRO


def registrar_entrenador(
    telegram_id: int,
    nombre: str,
    pin_texto: str,
) -> int:
    """Registra al entrenador principal."""

    pin_hash = hash_pin(pin_texto)

    with conexion() as conn:
        cur = conn.execute(
            """
            INSERT INTO usuarios (
                telegram_id,
                nombre,
                pin_hash,
                rol
            )
            VALUES (?, ?, ?, 'entrenador')
            """,
            (
                telegram_id,
                nombre,
                pin_hash,
            ),
        )

        return cur.lastrowid


def usuario_existe(telegram_id: int) -> bool:
    """Comprueba si un Telegram ya está vinculado a un usuario activo."""

    with conexion() as conn:
        row = conn.execute(
            """
            SELECT 1
            FROM usuarios
            WHERE telegram_id = ?
              AND activo = 1
            """,
            (telegram_id,),
        ).fetchone()

    return row is not None


def obtener_usuario(telegram_id: int) -> dict | None:
    """Devuelve los datos básicos del usuario."""

    with conexion() as conn:
        row = conn.execute(
            """
            SELECT
                id,
                telegram_id,
                nombre,
                rol,
                activo
            FROM usuarios
            WHERE telegram_id = ?
            """,
            (telegram_id,),
        ).fetchone()

    if not row:
        return None

    return dict(row)

def usuario_activo(telegram_id: int) -> dict | None:
    """
    Devuelve el usuario si existe y está activo.

    Si no existe o está inactivo, devuelve None.
    """

    with conexion() as conn:
        row = conn.execute(
            """
            SELECT
                id,
                telegram_id,
                nombre,
                rol,
                activo
            FROM usuarios
            WHERE telegram_id = ?
              AND activo = 1
            """,
            (telegram_id,),
        ).fetchone()

    return dict(row) if row else None


def alumno_activo(telegram_id: int) -> dict | None:
    """
    Devuelve el alumno activo y vinculado.

    No permite entrenadores.
    """

    usuario = usuario_activo(telegram_id)

    if not usuario:
        return None

    if usuario["rol"] != "alumno":
        return None

    return usuario


def entrenador_activo(telegram_id: int) -> dict | None:
    """
    Devuelve el entrenador activo.
    """

    usuario = usuario_activo(telegram_id)

    if not usuario:
        return None

    if usuario["rol"] != "entrenador":
        return None

    return usuario