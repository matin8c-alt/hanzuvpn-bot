import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CARD_NUMBER = os.getenv("CARD_NUMBER", "")

PLANS = {
    "10": {"volume": "10 گیگ", "price": 35000},
    "20": {"volume": "20 گیگ", "price": 70000},
    "30": {"volume": "30 گیگ", "price": 105000},
    "40": {"volume": "40 گیگ", "price": 140000},
    "50": {"volume": "50 گیگ", "price": 175000},
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🛒 خرید سرویس", callback_data="buy")],
        [InlineKeyboardButton("📦 سرویس‌های من", callback_data="my_services")],
        [InlineKeyboardButton("💬 پشتیبانی", callback_data="support")],
    ]

    await update.message.reply_text(
        "🌐 HanzuVPN\n\n"
        "به ربات فروش HanzuVPN خوش آمدید.\n\n"
        "گزینه موردنظر را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "buy":
        keyboard = [
            [InlineKeyboardButton("🔹 ۱۰ گیگ | ۳۵٬۰۰۰ تومان", callback_data="plan_10")],
            [InlineKeyboardButton("🔹 ۲۰ گیگ | ۷۰٬۰۰۰ تومان", callback_data="plan_20")],
            [InlineKeyboardButton("🔹 ۳۰ گیگ | ۱۰۵٬۰۰۰ تومان", callback_data="plan_30")],
            [InlineKeyboardButton("🔹 ۴۰ گیگ | ۱۴۰٬۰۰۰ تومان", callback_data="plan_40")],
            [InlineKeyboardButton("🔹 ۵۰ گیگ | ۱۷۵٬۰۰۰ تومان", callback_data="plan_50")],
            [InlineKeyboardButton("🔹 حجم دلخواه", callback_data="custom")],
        ]

        await query.edit_message_text(
            "🛒 انتخاب حجم سرویس\n\n"
            "تمام سرویس‌ها ۳۰ روزه هستند.\n\n"
            "حجم موردنظر را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data.startswith("plan_"):
        volume = query.data.replace("plan_", "")
        plan = PLANS[volume]

        context.user_data["volume"] = plan["volume"]
        context.user_data["price"] = plan["price"]

        keyboard = [
            [InlineKeyboardButton("💳 پرداخت کردم", callback_data="paid")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="buy")],
        ]

        await query.edit_message_text(
            f"🌐 سرویس {plan['volume']}\n"
            f"⏳ مدت: ۳۰ روز\n"
            f"💰 مبلغ: {plan['price']:,} تومان\n\n"
            f"💳 شماره کارت:\n"
            f"`{CARD_NUMBER}`\n\n"
            "بعد از انتقال وجه، روی «پرداخت کردم» بزنید.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "custom":
        context.user_data["waiting_custom"] = True

        await query.edit_message_text(
            "🔹 حجم دلخواه\n\n"
            "حجم موردنظر را فقط به صورت عدد ارسال کنید.\n\n"
            "مثلاً: 25\n\n"
            "قیمت هر گیگ: ۳٬۵۰۰ تومان"
        )

    elif query.data == "paid":
        context.user_data["waiting_receipt"] = True

        await query.edit_message_text(
            "📸 ارسال رسید پرداخت\n\n"
            "لطفاً عکس رسید پرداخت را همینجا ارسال کنید.\n\n"
            "بعد از بررسی، نتیجه اعلام می‌شود."
        )

    elif query.data == "my_services":
        await query.edit_message_text(
            "📦 سرویس‌های شما\n\n"
            "هنوز سرویسی برای این حساب ثبت نشده است."
        )

    elif query.data == "support":
        await query.edit_message_text(
            "💬 پشتیبانی HanzuVPN\n\n"
            "در صورت مشکل در خرید یا پرداخت، با پشتیبانی تماس بگیرید."
        )


async def custom_volume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_custom"):
        return

    try:
        volume = int(update.message.text)

        if volume <= 0:
            raise ValueError

    except ValueError:
        await update.message.reply_text(
            "❌ لطفاً فقط یک عدد صحیح وارد کنید.\n\n"
            "مثلاً: 25"
        )
        return

    price = volume * 3500

    context.user_data["volume"]
