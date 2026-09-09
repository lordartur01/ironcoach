"""Funciones para generar barras ASCII de progreso."""


def barra_horizontal(valor: float, minimo: float, maximo: float, largo: int = 16) -> str:
    """Dibuja una barra horizontal escalada entre minimo y maximo.

    Ejemplo: valor=72.5, minimo=60, maximo=80 -> ████████████░░░
    """
    if maximo <= minimo:
        return " " * largo
    proporcion = (valor - minimo) / (maximo - minimo)
    proporcion = max(0.0, min(1.0, proporcion))
    lleno = int(round(proporcion * largo))
    vacio = largo - lleno
    return "█" * lleno + "░" * vacio


def formato_diferencia(actual: float, anterior: float, unidad: str = "",
                       invertido: bool = False) -> str:
    """Genera texto con la diferencia entre dos valores.

    invertido=True se usa para medidas donde 'menos es mejor' (grasa, cintura).
    """
    if anterior == 0 or anterior is None or actual is None:
        return ""
    delta = actual - anterior
    if abs(delta) < 0.05:
        return f"  (sin cambio)"
    flecha = "↑" if delta > 0 else "↓"
    if invertido:
        flecha = "↓" if delta > 0 else "↑"
    return f"  {flecha} {abs(delta):.1f}{unidad}"


def linea_barra(etiqueta: str, actual: float, anterior: float | None,
                minimo: float, maximo: float, unidad: str = "",
                invertido: bool = False, record: bool = False) -> str:
    """Compone una linea completa: etiqueta + barra + valor + diferencia."""
    barra = barra_horizontal(actual, minimo, maximo)
    record_txt = "  RECORD" if record else ""
    diff_txt = formato_diferencia(actual, anterior, unidad, invertido) if anterior else ""
    return f"{etiqueta:<14} {barra}  {actual:>6.1f}{unidad}{diff_txt}{record_txt}"
