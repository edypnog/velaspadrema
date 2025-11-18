import logging
import os
import random
import re
import datetime
from dotenv import load_dotenv

from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode

import database
from config import CANDLE_GIFS

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

CANDLES_PER_PAGE = 10  # Velas por página
MAX_PAGES = 5  # Máximo de páginas a serem exibidas (limite de 50 velas)
MAX_ITEMS = CANDLES_PER_PAGE * MAX_PAGES


def _render_candle_list(velas, current_page, total_items, total_pages):
    """
    Função auxiliar para construir a mensagem e o teclado de paginação.
    Retorna (texto, teclado_inline).
    """
    if not velas:
        return (
            "Nenhuma vela acesa nesta página. Use /vela para acender a primeira! 🔥",
            None,
        )

    # 1. Constrói o texto
    message = f"🕯️ *Velas acesas: Página {current_page} de {total_pages}*\n\n"
    for vela in velas:
        safe_name = escape_markdown_v2(vela["user_name"])
        safe_purpose = escape_markdown_v2(vela["purpose"])
        message += f"`ID: {vela['id']:<3}` \\- *De:* {safe_name}\n"
        message += f"> {safe_purpose}\n\n"

    # 2. Constrói o teclado
    row = []

    # Botão Anterior
    if current_page > 1:
        row.append(
            InlineKeyboardButton("⬅️ Anterior", callback_data=f"list_{current_page - 1}")
        )

    # Indicador de Página (Não faz nada)
    row.append(
        InlineKeyboardButton(
            f"Página {current_page}/{total_pages}", callback_data="none"
        )
    )

    # Botão Próximo
    if current_page < total_pages:
        row.append(
            InlineKeyboardButton("Próximo ➡️", callback_data=f"list_{current_page + 1}")
        )

    return message, InlineKeyboardMarkup([row])


def escape_markdown_v2(text: str) -> str:
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)


async def post_init(application: Application):
    """
    Função para rodar após a inicialização, para configurar os comandos do bot.
    """
    commands = [
        BotCommand("start", "Inicia o bot e mostra os comandos"),
        BotCommand("vela", "Cria uma nova vela"),
        BotCommand("listar", "Mostra as últimas velas acesas"),
        BotCommand("minhasvelas", "Mostra todas as velas que você acendeu"),
        BotCommand("ver", "Vê os detalhes de uma vela"),
        BotCommand("editar", "Altera o propósito de uma vela sua"),
        BotCommand("excluir", "Apaga uma vela sua"),
    ]
    await application.bot.set_my_commands(commands)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envia uma mensagem de boas-vindas com a lista de comandos atualizada."""
    photo_url = "https://i.postimg.cc/rwNB8xtm/ma.jpg"
    texto_boas_vindas = (
        "Olá\\! ✨ Eu sou o Padre Marcelo Rossi\\.\n\n"
        "Você pode acender uma vela para qualquer intenção\\.\n\n"
        "*Comandos:*\n"
        "`/vela <propósito>` \\- Acende uma nova vela\\.\n"
        "`/minhasvelas` \\- Mostra todas as suas velas\\.\n"
        "`/listar` \\- Mostra as últimas velas acesas\\.\n"
        "`/ver <ID>` \\- Todos os detalhes de uma vela\\.\n"
        "`/editar <ID> <novo propósito>` \\- Altera o propósito de uma vela sua\\.\n"
        "`/excluir <ID>` \\- Apaga uma vela sua\\."
    )
    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=photo_url,
        caption=texto_boas_vindas,
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def vela(update: Update, context: ContextTypes.DEFAULT_TYPE):
    purpose = " ".join(context.args)
    if not purpose:
        await update.message.reply_text(
            "Por favor, escreva um propósito após o comando\\. Ex: `/vela pela paz mundial`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    user = update.message.from_user
    gif_url = random.choice(CANDLE_GIFS)
    success = database.add_candle(user.id, user.first_name, purpose, gif_url)

    if success:
        safe_name = escape_markdown_v2(user.first_name)
        safe_purpose = escape_markdown_v2(purpose)
        caption = f"*De:* `{safe_name}`\n\n> {safe_purpose}"
        await context.bot.send_animation(
            chat_id=update.effective_chat.id,
            animation=gif_url,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    else:
        logging.error("Falha ao salvar a vela no banco de dados.")


async def listar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Tenta obter a página a partir dos argumentos (e valida)
    page = 1
    if context.args:
        try:
            page = max(1, int(context.args[0]))
        except ValueError:
            pass  # Permanece na página 1

    # 2. Calcula limites
    total_items = database.get_total_candles_count()

    # Limita o total de páginas ao máximo exigido (5)
    total_pages_disponiveis = (total_items + CANDLES_PER_PAGE - 1) // CANDLES_PER_PAGE
    total_pages = min(MAX_PAGES, total_pages_disponiveis)

    if total_items == 0:
        await update.message.reply_text(
            "Nenhuma vela acesa no momento\\. Use `/vela` para acender a primeira\\! 🔥",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    # 3. Garante que a página não excede o limite
    if page > total_pages:
        page = total_pages

    # 4. Calcula offset e busca os dados
    offset = (page - 1) * CANDLES_PER_PAGE
    velas = database.get_paginated_candles(CANDLES_PER_PAGE, offset)

    if velas is None:
        logging.error("Falha ao buscar velas paginadas no banco de dados.")
        await update.message.reply_text(
            "Ocorreu um erro ao buscar velas no banco de dados\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    # 5. Renderiza e envia a resposta
    message, reply_markup = _render_candle_list(velas, page, total_items, total_pages)

    await update.message.reply_text(
        message, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=reply_markup
    )


async def pagination_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lida com cliques nos botões de paginação."""
    query = update.callback_query
    await query.answer()  # Fecha o aviso de carregamento no Telegram

    # Extrai o número da nova página do dado de callback ("list_X")
    try:
        page = int(query.data.split("_")[1])
    except (IndexError, ValueError):
        return

    # Repete a lógica de limite e busca para a nova página
    total_items = database.get_total_candles_count()
    total_pages_disponiveis = (total_items + CANDLES_PER_PAGE - 1) // CANDLES_PER_PAGE
    total_pages = min(MAX_PAGES, total_pages_disponiveis)

    if page > total_pages:
        page = total_pages

    offset = (page - 1) * CANDLES_PER_PAGE
    velas = database.get_paginated_candles(CANDLES_PER_PAGE, offset)

    if velas is None:
        logging.error("Falha ao buscar velas paginadas via callback.")
        return

    # Renderiza e edita a mensagem original
    message, reply_markup = _render_candle_list(velas, page, total_items, total_pages)

    # Usa edit_message_caption pois a mensagem original tem um cabeçalho
    await query.edit_message_caption(
        caption=message,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=reply_markup,
    )


async def ver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Por favor, informe o ID da vela\\. Ex: `/ver 5`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return
    try:
        candle_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "O ID precisa ser um número\\.", parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    vela = database.get_candle_by_id(candle_id)
    if vela is None:
        await update.message.reply_text(
            f"Não foi possível encontrar a vela com ID `{candle_id}`\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    gif_url_salvo = vela["gif_url"]
    timestamp_obj = datetime.datetime.fromisoformat(vela["timestamp"])
    timestamp_formatado = escape_markdown_v2(
        timestamp_obj.strftime("%d/%m/%Y às %H:%M")
    )
    safe_name = escape_markdown_v2(vela["user_name"])
    safe_purpose = escape_markdown_v2(vela["purpose"])
    caption = (
        f"*Detalhes da Vela ID:* `{vela['id']}`\n"
        f"*Acesa por:* {safe_name}\n"
        f"*Em:* {timestamp_formatado}\n\n"
        f"> {safe_purpose}"
    )
    await context.bot.send_animation(
        chat_id=update.effective_chat.id,
        animation=gif_url_salvo,
        caption=caption,
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def minhasvelas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista todas as velas acesas pelo usuário que enviou o comando."""
    user_id = update.message.from_user.id

    # Chama a nova função do banco de dados
    velas = database.get_candles_by_user(user_id)

    if velas is None:
        logging.error(f"Falha ao buscar velas do usuário {user_id} no banco de dados.")
        await update.message.reply_text(
            "Ocorreu um erro ao buscar suas velas\\. Tente novamente mais tarde\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    if not velas:
        await update.message.reply_text(
            "Você ainda não acendeu nenhuma vela\\. Use `/vela` para acender a sua primeira\\! 🔥",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    message = "🕯️ *Suas velas acesas:*\n\n"
    for vela in velas:
        safe_purpose = escape_markdown_v2(vela["purpose"])

        # Formata a data para ficar mais amigável
        timestamp_obj = datetime.datetime.fromisoformat(vela["timestamp"])
        timestamp_formatado = escape_markdown_v2(timestamp_obj.strftime("%d/%m/%Y"))

        message += f"`ID: {vela['id']:<3}` \\({timestamp_formatado}\\)\n"
        message += f"> {safe_purpose}\n\n"

    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN_V2)


# --- NOVA FUNÇÃO ---
async def excluir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exclui uma vela que pertence ao usuário."""
    if not context.args:
        await update.message.reply_text(
            "Por favor, informe o ID da vela que deseja excluir\\. Ex: `/excluir 5`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return
    try:
        candle_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "O ID precisa ser um número\\.", parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    user_id = update.message.from_user.id
    success = database.delete_candle(candle_id, user_id)

    if success:
        await update.message.reply_text(
            f"Vela ID `{candle_id}` excluída com sucesso\\!",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    else:
        await update.message.reply_text(
            f"Não foi possível excluir a vela ID `{candle_id}`\\. Verifique se o ID está correto e se a vela pertence a você\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )


# --- NOVA FUNÇÃO ---
async def editar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Edita o propósito de uma vela que pertence ao usuário."""
    if len(context.args) < 2:
        await update.message.reply_text(
            "Uso incorreto\\. Por favor, informe o ID e o novo propósito\\.\n"
            "Ex: `/editar 5 pra passar na prova`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return
    try:
        candle_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "O ID precisa ser um número\\.", parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    new_purpose = " ".join(context.args[1:])
    user_id = update.message.from_user.id
    success = database.update_candle_purpose(candle_id, user_id, new_purpose)

    if success:
        safe_purpose = escape_markdown_v2(new_purpose)
        await update.message.reply_text(
            f"Vela ID `{candle_id}` atualizada com sucesso\\!\n\n> {safe_purpose}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    else:
        await update.message.reply_text(
            f"Não foi possível editar a vela ID `{candle_id}`\\. Verifique se o ID está correto e se a vela pertence a você\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )


def main():
    load_dotenv()
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        print("Erro: O token do Telegram não foi encontrado.")
        return

    database.init_db()

    application = Application.builder().token(TOKEN).post_init(post_init).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("vela", vela))
    application.add_handler(CommandHandler("listar", listar))
    # O padrão r'^list_\d+$' garante que só responde a cliques nos botões de paginação
    application.add_handler(
        CallbackQueryHandler(pagination_callback, pattern=r"^list_\d+$")
    )
    application.add_handler(CommandHandler("ver", ver))
    application.add_handler(CommandHandler("minhasvelas", minhasvelas))
    application.add_handler(CommandHandler("excluir", excluir))
    application.add_handler(CommandHandler("editar", editar))

    print("Bot iniciado! Pressione Ctrl+C para parar.")
    application.run_polling()


if __name__ == "__main__":
    main()
