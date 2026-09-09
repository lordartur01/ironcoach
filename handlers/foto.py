from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from services.auth import obtener_usuario
from services.fotos import (
    guardar_foto,
    obtener_fotos_usuario,
    obtener_foto_por_id,
)
from services.alertas import notificar_entrenador

ESPERANDO_TIPO_FOTO = 1
ESPERANDO_IMAGEN = 2


async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela el flujo de fotos."""
    await update.message.reply_text(
        "Operación cancelada.\n\n"
        "Escribe /foto cuando quieras registrar una nueva foto."
    )
    context.user_data.clear()
    return ConversationHandler.END

#crear un comando /foto que inicie el proceso de registro de fotos

async def cmd_foto(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:

    usuario = obtener_usuario(
        update.effective_user.id
    )

    if not usuario:
        await update.message.reply_text(
            "ACCESO NO AUTORIZADO\n\n"
            "Escribe /start para vincular tu cuenta."
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "REGISTRO FOTOGRÁFICO\n\n"
        "Escribe el tipo de foto:\n\n"
        "frente\n"
        "espalda\n"
        "perfil_izquierdo\n"
        "perfil_derecho\n"
        "libre"
    )

    return ESPERANDO_TIPO_FOTO


#RECIBIR TIPO DE FOTO Y PEDIR IMAGEN

async def recibir_tipo_foto(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:

    tipo = update.message.text.strip().lower()

    tipos_validos = [
        "frente",
        "espalda",
        "perfil_izquierdo",
        "perfil_derecho",
        "libre",
    ]

    if tipo not in tipos_validos:

        await update.message.reply_text(
            "Tipo no válido.\n\n"
            "Opciones:\n"
            "frente\n"
            "espalda\n"
            "perfil_izquierdo\n"
            "perfil_derecho\n"
            "libre"
        )

        return ESPERANDO_TIPO_FOTO

    context.user_data["tipo_foto"] = tipo

    await update.message.reply_text(
        "Perfecto.\n\n"
        "Ahora envía la fotografía."
    )

    return ESPERANDO_IMAGEN


# =============================================
#RECIBIR MIS FOTOS
# =============================================
async def cmd_mis_fotos(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    usuario = obtener_usuario(
        update.effective_user.id
    )

    if not usuario:
        await update.message.reply_text(
            "ACCESO NO AUTORIZADO\n\n"
            "Necesitas una cuenta activa y vinculada."
        )
        return

    fotos = obtener_fotos_usuario(
        usuario["id"]
    )

    if not fotos:
        await update.message.reply_text(
            "HISTORIAL FOTOGRÁFICO\n\n"
            "Todavía no tienes fotos registradas."
        )
        return

    lineas = [
        "HISTORIAL FOTOGRÁFICO",
        "",
        f"Fotos registradas: {len(fotos)}",
        "",
    ]

    for foto in fotos:
        fecha = foto["fecha"][:10]

        tipo = foto["tipo"].replace(
            "_",
            " "
        ).title()

        lineas.append(
            f"#{foto['id']} - 📸 {tipo}\n"
            f"Fecha: {fecha}"
        )

    await update.message.reply_text(
        "\n\n".join(lineas)
    )


#VER FOTO

async def cmd_ver_foto(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    usuario = obtener_usuario(
        update.effective_user.id
    )

    if not usuario:
        await update.message.reply_text(
            "ACCESO NO AUTORIZADO\n\n"
            "Necesitas una cuenta activa y vinculada."
        )
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            "Uso:\n"
            "/ver_foto NUM\n\n"
            "Ejemplo:\n"
            "/ver_foto 1"
        )
        return

    foto_id = int(context.args[0])

    foto = obtener_foto_por_id(
        foto_id=foto_id,
        usuario_id=usuario["id"],
    )

    if not foto:
        await update.message.reply_text(
            "No encontré esa foto."
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
            f"Fecha: {foto['fecha'][:10]}"
        ),
    )

#RECIBIR IMAGEN Y GUARDARLA EN LA BASE DE DATOS
async def recibir_foto(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:

    usuario = obtener_usuario(
        update.effective_user.id
    )

    if not usuario:
        return ConversationHandler.END

    foto = update.message.photo[-1]

    telegram_file_id = foto.file_id

    tipo = context.user_data["tipo_foto"]

    guardar_foto(
        usuario_id=usuario["id"],
        tipo=tipo,
        telegram_file_id=telegram_file_id,
    )

    if usuario["rol"] == "alumno":

        await notificar_entrenador(
    context.application,
    (
        "🔔 NUEVA FOTO DE PROGRESO\n\n"
        f"Alumno: {usuario['nombre']}\n"
        f"Tipo: {tipo}"
    ),
)

    await update.message.reply_text(
        "📸 Foto registrada correctamente.\n\n"
        f"Tipo: {tipo}"
    )

    context.user_data.clear()

    return ConversationHandler.END

#REGISTRAR 

def handler():

    return ConversationHandler(
        entry_points=[
    CommandHandler(
        "foto",
        cmd_foto,
    ),
    CommandHandler(
        "mis_fotos",
        cmd_mis_fotos,
    ),
    CommandHandler(
        "ver_foto",
        cmd_ver_foto,
    ),
],

        states={
            ESPERANDO_TIPO_FOTO: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    recibir_tipo_foto,
                )
            ],

            ESPERANDO_IMAGEN: [
                MessageHandler(
                    filters.PHOTO,
                    recibir_foto,
                )
            ],
        },

        fallbacks=[
            CommandHandler(
                "cancel",
                lambda u, c: ConversationHandler.END,
            )
        ],

        allow_reentry=True,
    )