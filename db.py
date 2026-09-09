"""Conexion y ciclo de vida de la base de datos SQLite."""
import os
import sqlite3
from contextlib import contextmanager

from config import settings


def _ruta_absoluta() -> str:
    """Construye la ruta absoluta de la BD a partir de la config."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, settings.db_path)


@contextmanager
def conexion():
    """Context manager que abre y cierra la conexion."""
    conn = sqlite3.connect(_ruta_absoluta())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Crea las tablas si no existen."""
    from models import SCRIPT_SQL
    with conexion() as conn:
        conn.executescript(SCRIPT_SQL)
    print(f"OK Base de datos lista en {_ruta_absoluta()}")
