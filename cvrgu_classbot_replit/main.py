import os
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from bot_core import (
    start, help_cmd, today, next_cmd, subscribe, setgroup, text_router,
)
from keep_alive import keep_alive

def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in Replit Secrets.")
    # start the tiny web server so you can ping it to keep the repl awake
    keep_alive()
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("next", next_cmd))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("setgroup", setgroup))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
