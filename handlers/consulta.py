"""Handler para consulta de progreso y registros."""

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from db import conexion
from services.auth import obtener_usuario
from services.graficas import linea_barra


# ============================================================
# COMO VOY
# ============================================================

async def cmd_como_voy(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    from services.seguridad import exigir_usuario

    if not await exigir_usuario(update, context):
        return

    """Muestra el progreso del usuario con barras ASCII."""

    telegram_id = update.effective_user.id
    usuario = obtener_usuario(telegram_id)

    if not usuario:
        await update.message.reply_text(
            "Necesitas iniciar sesion. /start"
        )
        return

    uid = usuario["id"]

    lineas = [
        f"PROGRESO DE {usuario['nombre'].upper()}",
        "",
    ]

    with conexion() as conn:

        # ====================================================
        # MEDIDAS CORPORALES
        # ====================================================

        medidas = conn.execute(
            """
            SELECT
                fecha,
                peso_kg,
                grasa_pct,
                cintura
            FROM medidas_corporales
            WHERE usuario_id = ?
            ORDER BY fecha ASC
            """,
            (uid,),
        ).fetchall()

        if len(medidas) >= 2:

            primera = medidas[0]
            ultima = medidas[-1]

            lineas.append("PESO")

            if primera["peso_kg"] and ultima["peso_kg"]:

                lineas.append(
                    linea_barra(
                        "  Antes:",
                        primera["peso_kg"],
                        None,
                        50,
                        100,
                        "kg",
                    )
                )

                lineas.append(
                    linea_barra(
                        "  Ahora:",
                        ultima["peso_kg"],
                        primera["peso_kg"],
                        50,
                        100,
                        "kg",
                        invertido=True,
                    )
                )

            lineas.append("")

            if primera["grasa_pct"] and ultima["grasa_pct"]:

                lineas.append("GRASA CORPORAL")

                lineas.append(
                    linea_barra(
                        "  Antes:",
                        primera["grasa_pct"],
                        None,
                        5,
                        30,
                        "%",
                    )
                )

                lineas.append(
                    linea_barra(
                        "  Ahora:",
                        ultima["grasa_pct"],
                        primera["grasa_pct"],
                        5,
                        30,
                        "%",
                        invertido=True,
                    )
                )

            lineas.append("")

            if primera["cintura"] and ultima["cintura"]:

                lineas.append("CINTURA")

                lineas.append(
                    linea_barra(
                        "  Antes:",
                        primera["cintura"],
                        None,
                        60,
                        110,
                        " cm",
                    )
                )

                lineas.append(
                    linea_barra(
                        "  Ahora:",
                        ultima["cintura"],
                        primera["cintura"],
                        60,
                        110,
                        " cm",
                        invertido=True,
                    )
                )

            lineas.append("")

        elif len(medidas) == 1:

            m = medidas[0]

            lineas.append(
                "Solo tienes un registro de medidas."
            )

            lineas.append(
                f"  Peso: {m['peso_kg']} kg"
            )

            lineas.append(
                f"  Grasa: {m['grasa_pct']} %"
            )

            lineas.append(
                f"  Cintura: {m['cintura']} cm"
            )

            lineas.append(
                "Registra otra para ver progreso."
            )

            lineas.append("")

        # ====================================================
        # FUERZA
        # ====================================================

        fuerza = conn.execute(
            """
            SELECT
                e.nombre,
                MAX(s.peso_kg) AS max_peso
            FROM sesion_series s
            JOIN ejercicios e
                ON e.id = s.ejercicio_id
            JOIN sesiones ses
                ON ses.id = s.sesion_id
            WHERE
                ses.usuario_id = ?
                AND s.peso_kg IS NOT NULL
            GROUP BY e.nombre
            ORDER BY max_peso DESC
            LIMIT 5
            """,
            (uid,),
        ).fetchall()

        if fuerza:

            lineas.append(
                "FUERZA (mejor marca por ejercicio)"
            )

            for row in fuerza:

                lineas.append(
                    f"  {row['nombre']:<18} "
                    f"{row['max_peso']:>6.1f} kg"
                )

            lineas.append("")

        # ====================================================
        # CARDIO
        # ====================================================

        cardio = conn.execute(
            """
            SELECT
                fecha,
                distancia_km,
                tiempo_min,
                ritmo_promedio,
                vo2_estimado
            FROM registros_cardio
            WHERE usuario_id = ?
            ORDER BY fecha ASC
            """,
            (uid,),
        ).fetchall()

        if len(cardio) >= 1:

            lineas.append("CARDIO / RUNNING")

            for c in cardio[-5:]:

                fecha = (
                    c["fecha"][:10]
                    if c["fecha"]
                    else "?"
                )

                ritmo = (
                    c["ritmo_promedio"]
                    or "-"
                )

                vo2 = (
                    c["vo2_estimado"]
                    or "-"
                )

                lineas.append(
                    f"  {fecha}  "
                    f"{c['distancia_km']}km en "
                    f"{c['tiempo_min']}min  "
                    f"ritmo {ritmo}/km  "
                    f"VO2 {vo2}"
                )

            lineas.append("")

        if len(lineas) == 2:

            lineas.append(
                "Aun no tienes registros."
            )

            lineas.append(
                "Empieza con /medidas, "
                "/entrenamiento o /cardio."
            )

    await update.message.reply_text(
        "\n".join(lineas)
    )


# ============================================================
# MIS MEDIDAS
# ============================================================

async def cmd_mis_medidas(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    from services.seguridad import exigir_usuario

    if not await exigir_usuario(update, context):
        return

    usuario = obtener_usuario(
        update.effective_user.id
    )

    if not usuario:

        await update.message.reply_text(
            "Necesitas iniciar sesion. /start"
        )

        return

    with conexion() as conn:

        medidas = conn.execute(
            """
            SELECT
                fecha,
                peso_kg,
                grasa_pct,
                cintura
            FROM medidas_corporales
            WHERE usuario_id = ?
            ORDER BY fecha DESC
            LIMIT 10
            """,
            (usuario["id"],),
        ).fetchall()

    if not medidas:

        await update.message.reply_text(
            "Todavia no tienes medidas registradas.\n\n"
            "Usa /medidas para registrar la primera."
        )

        return

    lineas = [
        "📏 HISTORIAL DE MEDIDAS",
        "",
    ]

    for m in medidas:

        fecha = (
            m["fecha"][:10]
            if m["fecha"]
            else "?"
        )

        lineas.append(
            f"{fecha}\n"
            f"Peso: {m['peso_kg']} kg\n"
            f"Grasa: {m['grasa_pct']} %\n"
            f"Cintura: {m['cintura']} cm"
        )

    await update.message.reply_text(
        "\n\n".join(lineas)
    )


# ============================================================
# MIS ENTRENAMIENTOS
# ============================================================

async def cmd_mis_entrenamientos(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    from services.seguridad import exigir_usuario

    if not await exigir_usuario(update, context):
        return

    usuario = obtener_usuario(
        update.effective_user.id
    )

    if not usuario:

        await update.message.reply_text(
            "Necesitas iniciar sesion. /start"
        )

        return

    with conexion() as conn:

        sesiones = conn.execute(
            """
            SELECT
                s.id,
                s.fecha,
                r.nombre AS rutina
            FROM sesiones s
            LEFT JOIN rutinas r
                ON r.id = s.rutina_id
            WHERE s.usuario_id = ?
            ORDER BY s.fecha DESC
            LIMIT 20
            """,
            (usuario["id"],),
        ).fetchall()

    if not sesiones:

        await update.message.reply_text(
            "No tienes entrenamientos registrados."
        )

        return

    lineas = [
        "🏋️ HISTORIAL DE ENTRENAMIENTOS",
        "",
    ]

    for s in sesiones:

        fecha = (
            s["fecha"][:10]
            if s["fecha"]
            else "?"
        )

        rutina = s["rutina"] or "Libre"

        lineas.append(
            f"ID: {s['id']} | {fecha}\n"
            f"Rutina: {rutina}"
        )

    await update.message.reply_text(
        "\n\n".join(lineas)
    )


# ============================================================
# VER ENTRENAMIENTO
# ============================================================

async def cmd_ver_entrenamiento(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    from services.seguridad import exigir_usuario

    if not await exigir_usuario(update, context):
        return

    usuario = obtener_usuario(
        update.effective_user.id
    )

    if not usuario:
        return

    if not context.args:

        await update.message.reply_text(
            "Uso:\n"
            "/ver_entrenamiento ID\n\n"
            "Ejemplo:\n"
            "/ver_entrenamiento 15"
        )

        return

    try:

        sesion_id = int(
            context.args[0]
        )

    except ValueError:

        await update.message.reply_text(
            "ID no valido."
        )

        return

    with conexion() as conn:

        sesion = conn.execute(
            """
            SELECT
                s.id,
                s.fecha,
                r.nombre AS rutina
            FROM sesiones s
            LEFT JOIN rutinas r
                ON r.id = s.rutina_id
            WHERE
                s.id = ?
                AND s.usuario_id = ?
            """,
            (
                sesion_id,
                usuario["id"],
            ),
        ).fetchone()

        if not sesion:

            await update.message.reply_text(
                "No existe ese entrenamiento."
            )

            return

        ejercicios = conn.execute(
            """
            SELECT
                e.nombre,
                ss.series,
                ss.repeticiones,
                ss.peso_kg
            FROM sesion_series ss
            JOIN ejercicios e
                ON e.id = ss.ejercicio_id
            WHERE ss.sesion_id = ?
            ORDER BY ss.id
            """,
            (sesion_id,),
        ).fetchall()

    lineas = [
        f"🏋️ ENTRENAMIENTO #{sesion['id']}",
        "",
        f"Fecha: {sesion['fecha'][:10]}",
        f"Rutina: {sesion['rutina'] or 'Libre'}",
        "",
    ]

    if not ejercicios:

        lineas.append(
            "No hay ejercicios registrados."
        )

    else:

        for e in ejercicios:

            peso = e["peso_kg"] or 0

            lineas.append(
                f"{e['nombre']}\n"
                f"{e['series']}x"
                f"{e['repeticiones']} "
                f"@ {peso} kg"
            )

    await update.message.reply_text(
        "\n".join(lineas)
    )


# ============================================================
# MIS CARDIOS
# ============================================================

async def cmd_mis_cardios(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    from services.seguridad import exigir_usuario

    if not await exigir_usuario(update, context):
        return

    usuario = obtener_usuario(
        update.effective_user.id
    )

    if not usuario:
        return

    with conexion() as conn:

        cardios = conn.execute(
            """
            SELECT
                id,
                fecha,
                distancia_km,
                tiempo_min,
                ritmo_promedio,
                vo2_estimado
            FROM registros_cardio
            WHERE usuario_id = ?
            ORDER BY fecha DESC
            LIMIT 20
            """,
            (usuario["id"],),
        ).fetchall()

    if not cardios:

        await update.message.reply_text(
            "No tienes sesiones de cardio registradas."
        )

        return

    lineas = [
        "🏃 HISTORIAL DE CARDIO",
        "",
    ]

    for c in cardios:

        fecha = (
            c["fecha"][:10]
            if c["fecha"]
            else "?"
        )

        lineas.append(
            f"#{c['id']} - {fecha}\n"
            f"{c['distancia_km']} km | "
            f"{c['tiempo_min']} min\n"
            f"Ritmo: {c['ritmo_promedio']}\n"
            f"VO2: {c['vo2_estimado']}"
        )

    await update.message.reply_text(
        "\n\n".join(lineas)
    )


# ============================================================
# VER CARDIO
# ============================================================

async def cmd_ver_cardio(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    from services.seguridad import exigir_usuario

    if not await exigir_usuario(update, context):
        return

    usuario = obtener_usuario(
        update.effective_user.id
    )

    if not usuario:
        return

    if not context.args:

        await update.message.reply_text(
            "Uso:\n"
            "/ver_cardio ID\n\n"
            "Ejemplo:\n"
            "/ver_cardio 8"
        )

        return

    try:

        cardio_id = int(
            context.args[0]
        )

    except ValueError:

        await update.message.reply_text(
            "ID no valido."
        )

        return

    with conexion() as conn:

        cardio = conn.execute(
            """
            SELECT
                id,
                fecha,
                distancia_km,
                tiempo_min,
                ritmo_promedio,
                vo2_estimado
            FROM registros_cardio
            WHERE
                id = ?
                AND usuario_id = ?
            """,
            (
                cardio_id,
                usuario["id"],
            ),
        ).fetchone()

    if not cardio:

        await update.message.reply_text(
            "No existe ese registro de cardio."
        )

        return

    fecha = (
        cardio["fecha"][:10]
        if cardio["fecha"]
        else "?"
    )

    distancia = (
        cardio["distancia_km"]
        if cardio["distancia_km"] is not None
        else "No registrada"
    )

    tiempo = (
        cardio["tiempo_min"]
        if cardio["tiempo_min"] is not None
        else "No registrado"
    )

    ritmo = (
        cardio["ritmo_promedio"]
        if cardio["ritmo_promedio"]
        else "No calculado"
    )

    vo2 = (
        cardio["vo2_estimado"]
        if cardio["vo2_estimado"]
        else "No calculado"
    )

    lineas = [
        f"🏃 CARDIO #{cardio['id']}",
        "",
        f"📅 Fecha: {fecha}",
        f"📏 Distancia: {distancia} km",
        f"⏱️ Tiempo: {tiempo} min",
        f"⚡ Ritmo: {ritmo} min/km",
        f"❤️ VO2 estimado: {vo2}",
    ]

    await update.message.reply_text(
        "\n".join(lineas)
    )


# ============================================================
# RECORDS
# ============================================================

async def cmd_records(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    from services.seguridad import exigir_usuario

    if not await exigir_usuario(update, context):
        return

    usuario = obtener_usuario(
        update.effective_user.id
    )

    if not usuario:
        return

    with conexion() as conn:

        records = conn.execute(
            """
            SELECT
                e.nombre,
                MAX(ss.peso_kg) AS record_peso
            FROM sesion_series ss
            JOIN ejercicios e
                ON e.id = ss.ejercicio_id
            JOIN sesiones s
                ON s.id = ss.sesion_id
            WHERE
                s.usuario_id = ?
                AND ss.peso_kg IS NOT NULL
            GROUP BY e.nombre
            ORDER BY record_peso DESC
            """,
            (usuario["id"],),
        ).fetchall()

    if not records:

        await update.message.reply_text(
            "Todavia no tienes ejercicios registrados."
        )

        return

    lineas = [
        "🏆 RECORDS PERSONALES",
        "",
    ]

    for r in records:

        lineas.append(
            f"{r['nombre']:<20} "
            f"{r['record_peso']:>6.1f} kg"
        )

    lineas.append("")

    lineas.append(
        f"Total ejercicios con record: "
        f"{len(records)}"
    )

    await update.message.reply_text(
        "\n".join(lineas)
    )


# ============================================================
# ESTADISTICAS
# ============================================================

async def cmd_estadisticas(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    from services.seguridad import exigir_usuario

    if not await exigir_usuario(update, context):
        return

    usuario = obtener_usuario(
        update.effective_user.id
    )

    if not usuario:
        return

    uid = usuario["id"]

    with conexion() as conn:

        total_entrenamientos = conn.execute(
            """
            SELECT COUNT(*)
            FROM sesiones
            WHERE usuario_id = ?
            """,
            (uid,),
        ).fetchone()[0]

        total_cardios = conn.execute(
            """
            SELECT COUNT(*)
            FROM registros_cardio
            WHERE usuario_id = ?
            """,
            (uid,),
        ).fetchone()[0]

        total_medidas = conn.execute(
            """
            SELECT COUNT(*)
            FROM medidas_corporales
            WHERE usuario_id = ?
            """,
            (uid,),
        ).fetchone()[0]

        medidas = conn.execute(
            """
            SELECT
                peso_kg,
                grasa_pct
            FROM medidas_corporales
            WHERE usuario_id = ?
            ORDER BY fecha ASC
            """,
            (uid,),
        ).fetchall()

        km_totales = conn.execute(
            """
            SELECT SUM(distancia_km)
            FROM registros_cardio
            WHERE usuario_id = ?
            """,
            (uid,),
        ).fetchone()[0]

        mejor_vo2 = conn.execute(
            """
            SELECT MAX(vo2_estimado)
            FROM registros_cardio
            WHERE usuario_id = ?
            """,
            (uid,),
        ).fetchone()[0]

        ejercicios = conn.execute(
            """
            SELECT COUNT(DISTINCT ejercicio_id)
            FROM sesion_series ss
            JOIN sesiones s
                ON s.id = ss.sesion_id
            WHERE s.usuario_id = ?
            """,
            (uid,),
        ).fetchone()[0]

    lineas = [
        "📊 ESTADÍSTICAS GENERALES",
        "",
        f"🏋️ Entrenamientos: "
        f"{total_entrenamientos}",
        f"🏃 Cardios: "
        f"{total_cardios}",
        f"📏 Registros de medidas: "
        f"{total_medidas}",
        "",
    ]

    if len(medidas) >= 1:

        peso_inicial = medidas[0]["peso_kg"]
        peso_actual = medidas[-1]["peso_kg"]

        grasa_inicial = medidas[0]["grasa_pct"]
        grasa_actual = medidas[-1]["grasa_pct"]

        if peso_inicial and peso_actual:

            diferencia_peso = (
                peso_actual - peso_inicial
            )

            lineas.extend([
                f"⚖️ Peso inicial: "
                f"{peso_inicial} kg",

                f"⚖️ Peso actual: "
                f"{peso_actual} kg",

                f"📉 Cambio: "
                f"{diferencia_peso:+.1f} kg",

                "",
            ])

        if grasa_inicial and grasa_actual:

            diferencia_grasa = (
                grasa_actual - grasa_inicial
            )

            lineas.extend([
                f"🔥 Grasa inicial: "
                f"{grasa_inicial} %",

                f"🔥 Grasa actual: "
                f"{grasa_actual} %",

                f"📉 Cambio: "
                f"{diferencia_grasa:+.1f} %",

                "",
            ])

    lineas.extend([
        f"🏃 Kilómetros acumulados: "
        f"{round(km_totales or 0, 1)} km",

        f"❤️ Mejor VO2: "
        f"{round(mejor_vo2 or 0, 1)}",

        f"🏆 Ejercicios distintos: "
        f"{ejercicios or 0}",
    ])

    await update.message.reply_text(
        "\n".join(lineas)
    )


# ============================================================
# RANKING DE ALUMNOS
# ============================================================

async def cmd_ranking_alumnos(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    usuario = obtener_usuario(
        update.effective_user.id
    )

    if not usuario or usuario["rol"] != "entrenador":

        await update.message.reply_text(
            "Comando exclusivo para entrenador."
        )

        return

    with conexion() as conn:

        ranking = conn.execute(
            """
            SELECT
                u.nombre,
                COUNT(s.id) AS entrenamientos
            FROM usuarios u
            LEFT JOIN sesiones s
                ON s.usuario_id = u.id
            WHERE
                u.rol = 'alumno'
                AND u.activo = 1
            GROUP BY u.id
            ORDER BY entrenamientos DESC
            LIMIT 10
            """
        ).fetchall()

    if not ranking:

        await update.message.reply_text(
            "No hay alumnos registrados."
        )

        return

    medallas = [
        "🥇",
        "🥈",
        "🥉",
    ]

    lineas = [
        "🏆 RANKING DE ALUMNOS",
        "",
    ]

    for i, alumno in enumerate(ranking):

        icono = (
            medallas[i]
            if i < 3
            else "🏅"
        )

        lineas.append(
            f"{icono} {alumno['nombre']}\n"
            f"   {alumno['entrenamientos']} "
            f"entrenamientos"
        )

    lineas.append("")

    lineas.append(
        f"Total alumnos: {len(ranking)}"
    )

    await update.message.reply_text(
        "\n".join(lineas)
    )

#============================================================
#MIS RECORDS
#===========================================================

async def cmd_mis_records(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    from services.seguridad import exigir_usuario

    if not await exigir_usuario(update, context):
        return

    usuario = obtener_usuario(
        update.effective_user.id
    )

    if not usuario:
        return

    with conexion() as conn:

        fuerza = conn.execute(
            """
            SELECT
                e.nombre,
                MAX(ss.peso_kg) AS record_peso
            FROM sesion_series ss
            JOIN ejercicios e
                ON e.id = ss.ejercicio_id
            JOIN sesiones s
                ON s.id = ss.sesion_id
            WHERE s.usuario_id = ?
            GROUP BY e.nombre
            ORDER BY record_peso DESC
            LIMIT 1
            """,
            (usuario["id"],),
        ).fetchone()

        distancia = conn.execute(
            """
            SELECT *
            FROM registros_cardio
            WHERE usuario_id = ?
            ORDER BY distancia_km DESC
            LIMIT 1
            """,
            (usuario["id"],),
        ).fetchone()

        vo2 = conn.execute(
            """
            SELECT *
            FROM registros_cardio
            WHERE usuario_id = ?
            ORDER BY vo2_estimado DESC
            LIMIT 1
            """,
            (usuario["id"],),
        ).fetchone()

    lineas = [
        "🏆 MIS RECORDS",
        "",
    ]

    if fuerza:

        lineas.append(
            f"💪 Fuerza máxima\n"
            f"{fuerza['nombre']} - "
            f"{fuerza['record_peso']} kg"
        )
        lineas.append("")

    if distancia:

        lineas.append(
            f"🏃 Mayor distancia\n"
            f"{distancia['distancia_km']} km "
            f"({distancia['fecha'][:10]})"
        )
        lineas.append("")

    if vo2:

        lineas.append(
            f"🔥 Mejor VO2\n"
            f"{vo2['vo2_estimado']}"
        )

    await update.message.reply_text(
        "\n".join(lineas)
    )


#============================================================
#DASHBOARD
#===========================================================

async def cmd_dashboard(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    from services.seguridad import exigir_usuario

    if not await exigir_usuario(update, context):
        return

    usuario = obtener_usuario(
        update.effective_user.id
    )

    if not usuario:
        return

    with conexion() as conn:

        medida_actual = conn.execute(
            """
            SELECT *
            FROM medidas_corporales
            WHERE usuario_id = ?
            ORDER BY fecha DESC
            LIMIT 1
            """,
            (usuario["id"],),
        ).fetchone()

        medida_inicial = conn.execute(
            """
            SELECT *
            FROM medidas_corporales
            WHERE usuario_id = ?
            ORDER BY fecha ASC
            LIMIT 1
            """,
            (usuario["id"],),
        ).fetchone()

        total_entrenos = conn.execute(
            """
            SELECT COUNT(*)
            FROM sesiones
            WHERE usuario_id = ?
            """,
            (usuario["id"],),
        ).fetchone()[0]

        ultimo_entreno = conn.execute(
            """
            SELECT fecha
            FROM sesiones
            WHERE usuario_id = ?
            ORDER BY fecha DESC
            LIMIT 1
            """,
            (usuario["id"],),
        ).fetchone()

        ultimo_cardio = conn.execute(
            """
            SELECT *
            FROM registros_cardio
            WHERE usuario_id = ?
            ORDER BY fecha DESC
            LIMIT 1
            """,
            (usuario["id"],),
        ).fetchone()

        record = conn.execute(
            """
            SELECT
                e.nombre,
                MAX(ss.peso_kg) AS max_peso
            FROM sesion_series ss
            JOIN ejercicios e
                ON e.id = ss.ejercicio_id
            JOIN sesiones s
                ON s.id = ss.sesion_id
            WHERE s.usuario_id = ?
            GROUP BY e.nombre
            ORDER BY max_peso DESC
            LIMIT 1
            """,
            (usuario["id"],),
        ).fetchone()

    lineas = [
        f"📊 DASHBOARD DE {usuario['nombre'].upper()}",
        "",
    ]

    if medida_actual:

        lineas.extend([
            "👤 DATOS ACTUALES",
            f"Peso: {medida_actual['peso_kg']} kg",
            f"Grasa: {medida_actual['grasa_pct']} %",
            f"Cintura: {medida_actual['cintura']} cm",
            "",
        ])

    lineas.extend([
        "🏋️ FUERZA",
        f"Entrenamientos: {total_entrenos}",
    ])

    if ultimo_entreno:
        lineas.append(
            f"Último: {ultimo_entreno['fecha'][:10]}"
        )

    if record:
        lineas.extend([
            "",
            "🥇 MEJOR RECORD",
            f"{record['nombre']} -> {record['max_peso']} kg",
        ])

    if ultimo_cardio:

        lineas.extend([
            "",
            "🏃 CARDIO",
            f"VO2: {ultimo_cardio['vo2_estimado']}",
            f"Ritmo: {ultimo_cardio['ritmo_promedio']}",
        ])

    if medida_actual and medida_inicial:

        peso_delta = (
            medida_actual["peso_kg"]
            - medida_inicial["peso_kg"]
        )

        grasa_delta = (
            medida_actual["grasa_pct"]
            - medida_inicial["grasa_pct"]
        )

        lineas.extend([
            "",
            "📈 PROGRESO",
            f"Peso: {peso_delta:+.1f} kg",
            f"Grasa: {grasa_delta:+.1f} %",
        ])

    lineas.extend([
        "",
        "🎯 ACCESOS RAPIDOS",
        "/mis_medidas",
        "/mis_entrenamientos",
        "/mis_cardios",
        "/mis_records",
        "/como_voy",
    ])

    await update.message.reply_text(
        "\n".join(lineas)
    )


# ============================================================
# REGISTRAR COMANDOS
# ============================================================

def registrar(app):

    app.add_handler(
        CommandHandler(
            "como_voy",
            cmd_como_voy,
        )
    )

    app.add_handler(
        CommandHandler(
            "mis_medidas",
            cmd_mis_medidas,
        )
    )

    app.add_handler(
        CommandHandler(
            "mis_entrenamientos",
            cmd_mis_entrenamientos,
        )
    )

    app.add_handler(
        CommandHandler(
            "ver_entrenamiento",
            cmd_ver_entrenamiento,
        )
    )

    app.add_handler(
        CommandHandler(
            "mis_cardios",
            cmd_mis_cardios,
        )
    )

    app.add_handler(
        CommandHandler(
            "ver_cardio",
            cmd_ver_cardio,
        )
    )

    app.add_handler(
        CommandHandler(
            "records",
            cmd_records,
        )
    )

    app.add_handler(
        CommandHandler(
            "estadisticas",
            cmd_estadisticas,
        )
    )

    app.add_handler(
        CommandHandler(
            "ranking_alumnos",
            cmd_ranking_alumnos,
        )
    )

    app.add_handler(
    CommandHandler(
        "ver_cardio",
        cmd_ver_cardio,
    )
)

    app.add_handler(
    CommandHandler(
        "mis_records",
        cmd_mis_records,
    )
)

    app.add_handler(
    CommandHandler(
        "dashboard",
        cmd_dashboard,
    )
)