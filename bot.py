import os
import sqlite3

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

DB_PATH = os.getenv("DB_PATH", "hanzuvpn.db")


PLANS = {
    "10": 35000,
    "20": 70000,
    "30": 105000,
    "40": 140000,
    "50": 175000,
}


# =========================
# DATABASE
# =========================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            volume TEXT NOT NULL,
            link TEXT NOT NULL,
            used INTEGER DEFAULT 0
        )
        """
    )
    conn.commit()
    return conn


def add_subscription(volume, link):

    conn = get_db()

    conn.execute(
        "INSERT INTO subscriptions (volume, link, used) VALUES (?, ?, 0)",
        (volume, link)
    )

    conn.commit()
    conn.close()


def get_available_subscription(volume):

    conn = get_db()

    row = conn.execute(
        """
        SELECT id, link
        FROM subscriptions
        WHERE volume = ? AND used = 0
        ORDER BY id ASC
        LIMIT 1
        """,
        (volume,)
    ).fetchone()

    conn.close()

    return row


def use_subscription(subscription_id):

    conn = get_db()

    conn.execute(
        """
        UPDATE subscriptions
        SET used = 1
        WHERE id = ?
        """,
        (subscription_id,)
    )

    conn.commit()
    conn.close()


def get_stock():

    conn = get_db()

    rows = conn.execute(
        """
        SELECT volume, COUNT(*)
        FROM subscriptions
        WHERE used = 0
        GROUP BY volume
        """
    ).fetchall()

    conn.close()

    stock = {}

    for volume, count in rows:
        stock[volume] = count

    return stock


def delete_subscription(subscription_id):

    conn = get_db()

    conn.execute(
        "DELETE FROM subscriptions WHERE id = ?",
        (subscription_id,)
    )

    conn.commit()
    conn.close()


def get_subscription_list():

    conn = get_db()

    rows = conn.execute(
        """
        SELECT id, volume, link
        FROM subscriptions
        WHERE used = 0
        ORDER BY id ASC
        """
    ).fetchall()

    conn.close()

    return rows


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        [
            InlineKeyboardButton(
                "🛒 خرید سرویس",
                callback_data="buy"
            )
        ],

        [
            InlineKeyboardButton(
                "📦 سرویس‌های من",
                callback_data="services"
            )
        ],

        [
            InlineKeyboardButton(
                "💬 پشتیبانی",
                callback_data="support"
            )
        ]
    ]

    # پنل مدیریت فقط برای ادمین
    if update.effective_user.id == ADMIN_ID:

        keyboard.append([
            InlineKeyboardButton(
                "⚙️ پنل مدیریت",
                callback_data="admin"
            )
        ])

    await update.message.reply_text(
        "🌐 HanzuVPN\n\n"
        "به ربات فروش HanzuVPN خوش آمدید.\n\n"
        "یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================
# BUTTONS
# =========================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    try:

        await query.answer()

        data = query.data

        # =========================
        # HOME
        # =========================

        if data == "home":

            keyboard = [
                [
                    InlineKeyboardButton(
                        "🛒 خرید سرویس",
                        callback_data="buy"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "📦 سرویس‌های من",
                        callback_data="services"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "💬 پشتیبانی",
                        callback_data="support"
                    )
                ]
            ]

            if query.from_user.id == ADMIN_ID:

                keyboard.append([
                    InlineKeyboardButton(
                        "⚙️ پنل مدیریت",
                        callback_data="admin"
                    )
                ])

            await query.edit_message_text(
                "🌐 HanzuVPN\n\n"
                "یکی از گزینه‌های زیر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        # =========================
        # BUY
        # =========================

        elif data == "buy":

            keyboard = [

                [
                    InlineKeyboardButton(
                        "10 گیگ | 35,000 تومان",
                        callback_data="plan_10"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "20 گیگ | 70,000 تومان",
                        callback_data="plan_20"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "30 گیگ | 105,000 تومان",
                        callback_data="plan_30"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "40 گیگ | 140,000 تومان",
                        callback_data="plan_40"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "50 گیگ | 175,000 تومان",
                        callback_data="plan_50"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "🔹 حجم دلخواه",
                        callback_data="custom"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "🔙 بازگشت",
                        callback_data="home"
                    )
                ]
            ]

            await query.edit_message_text(
                "🛒 سرویس‌های HanzuVPN\n\n"
                "⏳ مدت همه سرویس‌ها: 30 روز\n\n"
                "حجم موردنظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        # =========================
        # PLAN
        # =========================

        elif data.startswith("plan_"):

            volume = data.replace("plan_", "")

            if volume not in PLANS:

                await query.edit_message_text(
                    "❌ سرویس پیدا نشد."
                )
                return

            price = PLANS[volume]

            keyboard = [
                [
                    InlineKeyboardButton(
                        "💳 پرداخت کردم",
                        callback_data=f"paid_{volume}_{price}"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "🔙 بازگشت",
                        callback_data="buy"
                    )
                ]
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

        # =========================
        # PAYMENT
        # =========================

        elif data.startswith("paid_"):

            parts = data.split("_")

            if len(parts) != 3:

                await query.edit_message_text(
                    "❌ اطلاعات پرداخت نامعتبر است."
                )
                return

            volume = parts[1]
            price = int(parts[2])

            context.user_data["volume"] = volume
            context.user_data["price"] = price
            context.user_data["waiting_receipt"] = True

            await query.edit_message_text(
                "✅ درخواست پرداخت ثبت شد.\n\n"
                "📸 حالا عکس رسید پرداخت را همینجا ارسال کنید."
            )

        # =========================
        # CUSTOM
        # =========================

        elif data == "custom":

            context.user_data["waiting_custom"] = True

            await query.edit_message_text(
                "🔹 حجم دلخواه\n\n"
                "حجم موردنظر را به صورت عدد ارسال کنید.\n\n"
                "مثال:\n"
                "25\n\n"
                "💰 قیمت هر گیگ: 3,500 تومان"
            )

        # =========================
        # SERVICES
        # =========================

        elif data == "services":

            await query.edit_message_text(
                "📦 سرویس‌های من\n\n"
                "فعلاً سرویس فعالی ثبت نشده است.",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "🔙 بازگشت",
                            callback_data="home"
                        )
                    ]
                ])
            )

        # =========================
        # SUPPORT
        # =========================

        elif data == "support":

            await query.edit_message_text(
                "💬 پشتیبانی HanzuVPN\n\n"
                "برای پشتیبانی با مدیریت در ارتباط باشید.",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "🔙 بازگشت",
                            callback_data="home"
                        )
                    ]
                ])
            )

        # =========================
        # ADMIN PANEL
        # =========================

        elif data == "admin":

            if query.from_user.id != ADMIN_ID:
                await query.answer(
                    "⛔ دسترسی ندارید.",
                    show_alert=True
                )
                return

            keyboard = [

                [
                    InlineKeyboardButton(
                        "➕ افزودن لینک ساب",
                        callback_data="admin_add"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "📦 موجودی",
                        callback_data="admin_stock"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "🗑 حذف لینک",
                        callback_data="admin_delete"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "🔙 بازگشت",
                        callback_data="home"
                    )
                ]
            ]

            await query.edit_message_text(
                "⚙️ پنل مدیریت HanzuVPN\n\n"
                "عملیات موردنظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        # =========================
        # ADD LINK
        # =========================

        elif data == "admin_add":

            if query.from_user.id != ADMIN_ID:
                return

            keyboard = [

                [
                    InlineKeyboardButton(
                        "10 گیگ",
                        callback_data="add_10"
                    ),

                    InlineKeyboardButton(
                        "20 گیگ",
                        callback_data="add_20"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "30 گیگ",
                        callback_data="add_30"
                    ),

                    InlineKeyboardButton(
                        "40 گیگ",
                        callback_data="add_40"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "50 گیگ",
                        callback_data="add_50"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "🔙 بازگشت",
                        callback_data="admin"
                    )
                ]
            ]

            await query.edit_message_text(
                "➕ افزودن لینک ساب\n\n"
                "حجم لینک را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        # =========================
        # SELECT VOLUME FOR ADD
        # =========================

        elif data.startswith("add_"):

            if query.from_user.id != ADMIN_ID:
                return

            volume = data.replace("add_", "")

            context.user_data["adding_subscription"] = volume

            await query.edit_message_text(
                f"➕ افزودن لینک\n\n"
                f"📦 حجم: {volume} گیگ\n\n"
                "حالا لینک Subscription را همینجا ارسال کن.\n\n"
                "مثال:\n"
                "https://example.com/sub/..."
            )

        # =========================
        # STOCK
        # =========================

        elif data == "admin_stock":

            if query.from_user.id != ADMIN_ID:
                return

            stock = get_stock()

            text = "📦 موجودی لینک‌ها\n\n"

            for volume in ["10", "20", "30", "40", "50"]:

                count = stock.get(volume, 0)

                text += f"🔹 {volume} گیگ: {count} لینک\n"

            keyboard = [
                [
                    InlineKeyboardButton(
                        "🔙 بازگشت",
                        callback_data="admin"
                    )
                ]
            ]

            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        # =========================
        # DELETE MENU
        # =========================

        elif data == "admin_delete":

            if query.from_user.id != ADMIN_ID:
                return

            rows = get_subscription_list()

            if not rows:

                await query.edit_message_text(
                    "📦 هیچ لینک فعالی برای حذف وجود ندارد.",
                    reply_markup=InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton(
                                "🔙 بازگشت",
                                callback_data="admin"
                            )
                        ]
                    ])
                )

                return

            keyboard = []

            for row_id, volume, link in rows:

                keyboard.append([
                    InlineKeyboardButton(
                        f"🗑 {volume} گیگ | ID {row_id}",
                        callback_data=f"del_{row_id}"
                    )
                ])

            keyboard.append([
                InlineKeyboardButton(
                    "🔙 بازگشت",
                    callback_data="admin"
                )
            ])

            await query.edit_message_text(
                "🗑 حذف لینک\n\n"
                "لینک موردنظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        # =========================
        # DELETE
        # =========================

        elif data.startswith("del_"):

            if query.from_user.id != ADMIN_ID:
                return

            subscription_id = int(
                data.replace("del_", "")
            )

            delete_subscription(subscription_id)

            await query.edit_message_text(
                "✅ لینک با موفقیت حذف شد.",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "⚙️ پنل مدیریت",
                            callback_data="admin"
                        )
                    ]
                ])
            )

        # =========================
        # APPROVE PAYMENT
        # =========================

        elif data.startswith("approve_"):

            if query.from_user.id != ADMIN_ID:

                await query.answer(
                    "⛔ دسترسی ندارید.",
                    show_alert=True
                )

                return

            parts = data.split("_")

            if len(parts) != 3:
                return

            user_id = int(parts[1])
            volume = parts[2]

            subscription = get_available_subscription(volume)

            if not subscription:

                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        "✅ پرداخت شما تأیید شد.\n\n"
                        "⚠️ اما در حال حاضر لینک Subscription "
                        "مربوط به حجم خریداری‌شده موجود نیست.\n\n"
                        "لطفاً با پشتیبانی در ارتباط باشید."
                    )
                )

                await query.edit_message_caption(
                    caption=query.message.caption +
                    "\n\n⚠️ پرداخت تأیید شد ولی لینک موجود نبود."
                )

                return

            subscription_id = subscription[0]
            subscription_link = subscription[1]

            use_subscription(subscription_id)

            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "✅ پرداخت شما تأیید شد.\n\n"
                    "🌐 HanzuVPN\n\n"
                    f"📦 حجم: {volume} گیگ\n"
                    "⏳ مدت: 30 روز\n\n"
                    "🔗 لینک Subscription:\n\n"
                    f"{subscription_link}\n\n"
                    "📌 لینک را در برنامه VPN خود وارد کنید."
                )
            )

            await query.edit_message_caption(
                caption=query.message.caption +
                "\n\n✅ پرداخت تأیید شد و لینک ارسال گردید."
            )

        # =========================
        # REJECT PAYMENT
        # =========================

        elif data.startswith("reject_"):

            if query.from_user.id != ADMIN_ID:
                return

            parts = data.split("_")

            user_id = int(parts[1])

            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "❌ پرداخت شما تأیید نشد.\n\n"
                    "لطفاً رسید پرداخت را بررسی کرده و "
                    "در صورت نیاز مجدداً ارسال کنید."
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


# =========================
# TEXT HANDLER
# =========================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # افزودن لینک توسط ادمین
    if context.user_data.get("adding_subscription"):

        if update.effective_user.id != ADMIN_ID:
            return

        volume = context.user_data["adding_subscription"]

        link = update.message.text.strip()

        if not link.startswith("http://") and not link.startswith("https://"):

            await update.message.reply_text(
                "❌ لینک معتبر نیست.\n\n"
                "لینک باید با http:// یا https:// شروع شود."
            )

            return

        add_subscription(volume, link)

        context.user_data["adding_subscription"] = None

        await update.message.reply_text(
            f"✅ لینک با موفقیت اضافه شد.\n\n"
            f"📦 حجم: {volume} گیگ\n"
            f"🔗 لینک ذخیره شد.\n\n"
            "برای افزودن لینک دیگر دوباره وارد پنل مدیریت شوید."
        )

        return

    # حجم دلخواه مشتری
    if context.user_data.get("waiting_custom"):

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
        context.user_data["volume"] = str(volume)
        context.user_data["price"] = price

        keyboard = [
            [
                InlineKeyboardButton(
                    "💳 پرداخت کردم",
                    callback_data=f"paid_{volume}_{price}"
                )
            ],

            [
                InlineKeyboardButton(
                    "🔙 بازگشت",
                    callback_data="buy"
                )
            ]
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


# =========================
# PHOTO / RECEIPT
# =========================

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
        f"📦 سرویس: {volume} گیگ\n"
        f"💰 مبلغ: {price:,} تومان"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ تأیید پرداخت",
                callback_data=f"approve_{user.id}_{volume}"
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
        "⏳ رسید برای مدیریت ارسال شد.\n"
        "پس از بررسی، نتیجه برای شما ارسال می‌شود."
    )


# =========================
# MAIN
# =========================

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

    # ساخت دیتابیس
    get_db().close()

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

    print("HanzuVPN Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
