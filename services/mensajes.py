"""Mensajes motivacionales para las alertas diarias."""

import random


MENSAJES_BASE = [
    "Buenos dias. Hoy es un gran dia para entrenar duro.",
    "Levantate y entrena. Tu yo del futuro te lo agradecera.",
    "Un dia mas, un dia mas cerca de tu mejor version.",
    "No esperes a estar motivado. Entrena y la motivacion llega.",
    "La constancia gana al talento cuando el talento descansa.",
    "Hoy no tienes que ser perfecto, solo tienes que aparecer.",
    "Tu cuerpo puede con todo. Confia en el.",
    "El entrenamiento duro supera al talento natural.",
    "Un纪录 mas cerca. A por el dia de hoy.",
    "Recuerda: lo que no te desafia, no te cambia.",
]


MENSAJES_RUTINA = [
    "Hoy toca darlo todo en el gym. A por ello.",
    "Tu cuerpo descansado rinde mejor. Entrena con cabeza.",
    "Antes del entreno: hidratacion y calentamiento. Vamos.",
]


MENSAJES_FOTO = [
    "No olvides tu foto semanal. Tu progreso merece documentarse.",
    "Una foto vale mas que mil numeros. Subela hoy.",
    "Registro fotografico del dia? Tu progreso te lo agradecera.",
]


MENSAJES_HIDRATACION = [
    "Bebe agua. Tu cuerpo te lo pide.",
    "Hidratacion y sueno: las dos claves olvidadas.",
    "2 litros de agua minimo. Vamos.",
]


def mensaje_aleatorio() -> str:
    """Devuelve un mensaje motivacional aleatorio."""
    return random.choice(MENSAJES_BASE)


def mensaje_con_nombre(nombre: str) -> str:
    """Mensaje personalizado con el nombre del usuario."""
    base = random.choice(MENSAJES_BASE)
    return f"Hola {nombre}. {base}"


def variante_diaria(dia_numero: int) -> str:
    """Segun el dia, devuelve un tipo de mensaje diferente.

    dia_numero: 1-7 (mod 7).
    """
    resto = dia_numero % 7
    if resto in (0, 1):
        return random.choice(MENSAJES_RUTINA)
    elif resto in (2, 3):
        return random.choice(MENSAJES_FOTO)
    elif resto in (4, 5):
        return random.choice(MENSAJES_HIDRATACION)
    else:
        return random.choice(MENSAJES_BASE)
