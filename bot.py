import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CARD_NUMBER = os.getenv("CARD_NUMBER", "")

PLANS = {
    "10": ("10 گیگ", 35000),
    "20": ("20 گیگ", 70000),
    "30": ("30 گیگ", 105000),
    "40": ("40 گیگ", 140000),
    "50": ("50 گیگ", 175000),
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🛒 خرید سرویس", callback_data="buy")],
        [InlineKeyboardButton("📦 سرویس‌های من", callback_data="services")],
        [InlineKeyboardButton("💬 پشتیبانی", callback_data="support")],
    ]

    await update.message.reply_text(
        "🌐 HanzuVPN\n\n"
        "به ربات فروش HanzuVPN خوش آمدید.\n\n"
        "یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "buy":
        keyboard = [
            [InlineKeyboardButton("10 گیگ | 35,000 تومان", callback_data="p10")],
            [InlineKeyboardButton("20 گیگ | 70,000 تومان", callback_data="p20")],
            [InlineKeyboardButton("30 گیگ | 105,000 تومان", callback_data="p30")],
            [InlineKeyboardButton("40 گیگ | 140,000 تومان", callback_data="p40")],
            [InlineKeyboardButton("50 گیگ | 175,000 تومان", callback_data="p50")],
            [InlineKeyboardButton("حجم دلخواه", callback_data="custom")],
        ]

        await query.edit_message_text(
            "🛒 سرویس‌های HanzuVPN\n\n"
            "همه سرویس‌ها 30 روزه هستند.\n"
            "حجم موردنظر را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data.startswith("p"):
        volume = query.data[1:]
        volume_name, price = PLANS[volume]

        context.user_data["volume"] = volume_name
        context.user_data["price"] = price

        keyboard = [
            [InlineKeyboardButton("💳 پرداخت کردم", callback_data="paid")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="buy")],
        ]

        await query.edit_message_text(
            f"🌐 سرویس: {volume_name}\n"
            f"⏳ مدت: 30 روز\n"
            f"💰 مبلغ: {price:,} تومان\n\n"
            f"💳 شماره کارت:\n{CARD_NUMBER}\n\n"
            "پس از پرداخت روی دکمه «پرداخت کردم» بزنید.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "custom":
        context.user_data["custom"] = True

        await query.edit_message_text(
            "🔹 حجم دلخواه\n\n"
            "حجم موردنظر را به صورت عدد بفرستید.\n\n"
            "مثال: 25\n\n"
            "قیمت هر گیگ: 3,500 تومان"
        )

    elif query.data == "paid":
        context.user_data["receipt"] = True

        await query.edit_message_text(
            "📸 ارسال رسید\n\n"
            "لطفاً عکس رسید پرداخت را همینجا ارسال کنید."
        )

    elif query.data == "services":
        await query.edit_message_text(
            "📦 سرویس‌های من\n\n"
            "در حال حاضر سرویس فعالی ثبت نشده است."
        )

    elif query.data == "support":
        await query.edit_message_text(
            "💬 پشتیبانی HanzuVPN\n\n"
            "برای پشتیبانی با مدیریت در ارتباط باشید."
        )


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("custom"):
        return

    try:
        volume = int(update.message.text)
    except ValueError:
        await update.message.reply_text(
            "❌ فقط عدد وارد کنید.\nمثال: 25"
        )
        return

    if volume <= 0:
        await update.message.reply_text(
            "❌ حجم باید بیشتر از صفر باشد."
        )
        return

    price = volume * 3500

    context.user_data["custom"] = False
    context.user_data["volume"] = f"{volume} گیگ"
    context.user_data["price"] = price

    keyboard = [
        [InlineKeyboardButton("💳 پرداخت کردم", callback_data="paid")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="buy")],
    ]

    await update.message.reply_text(
        f"🌐 سرویس: {volume} گیگ\n"
        f"⏳ مدت: 30 روز\n"
        f"💰 مبلغ: {price:,} تومان\n\n"
        f"💳 شماره کارت:\n{CARD_NUMBER}\n\n"
        "پس از پرداخت روی «پرداخت کردم» بزنید.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("receipt"):
        return

    photo = update.message.photo[-1]
    user = update.effective_user

    volume = context.user_data.get("volume", "نامشخص")
    price = context.user_data.get("price", 0)

    username = user.username if user.username else "ندارد"

    message = (
        "🔔 رسید پرداخت جدید\n\n"
        f"👤 نام: {user.full_name}\n"
        f"👤 Username: @{username}\n"
        f"🆔 User ID: {user.id}\n\n"
        f"📦 سرویس: {volume}\n"
        f"💰 مبلغ: {price:,} تومان"
    )

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo.file_id,
        caption=message,
    )

    context.user_data["receipt"] = False

    await update.message.reply_text(
        "✅ رسید دریافت شد.\n\n"
        "پرداخت شما توسط مدیریت بررسی می‌شود."
    )


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN تنظیم نشده است.")

    if not ADMIN_ID:
        raise ValueError("ADMIN_ID تنظیم نشده است.")

    if not CARD_NUMBER:
        raise ValueError("CARD_NUMBER تنظیم نشده است.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        CallbackQueryHandler(buttons)
    )

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            photo_handler
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler
        )
    )

    print("HanzuVPN Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
