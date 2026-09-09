"""Funciones de seguridad para IronCoach."""

from cryptography.fernet import Fernet
from werkzeug.security import generate_password_hash, check_password_hash

from config import settings


def _fernet() -> Fernet:
    """Devuelve una instancia de Fernet usando la clave del .env."""
    return Fernet(settings.fernet_key.encode())


def encrypt(texto_plano: str) -> str | None:
    """Cifra un texto usando Fernet."""
    if texto_plano is None:
        return None

    return _fernet().encrypt(
        texto_plano.encode()
    ).decode()


def decrypt(texto_cifrado: str) -> str | None:
    """Descifra un texto previamente cifrado con Fernet."""
    if not texto_cifrado:
        return None

    try:
        return _fernet().decrypt(
            texto_cifrado.encode()
        ).decode()
    except Exception:
        return None


def hash_pin(pin: str) -> str:
    """Genera un hash seguro para un PIN."""
    if not pin:
        raise ValueError("El PIN no puede estar vacío.")

    return generate_password_hash(pin)


def verify_pin(pin: str, hash_guardado: str) -> bool:
    """Comprueba un PIN contra su hash."""
    if not pin or not hash_guardado:
        return False

    try:
        return check_password_hash(hash_guardado, pin)
    except Exception:
        return False