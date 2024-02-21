import os
import logging
import asyncio
import traceback
import html
import json
import tempfile
import pydub
from pathlib import Path
from datetime import datetime
import openai

import telegram
from telegram import (
    Update,
    User,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackContext,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    AIORateLimiter,
    filters
)
from telegram.constants import ParseMode, ChatAction

import config
from database import Database  # Ensure Database class is correctly imported
import openai_utils

# setup
db = Database()
logger = logging.getLogger(__name__)

user_semaphores = {}
user_tasks = {}

HELP_MESSAGE = """Commands:
⚪ /retry – Regenerate last bot answer
⚪ /new – Start new dialog
⚪ /mode – Select chat mode
⚪ /settings – Show settings
⚪ /balance – Show balance
⚪ /help – Show help
⚪ /add_journal_entry - Add a new journal entry

🎨 Generate images from text prompts in <b>👩‍🎨 Artist</b> /mode
👥 Add bot to <b>group chat</b>: /help_group_chat
🎤 You can send <b>Voice Messages</b> instead of text
"""

HELP_GROUP_CHAT_MESSAGE = """You can add bot to any <b>group chat</b> to help and entertain its participants!

Instructions (see <b>video</b> below):
1. Add the bot to the group chat
2. Make it an <b>admin</b>, so that it can see messages (all other rights can be restricted)
3. You're awesome!

To get a reply from the bot in the chat – @ <b>tag</b> it or <b>reply</b> to its message.
For example: "{bot_username} write a poem about Telegram"
"""

# Add the new add_journal_entry_handle function here
async def add_journal_entry_handle(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    args = context.args  # Assuming the command format is /add_journal_entry <category> <content>
    
    if len(args) < 2:
        await update.message.reply_text("Usage: /add_journal_entry <category> <content>")
        return
    
    category = args[0]
    content = " ".join(args[1:])
    
    db.add_journal_entry(user_id, category, content)
    await update.message.reply_text("Journal entry added successfully.")

# Include other handlers and functions as they were in your initial setup

def run_bot() -> None:
    application = (
        ApplicationBuilder()
        .token(config.telegram_token)
        .concurrent_updates(True)
        .rate_limiter(AIORateLimiter(max_retries=5))
        .http_version("1.1")
        .get_updates_http_version("1.1")
        .post_init(post_init)
        .build()
    )

    # add handlers including the new add_journal_entry_handle
    application.add_handler(CommandHandler("start", start_handle, filters=filters.ALL))
    application.add_handler(CommandHandler("add_journal_entry", add_journal_entry_handle, filters=filters.ALL))
    # Add the rest of your handlers here

    # start the bot
    application.run_polling()

if __name__ == "__main__":
    run_bot()
