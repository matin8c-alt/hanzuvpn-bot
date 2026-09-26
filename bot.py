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
    "10": 35000,
    "20": 70000,
    "30": 105000,
    "40": 140000,
    "50": 175000,
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
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    try:
        await query.answer()

        data = query.data

        # خرید سرویس
        if data == "buy":

            keyboard = [
                [InlineKeyboardButton(
                    "10 گیگ | 35,000 تومان",
                    callback_data="plan_10"
                )],

                [InlineKeyboardButton(
                    "20 گیگ | 70,000 تومان",
                    callback_data="plan_20"
                )],

                [InlineKeyboardButton(
                    "30 گیگ | 105,000 تومان",
                    callback_data="plan_30"
                )],

                [InlineKeyboardButton(
                    "40 گیگ | 140,000 تومان",
                    callback_data="plan_40"
                )],

                [InlineKeyboardButton(
                    "50 گیگ | 175,000 تومان",
                    callback_data="plan_50"
                )],

                [InlineKeyboardButton(
                    "🔹 حجم دلخواه",
                    callback_data="custom"
                )],

                [InlineKeyboardButton(
                    "🔙 بازگشت",
                    callback_data="home"
                )]
            ]

            await query.edit_message_text(
                "🛒 سرویس‌های HanzuVPN\n\n"
                "⏳ مدت همه سرویس‌ها: 30 روز\n\n"
                "حجم موردنظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        # صفحه اصلی
        elif data == "home":

            keyboard = [
                [InlineKeyboardButton(
                    "🛒 خرید سرویس",
                    callback_data="buy"
                )],

                [InlineKeyboardButton(
                    "📦 سرویس‌های من",
                    callback_data="services"
                )],

                [InlineKeyboardButton(
                    "💬 پشتیبانی",
                    callback_data="support"
                )]
            ]

            await query.edit_message_text(
                "🌐 HanzuVPN\n\n"
                "یکی از گزینه‌های زیر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        # پلن‌های آماده
        elif data.startswith("plan_"):

            volume = data.replace("plan_", "")

            if volume not in PLANS:
                await query.edit_message_text(
                    "❌ سرویس پیدا نشد."
                )
                return

            price = PLANS[volume]

            keyboard = [
                [InlineKeyboardButton(
                    "💳 پرداخت کردم",
                    callback_data=f"paid_{volume}_{price}"
                )],

                [InlineKeyboardButton(
                    "🔙 بازگشت",
                    callback_data="buy"
                )]
            ]

            await query.edit_message_text(
                f"🌐 سرویس: {volume} گیگ\n"
                f"⏳ مدت: 30 روز\n"
                f"💰 مبلغ: {price:,} تومان\n\n"
                f"💳 شماره کارت:\n"
                f"{CARD_NUMBER}\n\n"
                "بعد از پرداخت روی دکمه زیر بزنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        # پرداخت
        elif data.startswith("paid_"):

            parts = data.split("_")

            if len(parts) != 3:

                await query.edit_message_text(
                    "❌ اطلاعات پرداخت نامعتبر است."
                )
                return

            volume = parts[1]
            price = int(parts[2])

            context.user_data["volume"] = f"{volume} گیگ"
            context.user_data["price"] = price
            context.user_data["waiting_receipt"] = True

            await query.edit_message_text(
                "✅ درخواست پرداخت ثبت شد.\n\n"
                "📸 حالا عکس رسید پرداخت را همینجا ارسال کنید.\n\n"
                "⚠️ لطفاً فقط عکس رسید را ارسال کنید."
            )

        # حجم دلخواه
        elif data == "custom":

            context.user_data["waiting_custom"] = True

            await query.edit_message_text(
                "🔹 حجم دلخواه\n\n"
                "حجم موردنظر را به صورت عدد ارسال کنید.\n\n"
                "مثال:\n"
                "25\n\n"
                "💰 قیمت هر گیگ: 3,500 تومان"
            )

        # سرویس‌های من
        elif data == "services":

            await query.edit_message_text(
                "📦 سرویس‌های من\n\n"
                "در حال حاضر سرویس فعالی ثبت نشده است.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        "🔙 بازگشت",
                        callback_data="home"
                    )]
                ])
            )

        # پشتیبانی
        elif data == "support":

            await query.edit_message_text(
                "💬 پشتیبانی HanzuVPN\n\n"
                "برای پشتیبانی با مدیریت در ارتباط باشید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        "🔙 بازگشت",
                        callback_data="home"
                    )]
                ])
            )

        # تایید توسط ادمین
        elif data.startswith("approve_"):

            if query.from_user.id != ADMIN_ID:
                await query.answer(
                    "⛔ شما دسترسی ندارید.",
                    show_alert=True
                )
                return

            user_id = int(data.split("_")[1])

            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "✅ پرداخت شما تأیید شد.\n\n"
                    "🌐 HanzuVPN\n\n"
                    "سرویس شما با موفقیت تأیید شد.\n\n"
                    "📦 کانفیگ در مرحله بعد برای شما ارسال می‌شود."
                )
            )

            await query.edit_message_caption(
                caption=query.message.caption +
                "\n\n✅ پرداخت توسط مدیریت تأیید شد."
            )

        # رد توسط ادمین
        elif data.startswith("reject_"):

            if query.from_user.id != ADMIN_ID:
                await query.answer(
                    "⛔ شما دسترسی ندارید.",
                    show_alert=True
                )
                return

            user_id = int(data.split("_")[1])

            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "❌ پرداخت شما تأیید نشد.\n\n"
                    "لطفاً رسید پرداخت را بررسی کرده و "
                    "مجدداً ارسال کنید."
                )
            )

            await query.edit_message_caption(
                caption=query.message.caption +
                "\n\n❌ پرداخت توسط مدیریت رد شد."
            )

    except Exception as e:

        print("ERROR:", repr(e))

        try:
            await query.answer(
                "❌ خطایی رخ داد.",
                show_alert=True
            )
        except Exception:
            pass


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.user_data.get("waiting_custom"):
        return

    try:

        volume = int(update.message.text)

    except ValueError:

        await update.message.reply_text(
            "❌ فقط عدد وارد کنید.\n\n"
            "مثال: 25"
        )
        return

    if volume <= 0:

        await update.message.reply_text(
            "❌ حجم باید بیشتر از صفر باشد."
        )
        return

    price = volume * 3500

    context.user_data["waiting_custom"] = False
    context.user_data["volume"] = f"{volume} گیگ"
    context.user_data["price"] = price

    keyboard = [
        [InlineKeyboardButton(
            "💳 پرداخت کردم",
            callback_data=f"paid_{volume}_{price}"
        )],

        [InlineKeyboardButton(
            "🔙 بازگشت",
            callback_data="buy"
        )]
    ]

    await update.message.reply_text(
        f"🌐 سرویس: {volume} گیگ\n"
        f"⏳ مدت: 30 روز\n"
        f"💰 مبلغ: {price:,} تومان\n\n"
        f"💳 شماره کارت:\n"
        f"{CARD_NUMBER}\n\n"
        "بعد از پرداخت روی دکمه زیر بزنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.user_data.get("waiting_receipt"):
        return

    photo = update.message.photo[-1]

    user = update.effective_user

    volume = context.user_data.get(
        "volume",
        "نامشخص"
    )

    price = context.user_data.get(
        "price",
        0
    )

    username = user.username if user.username else "ندارد"

    caption = (
        "🔔 رسید پرداخت جدید\n\n"
        f"👤 نام: {user.full_name}\n"
        f"👤 Username: @{username}\n"
        f"🆔 User ID: {user.id}\n\n"
        f"📦 سرویس: {volume}\n"
        f"💰 مبلغ: {price:,} تومان"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ تأیید پرداخت",
                callback_data=f"approve_{user.id}"
            ),

            InlineKeyboardButton(
                "❌ رد پرداخت",
                callback_data=f"reject_{user.id}"
            )
        ]
    ]

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo.file_id,
        caption=caption,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    context.user_data["waiting_receipt"] = False

    await update.message.reply_text(
        "✅ رسید دریافت شد.\n\n"
        "⏳ رسید شما برای مدیریت ارسال شد.\n"
        "پس از بررسی، نتیجه برای شما ارسال می‌شود."
    )


def main():

    if not BOT_TOKEN:
        raise ValueError(
            "BOT_TOKEN تنظیم نشده است."
        )

    if not ADMIN_ID:
        raise ValueError(
            "ADMIN_ID تنظیم نشده است."
        )

    if not CARD_NUMBER:
        raise ValueError(
            "CARD_NUMBER تنظیم نشده است."
        )

    app = Application.builder().token(
        BOT_TOKEN
    ).build()

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            buttons
        )
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

    print(
        "HanzuVPN Bot is running..."
    )

    app.run_polling()


if __name__ == "__main__":
    main()
