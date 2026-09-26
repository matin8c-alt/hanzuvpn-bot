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

    context.user_data["volume"] = f"{volume} گیگ"
    context.user_data["price"] = price
    context.user_data["waiting_custom"] = False

    keyboard = [
        [InlineKeyboardButton("💳 پرداخت کردم", callback_data="paid")],
        [InlineKeyboardButton("🛒 انتخاب دوباره", callback_data="buy")],
    ]

    await update.message.reply_text(
        f"🌐 سرویس {volume} گیگ\n"
        f"⏳ مدت: ۳۰ روز\n"
        f"💰 مبلغ: {price:,} تومان\n\n"
        f"💳 شماره کارت:\n"
        f"`{CARD_NUMBER}`\n\n"
        "بعد از انتقال وجه، روی «پرداخت کردم» بزنید.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def receipt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_receipt"):
        return

    if not update.message.photo:
        await update.message.reply_text(
            "❌ لطفاً عکس رسید پرداخت را ارسال کنید."
        )
        return

    photo = update.message.photo[-1]
    user = update.effective_user

    volume = context.user_data.get("volume", "نامشخص")
    price = context.user_data.get("price", 0)

    username = f"@{user.username}" if user.username else "ندارد"

    caption = (
        "🔔 رسید پرداخت جدید\n\n"
        f"👤 نام: {user.full_name}\n"
        f"🆔 Username: {username}\n"
        f"🔢 User ID: {user.id}\n\n"
        f"📦 سرویس: {volume}\n"
        f"💰 مبلغ: {price:,} تومان\n\n"
        "⚠️ لطفاً پرداخت را بررسی کنید."
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ تأیید پرداخت",
                callback_data=f"approve_{user.id}",
            ),
            InlineKeyboardButton(
                "❌ رد پرداخت",
                callback_data=f"reject_{user.id}",
            ),
        ]
    ]

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo.file_id,
        caption=caption,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    context.user_data["waiting_receipt"] = False

    await update.message.reply_text(
        "✅ رسید شما دریافت شد.\n\n"
        "در حال بررسی پرداخت توسط پشتیبانی هستیم."
    )


async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query.from_user.id != ADMIN_ID:
        await query.answer(
            "شما دسترسی مدیریت ندارید.",
            show_alert=True,
        )
        return

    await query.answer()

    if query.data.startswith("approve_"):
        user_id = int(query.data.replace("approve_", ""))

        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "✅ پرداخت شما تأیید شد.\n\n"
                "کانفیگ سرویس پس از آماده‌سازی برای شما ارسال می‌شود."
            ),
        )

        await query.edit_message_caption(
            caption=query.message.caption + "\n\n✅ پرداخت تأیید شد."
        )

    elif query.data.startswith("reject_"):
        user_id = int(query.data.replace("reject_", ""))

        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "❌ پرداخت شما تأیید نشد.\n\n"
                "لطفاً با پشتیبانی تماس بگیرید."
            ),
        )

        await query.edit_message_caption(
            caption=query.message.caption + "\n\n❌ پرداخت رد شد."
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
        CallbackQueryHandler(
            admin_handler,
            pattern=r"^(approve_|reject_)",
        )
    )

    app.add_handler(
        CallbackQueryHandler(button_handler)
    )

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            receipt_handler,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            custom_volume,
        )
    )

    print("HanzuVPN Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
