import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🛒 خرید سرویس", callback_data="buy")],
        [InlineKeyboardButton("📦 سرویس‌های من", callback_data="my_services")],
        [InlineKeyboardButton("💬 پشتیبانی", callback_data="support")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🌐 HanzuVPN\n\n"
        "به ربات فروش HanzuVPN خوش آمدید.\n\n"
        "از منوی زیر گزینه موردنظر خود را انتخاب کنید:",
        reply_markup=reply_markup,
    )


async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    if query.data == "buy":
        keyboard = [
            [InlineKeyboardButton("🔹 سرویس 30 روزه", callback_data="plan_30")],
            [InlineKeyboardButton("🔹 سرویس 60 روزه", callback_data="plan_60")],
            [InlineKeyboardButton("🔹 سرویس 90 روزه", callback_data="plan_90")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back")],
        ]

        await query.edit_message_text(
            "🛒 انتخاب سرویس\n\n"
            "پلن موردنظر خود را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "plan_30":
        await query.edit_message_text(
            "🔹 سرویس 30 روزه\n\n"
            "💰 قیمت: به‌زودی\n\n"
            "برای خرید این سرویس، ادامه مراحل را انجام دهید."
        )

    elif query.data == "plan_60":
        await query.edit_message_text(
            "🔹 سرویس 60 روزه\n\n"
            "💰 قیمت: به‌زودی\n\n"
            "برای خرید این سرویس، ادامه مراحل را انجام دهید."
        )

    elif query.data == "plan_90":
        await query.edit_message_text(
            "🔹 سرویس 90 روزه\n\n"
            "💰 قیمت: به‌زودی\n\n"
            "برای خرید این سرویس، ادامه مراحل را انجام دهید."
        )

    elif query.data == "my_services":
        await query.edit_message_text(
            "📦 سرویس‌های شما\n\n"
            "در حال حاضر سرویس فعالی برای شما ثبت نشده است."
        )

    elif query.data == "support":
        await query.edit_message_text(
            "💬 پشتیبانی HanzuVPN\n\n"
            "برای ارتباط با پشتیبانی، از آیدی پشتیبانی کانال استفاده کنید."
        )

    elif query.data == "back":
        keyboard = [
            [InlineKeyboardButton("🛒 خرید سرویس", callback_data="buy")],
            [InlineKeyboardButton("📦 سرویس‌های من", callback_data="my_services")],
            [InlineKeyboardButton("💬 پشتیبانی", callback_data="support")],
        ]

        await query.edit_message_text(
            "🌐 HanzuVPN\n\n"
            "گزینه موردنظر را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN تنظیم نشده است.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("HanzuVPN Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
