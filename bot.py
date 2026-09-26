import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام 👋\n"
        "به ربات HanzuVPN خوش آمدید 🌐\n\n"
        "برای مشاهده سرویس‌ها از منوی ربات استفاده کنید."
    )


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN تنظیم نشده است.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    print("HanzuVPN Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
