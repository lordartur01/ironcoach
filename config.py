"""Configuracion central del bot (lee .env)."""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

import os as _os
from pathlib import Path as _Path
_env_path = _Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_env_path, encoding="utf-8-sig")


@dataclass(frozen=True)
class Settings:
    telegram_token: str
    fernet_key: str
    entrenador_nombre: str
    hora_alerta: str
    db_path: str


def _get(name: str, default: str = "") -> str:
    val = os.getenv(name)
    return val if val is not None and val != "" else default


settings = Settings(
    telegram_token=_get("TELEGRAM_TOKEN", ""),
    fernet_key=_get("FERNET_KEY", ""),
    entrenador_nombre=_get("ENTRENADOR_NOMBRE", "Entrenador"),
    hora_alerta=_get("HORA_ALERTA", "06:00"),
    db_path=_get("DB_PATH", "data\\ironcoach.db"),
)
