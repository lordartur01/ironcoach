"""Comandos exclusivos del entrenador."""

from telegram import Update
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from db import conexion

from services.auth import obtener_usuario

from services.usuarios import (
    listar_alumnos,
    obtener_alumno_por_id,
    buscar_alumno_por_nombre,
    crear_invitacion,
    desactivar_alumno,
    reactivar_alumno,
)

from services.fotos import (
    obtener_fotos_alumno,
    obtener_foto_alumno,
)


# Estado de conversación para crear invitaciones
ESPERANDO_NOMBRE_INVITACION = 10


from services.auth import entrenador_activo


def _es_entrenador(telegram_id: int) -> bool:
    """Comprueba que sea el entrenador activo."""

    return entrenador_activo(telegram_id) is not None


# ============================================================
# REGISTRAR ALUMNO
# ============================================================

async def cmd_registrar_alumno(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Inicia la creación de una invitación."""

    if not _es_entrenador(update.effective_user.id):
        await update.message.reply_text(
            "Solo el entrenador puede usar este comando."
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "REGISTRO DE ALUMNO\n\n"
        "Escribe el nombre completo del alumno.\n\n"
        "Ejemplo:\n"
        "Juan Perez\n\n"
        "Escribe CANCELAR para cancelar."
    )

    return ESPERANDO_NOMBRE_INVITACION


async def recibir_nombre_invitacion(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Recibe el nombre y genera la invitación."""

    nombre = update.message.text.strip()

    if nombre.upper() == "CANCELAR":
        await update.message.reply_text(
            "Registro cancelado."
        )
        return ConversationHandler.END

    if len(nombre) < 2:
        await update.message.reply_text(
            "El nombre es demasiado corto.\n"
            "Escribe el nombre completo."
        )
        return ESPERANDO_NOMBRE_INVITACION

    try:
        codigo = crear_invitacion(nombre)

    except Exception as e:
        await update.message.reply_text(
            "No pude crear la invitación.\n\n"
            f"Error: {e}"
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "INVITACIÓN CREADA\n\n"
        f"Alumno: {nombre}\n"
        f"Código: {codigo}\n\n"
        "Envíale este código al alumno.\n\n"
        "El alumno debe:\n"
        "1. Abrir IronCoach\n"
        "2. Escribir /start\n"
        "3. Introducir este código\n\n"
        "Cuando lo haga, su cuenta quedará vinculada."
    )

    return ConversationHandler.END


# ============================================================
# LISTAR ALUMNOS
# ============================================================

async def cmd_alumnos(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Lista todos los alumnos."""

    if not _es_entrenador(update.effective_user.id):
        await update.message.reply_text(
            "Solo el entrenador puede usar este comando."
        )
        return

    alumnos = listar_alumnos()

    if not alumnos:
        await update.message.reply_text(
            "Aun no tienes alumnos registrados."
        )
        return

    lineas = [
        f"TUS ALUMNOS ({len(alumnos)})",
        "",
    ]

    for alumno in alumnos:

        estado = ""

        if not alumno["activo"]:
            estado = " (inactivo)"

        edad = ""

        if alumno["edad"]:
            edad = f", {alumno['edad']} anos"

        lineas.append(
            f"#{alumno['id']} - "
            f"{alumno['nombre']}"
            f"{edad}"
            f"{estado}"
        )

    lineas.extend(
        [
            "",
            "Usa:",
            "/ver_alumno NUM",
            "",
            "Ejemplo:",
            "/ver_alumno 1",
        ]
    )

    await update.message.reply_text(
        "\n".join(lineas)
    )


# ============================================================
# VER ALUMNO
# ============================================================

async def cmd_ver_alumno(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Muestra la ficha de un alumno."""

    if not _es_entrenador(update.effective_user.id):
        await update.message.reply_text(
            "Solo el entrenador puede usar este comando."
        )
        return

    if not context.args:
        await update.message.reply_text(
            "Uso:\n"
            "/ver_alumno NUMERO\n\n"
            "Ejemplo:\n"
            "/ver_alumno 1\n\n"
            "También puedes buscar por nombre:\n"
            "/ver_alumno Juan"
        )
        return

    argumento = " ".join(context.args)

    alumno = None

    if argumento.isdigit():

        alumno = obtener_alumno_por_id(
            int(argumento)
        )

    else:

        encontrados = buscar_alumno_por_nombre(
            argumento
        )

        if len(encontrados) == 1:

            alumno = obtener_alumno_por_id(
                encontrados[0]["id"]
            )

        elif len(encontrados) > 1:

            nombres = "\n".join(
                f"#{a['id']} - {a['nombre']}"
                for a in encontrados
            )

            await update.message.reply_text(
                "Encontré varios alumnos:\n\n"
                f"{nombres}\n\n"
                "Usa el número del alumno."
            )

            return

    if not alumno:

        await update.message.reply_text(
            "No encontré ese alumno."
        )
        return

    # --------------------------------------------------------
    # Estadísticas
    # --------------------------------------------------------

    with conexion() as conn:

        n_medidas = conn.execute(
            """
            SELECT COUNT(*)
            FROM medidas_corporales
            WHERE usuario_id = ?
            """,
            (alumno["id"],),
        ).fetchone()[0]

        n_sesiones = conn.execute(
            """
            SELECT COUNT(*)
            FROM sesiones
            WHERE usuario_id = ?
            """,
            (alumno["id"],),
        ).fetchone()[0]

        n_cardio = conn.execute(
            """
            SELECT COUNT(*)
            FROM registros_cardio
            WHERE usuario_id = ?
            """,
            (alumno["id"],),
        ).fetchone()[0]

        ultima = conn.execute(
            """
            SELECT fecha, peso_kg, grasa_pct, cintura
            FROM medidas_corporales
            WHERE usuario_id = ?
            ORDER BY fecha DESC
            LIMIT 1
            """,
            (alumno["id"],),
        ).fetchone()

    # --------------------------------------------------------
    # Mostrar ficha
    # --------------------------------------------------------

    lineas = [
        f"FICHA DE {alumno['nombre'].upper()}",
        "",
        f"ID: {alumno['id']}",
        f"Telegram: "
        f"{alumno['telegram_id'] or 'Pendiente de vinculación'}",
        f"Estado: "
        f"{'Activo' if alumno['activo'] else 'Inactivo'}",
        "",
        f"Edad: {alumno['edad'] or '-'}",
        f"Sexo: {alumno['sexo'] or '-'}",
        f"Altura: {alumno['altura_cm'] or '-'} cm",
        f"Peso inicial: "
        f"{alumno['peso_inicial_kg'] or '-'} kg",
        f"Grasa inicial: "
        f"{alumno['grasa_inicial_pct'] or '-'} %",
        f"Registrado: "
        f"{alumno['fecha_registro'][:10]}",
        "",
        "ACTIVIDAD",
        f"Medidas: {n_medidas}",
        f"Sesiones gym: {n_sesiones}",
        f"Sesiones cardio: {n_cardio}",
    ]

    if ultima:

        lineas.extend(
            [
                "",
                "ULTIMA MEDIDA",
                f"Fecha: {ultima['fecha'][:10]}",
                f"Peso: {ultima['peso_kg']} kg",
                f"Grasa: {ultima['grasa_pct']} %",
                f"Cintura: {ultima['cintura']} cm",
            ]
        )

    await update.message.reply_text(
        "\n".join(lineas)
    )

# ============================================================
# ELIMINAR ALUMNO
# ============================================================
async def cmd_eliminar_alumno(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Desactiva un alumno y conserva su historial."""

    if not _es_entrenador(update.effective_user.id):
        await update.message.reply_text(
            "Solo el entrenador puede usar este comando."
        )
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            "Uso:\n"
            "/eliminar_alumno NUM\n\n"
            "Ejemplo:\n"
            "/eliminar_alumno 3"
        )
        return

    alumno_id = int(context.args[0])

    alumno = obtener_alumno_por_id(alumno_id)

    if not alumno:
        await update.message.reply_text(
            "No existe ese alumno."
        )
        return

    if not alumno["activo"]:
        await update.message.reply_text(
            "Ese alumno ya está inactivo."
        )
        return

    nombre = alumno["nombre"]

    eliminado = desactivar_alumno(alumno_id)

    if not eliminado:
        await update.message.reply_text(
            "No pude desactivar al alumno."
        )
        return

    await update.message.reply_text(
        f"Alumno desactivado correctamente.\n\n"
        f"Alumno: {nombre}\n"
        f"ID: #{alumno_id}\n\n"
        "Su historial de entrenamientos, medidas y cardio "
        "se conserva en la base de datos."
    )

# ============================================================
# REACTIVAR ALUMNO
# ============================================================
async def cmd_reactivar_alumno(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Reactiva un alumno y genera una nueva invitación."""

    if not _es_entrenador(update.effective_user.id):
        await update.message.reply_text(
            "Solo el entrenador puede usar este comando."
        )
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            "Uso:\n"
            "/reactivar_alumno NUM\n\n"
            "Ejemplo:\n"
            "/reactivar_alumno 3"
        )
        return

    alumno_id = int(context.args[0])

    alumno = obtener_alumno_por_id(alumno_id)

    if not alumno:
        await update.message.reply_text(
            "No existe ese alumno."
        )
        return

    if alumno["activo"]:
        await update.message.reply_text(
            "Ese alumno ya está activo."
        )
        return

    codigo = reactivar_alumno(alumno_id)

    if not codigo:
        await update.message.reply_text(
            "No pude reactivar al alumno."
        )
        return

    await update.message.reply_text(
        "ALUMNO REACTIVADO\n\n"
        f"Alumno: {alumno['nombre']}\n"
        f"ID: #{alumno_id}\n\n"
        f"Nuevo código de invitación:\n"
        f"{codigo}\n\n"
        "Envíale este código al alumno.\n"
        "El alumno debe escribir /start para vincular "
        "nuevamente su cuenta."
    )    


#=============================================================
#Cancelar_invitacion
#=============================================================
async def cancelar_invitacion(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Cancela la creación de una invitación."""

    await update.message.reply_text(
        "Registro cancelado.\n\n"
        "Puedes usar /registrar_alumno cuando quieras."
    )

    context.user_data.clear()

    return ConversationHandler.END

# ============================================================
# FOTOS DEL ALUMNO
# ============================================================

async def cmd_fotos_alumno(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Muestra el historial fotográfico de un alumno."""

    if not _es_entrenador(update.effective_user.id):
        await update.message.reply_text(
            "ACCESO NO AUTORIZADO\n\n"
            "Solo el entrenador puede consultar "
            "las fotos de los alumnos."
        )
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            "Uso:\n"
            "/fotos_alumno NUM\n\n"
            "Ejemplo:\n"
            "/fotos_alumno 3"
        )
        return

    alumno_id = int(context.args[0])

    alumno = obtener_alumno_por_id(alumno_id)

    if not alumno:
        await update.message.reply_text(
            "No encontré ese alumno."
        )
        return

    fotos = obtener_fotos_alumno(alumno_id)

    if not fotos:
        await update.message.reply_text(
            "HISTORIAL FOTOGRÁFICO\n\n"
            f"Alumno: {alumno['nombre']}\n\n"
            "Este alumno todavía no tiene "
            "fotos registradas."
        )
        return

    lineas = [
        "HISTORIAL FOTOGRÁFICO",
        "",
        f"Alumno: {alumno['nombre']}",
        f"Fotos registradas: {len(fotos)}",
        "",
    ]

    for foto in fotos:
        tipo = foto["tipo"].replace(
            "_",
            " "
        ).title()

        fecha = foto["fecha"][:10]

        lineas.append(
            f"#{foto['id']} - 📸 {tipo}\n"
            f"Fecha: {fecha}"
        )

    lineas.extend(
        [
            "",
            "Para ver una foto específica:",
            "/ver_foto_alumno ALUMNO FOTO",
            "",
            "Ejemplo:",
            f"/ver_foto_alumno {alumno_id} "
            f"{fotos[0]['id']}",
        ]
    )

    await update.message.reply_text(
        "\n\n".join(lineas)
    )

"""Ver foto alumno"""
async def cmd_ver_foto_alumno(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Envía al entrenador una foto específica de un alumno."""

    if not _es_entrenador(update.effective_user.id):
        await update.message.reply_text(
            "ACCESO NO AUTORIZADO\n\n"
            "Solo el entrenador puede consultar "
            "las fotos de los alumnos."
        )
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Uso:\n"
            "/ver_foto_alumno ALUMNO FOTO\n\n"
            "Ejemplo:\n"
            "/ver_foto_alumno 3 5"
        )
        return

    if (
        not context.args[0].isdigit()
        or not context.args[1].isdigit()
    ):
        await update.message.reply_text(
            "Los IDs deben ser números.\n\n"
            "Ejemplo:\n"
            "/ver_foto_alumno 3 5"
        )
        return

    alumno_id = int(context.args[0])
    foto_id = int(context.args[1])

    alumno = obtener_alumno_por_id(alumno_id)

    if not alumno:
        await update.message.reply_text(
            "No encontré ese alumno."
        )
        return

    foto = obtener_foto_alumno(
        alumno_id=alumno_id,
        foto_id=foto_id,
    )

    if not foto:
        await update.message.reply_text(
            "No encontré esa foto para ese alumno."
        )
        return

    tipo = foto["tipo"].replace(
        "_",
        " "
    ).title()

    await update.message.reply_photo(
        photo=foto["telegram_file_id"],
        caption=(
            f"📸 {tipo}\n"
            f"Alumno: {alumno['nombre']}\n"
            f"Fecha: {foto['fecha'][:10]}"
        ),
    )

# ============================================================
# REGISTRAR HANDLERS
# ============================================================

def registrar(app):
    """Registra los comandos del entrenador."""

    # Conversación para crear invitación
    invitacion_conv = ConversationHandler(
        entry_points=[
            CommandHandler(
                "registrar_alumno",
                cmd_registrar_alumno,
            )
        ],
        states={
            ESPERANDO_NOMBRE_INVITACION: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    recibir_nombre_invitacion,
                )
            ]
        },
        fallbacks=[
    CommandHandler(
        "cancel",
        cancelar_invitacion,
    )
        ],
        allow_reentry=True,
    )

    app.add_handler(invitacion_conv)

    app.add_handler(
        CommandHandler(
            "alumnos",
            cmd_alumnos,
        )
    )

    app.add_handler(
        CommandHandler(
            "ver_alumno",
            cmd_ver_alumno,
        )
    )

    app.add_handler(
    CommandHandler(
        "eliminar_alumno",
        cmd_eliminar_alumno,
    )
)
    app.add_handler(
        CommandHandler(
            "reactivar_alumno",
            cmd_reactivar_alumno,
        )
    )

    app.add_handler(
        CommandHandler(
            "fotos_alumno",
            cmd_fotos_alumno,
        )
    )

    app.add_handler(
        CommandHandler(
            "ver_foto_alumno",
            cmd_ver_foto_alumno,
        )
    )