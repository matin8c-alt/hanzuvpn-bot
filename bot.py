import os
import sqlite3
import asyncio
from datetime import datetime, timedelta

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================================================
# تنظیمات
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CARD_NUMBER = os.getenv("CARD_NUMBER", "")
DB_PATH = os.getenv("DB_PATH", "hanzuvpn.db")

PRICE_PER_GB = 3500

PLANS = {
    "10": 35000,
    "20": 70000,
    "30": 105000,
    "40": 140000,
    "50": 175000,
}

SERVICE_DAYS = 30
TRIAL_MB = 100
TRIAL_DAYS = 1


# =========================================================
# ابزارهای عمومی
# =========================================================

def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_user(user):
    if not user:
        return

    conn = get_db()

    conn.execute("""
        INSERT OR IGNORE INTO users
        (
            user_id,
            username,
            first_name,
            created_at
        )
        VALUES (?, ?, ?, ?)
    """, (
        user.id,
        user.username or "",
        user.first_name or "",
        now_text(),
    ))

    conn.execute("""
        UPDATE users
        SET username = ?, first_name = ?
        WHERE user_id = ?
    """, (
        user.username or "",
        user.first_name or "",
        user.id,
    ))

    conn.commit()
    conn.close()


# =========================================================
# دیتابیس
# =========================================================

def init_db():

    conn = get_db()

    # لینک‌های فروش
    conn.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            volume TEXT NOT NULL,
            link TEXT NOT NULL,
            used INTEGER DEFAULT 0
        )
    """)

    # سفارش‌ها
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            first_name TEXT,
            volume TEXT NOT NULL,
            price INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            subscription_id INTEGER,
            created_at TEXT NOT NULL,
            approved_at TEXT,
            expires_at TEXT
        )
    """)

    # کاربران
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            created_at TEXT NOT NULL,
            referred_by INTEGER,
            referral_rewarded INTEGER DEFAULT 0
        )
    """)

    # تست رایگان
    conn.execute("""
        CREATE TABLE IF NOT EXISTS free_trials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link TEXT NOT NULL,
            used INTEGER DEFAULT 0
        )
    """)

    # کسانی که تست گرفته‌اند
    conn.execute("""
        CREATE TABLE IF NOT EXISTS free_trial_users (
            user_id INTEGER PRIMARY KEY,
            trial_id INTEGER,
            claimed_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )
    """)

    # کوپن‌ها
    conn.execute("""
        CREATE TABLE IF NOT EXISTS coupons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            percent INTEGER NOT NULL,
            max_uses INTEGER DEFAULT 0,
            used_count INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)

    # استفاده از کوپن
    conn.execute("""
        CREATE TABLE IF NOT EXISTS coupon_uses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            coupon_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            order_id INTEGER,
            created_at TEXT NOT NULL,
            UNIQUE(coupon_id, user_id)
        )
    """)

    # تیکت‌ها
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT,
            status TEXT DEFAULT 'open',
            created_at TEXT NOT NULL,
            closed_at TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS ticket_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            message TEXT,
            created_at TEXT NOT NULL
        )
    """)

    # یادآوری‌ها
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            reminder_type TEXT NOT NULL,
            sent_at TEXT NOT NULL,
            UNIQUE(order_id, reminder_type)
        )
    """)

    conn.commit()

    # سازگاری با دیتابیس قبلی
    try:
        conn.execute(
            "ALTER TABLE orders ADD COLUMN expires_at TEXT"
        )
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute(
            "ALTER TABLE users ADD COLUMN referred_by INTEGER"
        )
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute(
            "ALTER TABLE users ADD COLUMN referral_rewarded INTEGER DEFAULT 0"
        )
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


# =========================================================
# منوی اصلی
# =========================================================

def home_keyboard(user_id):

    keyboard = [
        [
            InlineKeyboardButton(
                "🛒 خرید سرویس",
                callback_data="buy"
            )
        ],
        [
            InlineKeyboardButton(
                "🎁 تست رایگان",
                callback_data="trial"
            )
        ],
        [
            InlineKeyboardButton(
                "📦 سرویس‌های من",
                callback_data="my_services"
            ),
            InlineKeyboardButton(
                "🔄 تمدید",
                callback_data="renew"
            ),
        ],
        [
            InlineKeyboardButton(
                "🎟 کد تخفیف",
                callback_data="coupon"
            ),
            InlineKeyboardButton(
                "👥 دعوت دوستان",
                callback_data="referral"
            ),
        ],
        [
            InlineKeyboardButton(
                "🎫 پشتیبانی",
                callback_data="support"
            ),
        ],
    ]

    if user_id == ADMIN_ID:
        keyboard.append([
            InlineKeyboardButton(
                "⚙️ پنل مدیریت",
                callback_data="admin"
            )
        ])

    return InlineKeyboardMarkup(keyboard)


async def show_home(query, user_id):

    await query.edit_message_text(
        "🌐 HanzuVPN\n\n"
        "به ربات HanzuVPN خوش آمدید ❤️\n\n"
        "از منوی زیر انتخاب کنید:",
        reply_markup=home_keyboard(user_id)
    )


async def send_home(message, user_id):

    await message.reply_text(
        "🌐 HanzuVPN\n\n"
        "به ربات HanzuVPN خوش آمدید ❤️\n\n"
        "از منوی زیر انتخاب کنید:",
        reply_markup=home_keyboard(user_id)
    )


# =========================================================
# دستورات
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    ensure_user(user)

    # سیستم دعوت
    if context.args:

        try:
            referrer_id = int(context.args[0])

            if referrer_id != user.id:

                conn = get_db()

                existing = conn.execute("""
                    SELECT referred_by
                    FROM users
                    WHERE user_id = ?
                """, (user.id,)).fetchone()

                if existing and existing["referred_by"] is None:

                    conn.execute("""
                        UPDATE users
                        SET referred_by = ?
                        WHERE user_id = ?
                    """, (
                        referrer_id,
                        user.id,
                    ))

                    conn.commit()

                conn.close()

        except Exception:
            pass

    await send_home(
        update.message,
        user.id
    )


async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    ensure_user(update.effective_user)

    await send_buy_message(
        update.message
    )


async def services_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    ensure_user(update.effective_user)

    await send_services_message(
        update.message,
        update.effective_user.id
    )


async def trial_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    ensure_user(update.effective_user)

    result = claim_trial(
        update.effective_user
    )

    if result["status"] == "already":

        await update.message.reply_text(
            "⚠️ شما قبلاً تست رایگان خود را دریافت کرده‌اید.\n\n"
            "هر کاربر فقط یک‌بار می‌تواند از تست رایگان استفاده کند."
        )

        return

    if result["status"] == "empty":

        await update.message.reply_text(
            "😔 در حال حاضر تست رایگان موجود نیست.\n\n"
            "لطفاً بعداً دوباره امتحان کنید."
        )

        return

    await update.message.reply_text(
        "🎁 تست رایگان HanzuVPN\n\n"
        "📦 حجم: 100 مگابایت\n"
        "⏳ مدت: 1 روز\n\n"
        "🔗 لینک Subscription:\n\n"
        f"{result['link']}\n\n"
        "📌 لینک را در برنامه VPN خود وارد کنید."
    )


async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    ensure_user(update.effective_user)

    await update.message.reply_text(
        "🎫 پشتیبانی HanzuVPN\n\n"
        "برای ارتباط با پشتیبانی روی گزینه زیر بزنید.",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🎫 ایجاد تیکت",
                    callback_data="new_ticket"
                )
            ],
            [
                InlineKeyboardButton(
                    "🔙 منوی اصلی",
                    callback_data="home"
                )
            ]
        ])
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "📚 راهنمای HanzuVPN\n\n"
        "/start - منوی اصلی\n"
        "/buy - خرید سرویس\n"
        "/services - سرویس‌های من\n"
        "/trial - تست رایگان\n"
        "/support - پشتیبانی\n"
        "/help - راهنما\n\n"
        "تمام امکانات از طریق منوی اصلی نیز قابل استفاده هستند."
    )


# =========================================================
# دستورات منوی تلگرام
# =========================================================

async def set_bot_commands(application):

    commands = [
        BotCommand("start", "منوی اصلی"),
        BotCommand("buy", "خرید سرویس"),
        BotCommand("services", "سرویس‌های من"),
        BotCommand("trial", "تست رایگان"),
        BotCommand("support", "پشتیبانی"),
        BotCommand("help", "راهنما"),
    ]

    await application.bot.set_my_commands(commands)


# =========================================================
# خرید
# =========================================================

def buy_keyboard():

    return InlineKeyboardMarkup([
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
                "✏️ حجم دلخواه",
                callback_data="custom"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="home"
            )
        ]
    ])


async def send_buy_message(message):

    await message.reply_text(
        "🛒 انتخاب سرویس\n\n"
        "⏳ مدت تمام سرویس‌ها: 30 روز\n\n"
        "حجم موردنظر خود را انتخاب کنید:",
        reply_markup=buy_keyboard()
    )


async def show_buy_menu(query):

    await query.edit_message_text(
        "🛒 انتخاب سرویس\n\n"
        "⏳ مدت تمام سرویس‌ها: 30 روز\n\n"
        "حجم موردنظر خود را انتخاب کنید:",
        reply_markup=buy_keyboard()
    )


# =========================================================
# پرداخت
# =========================================================

async def show_payment(
    query,
    volume,
    price,
    original_price=None,
    coupon_code=None
):

    if original_price is None:
        original_price = price

    caption = (
        "💳 اطلاعات پرداخت\n\n"
        f"📦 حجم: {volume} گیگ\n"
        f"💰 مبلغ: {price:,} تومان\n"
        "⏳ مدت: 30 روز\n"
    )

    if original_price != price:
        caption += (
            f"\n🏷 مبلغ اصلی: {original_price:,} تومان\n"
            f"🎟 کد تخفیف: {coupon_code}\n"
        )

    caption += (
        "\n💳 شماره کارت:\n"
        f"`{CARD_NUMBER}`\n\n"
        "بعد از انتقال مبلغ، روی «پرداخت کردم» بزنید "
        "و سپس تصویر رسید را ارسال کنید."
    )

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
        caption,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================================================
# لینک‌های سرویس
# =========================================================

def add_subscription(volume, link):

    conn = get_db()

    conn.execute("""
        INSERT INTO subscriptions
        (volume, link, used)
        VALUES (?, ?, 0)
    """, (
        str(volume),
        link,
    ))

    conn.commit()
    conn.close()


def get_subscription_list():

    conn = get_db()

    rows = conn.execute("""
        SELECT id, volume, link
        FROM subscriptions
        WHERE used = 0
        ORDER BY CAST(volume AS INTEGER), id
    """).fetchall()

    conn.close()

    return rows


def delete_subscription(subscription_id):

    conn = get_db()

    conn.execute("""
        DELETE FROM subscriptions
        WHERE id = ?
        AND used = 0
    """, (subscription_id,))

    conn.commit()
    conn.close()


def get_stock():

    conn = get_db()

    rows = conn.execute("""
        SELECT volume, COUNT(*) AS count
        FROM subscriptions
        WHERE used = 0
        GROUP BY volume
        ORDER BY CAST(volume AS INTEGER)
    """).fetchall()

    conn.close()

    return {
        row["volume"]: row["count"]
        for row in rows
    }


# =========================================================
# تست رایگان
# =========================================================

def add_free_trial(link):

    conn = get_db()

    conn.execute("""
        INSERT INTO free_trials
        (link, used)
        VALUES (?, 0)
    """, (link,))

    conn.commit()
    conn.close()


def get_free_trial_stock():

    conn = get_db()

    count = conn.execute("""
        SELECT COUNT(*)
        FROM free_trials
        WHERE used = 0
    """).fetchone()[0]

    conn.close()

    return count


def get_free_trial_list():

    conn = get_db()

    rows = conn.execute("""
        SELECT id, link
        FROM free_trials
        WHERE used = 0
        ORDER BY id
    """).fetchall()

    conn.close()

    return rows


def delete_free_trial(trial_id):

    conn = get_db()

    conn.execute("""
        DELETE FROM free_trials
        WHERE id = ?
        AND used = 0
    """, (trial_id,))

    conn.commit()
    conn.close()


def claim_trial(user):

    conn = get_db()

    try:

        conn.execute("BEGIN IMMEDIATE")

        already = conn.execute("""
            SELECT *
            FROM free_trial_users
            WHERE user_id = ?
        """, (user.id,)).fetchone()

        if already:

            conn.rollback()

            return {
                "status": "already"
            }

        trial = conn.execute("""
            SELECT id, link
            FROM free_trials
            WHERE used = 0
            ORDER BY id
            LIMIT 1
        """).fetchone()

        if not trial:

            conn.rollback()

            return {
                "status": "empty"
            }

        claimed_at = datetime.now()
        expires_at = claimed_at + timedelta(
            days=TRIAL_DAYS
        )

        conn.execute("""
            UPDATE free_trials
            SET used = 1
            WHERE id = ?
            AND used = 0
        """, (trial["id"],))

        conn.execute("""
            INSERT INTO free_trial_users
            (
                user_id,
                trial_id,
                claimed_at,
                expires_at
            )
            VALUES (?, ?, ?, ?)
        """, (
            user.id,
            trial["id"],
            claimed_at.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            expires_at.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        ))

        conn.commit()

        return {
            "status": "success",
            "link": trial["link"]
        }

    except Exception:

        conn.rollback()
        raise

    finally:

        conn.close()


# =========================================================
# سفارش
# =========================================================

def create_order(user, volume, price):

    conn = get_db()

    cursor = conn.execute("""
        INSERT INTO orders
        (
            user_id,
            username,
            first_name,
            volume,
            price,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, 'pending', ?)
    """, (
        user.id,
        user.username or "",
        user.first_name or "",
        str(volume),
        int(price),
        now_text(),
    ))

    order_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return order_id


def get_latest_pending_order(user_id):

    conn = get_db()

    row = conn.execute("""
        SELECT *
        FROM orders
        WHERE user_id = ?
        AND status = 'pending'
        ORDER BY id DESC
        LIMIT 1
    """, (user_id,)).fetchone()

    conn.close()

    return row


# =========================================================
# تأیید سفارش
# =========================================================

def approve_order(order_id):

    conn = get_db()

    try:

        conn.execute("BEGIN IMMEDIATE")

        order = conn.execute("""
            SELECT *
            FROM orders
            WHERE id = ?
        """, (order_id,)).fetchone()

        if not order:

            conn.rollback()

            return {
                "status": "not_found"
            }

        if order["status"] != "pending":

            conn.rollback()

            return {
                "status": "already_processed",
                "order": order
            }

        subscription = conn.execute("""
            SELECT id, link
            FROM subscriptions
            WHERE volume = ?
            AND used = 0
            ORDER BY id
            LIMIT 1
        """, (order["volume"],)).fetchone()

        if not subscription:

            conn.rollback()

            return {
                "status": "no_stock",
                "order": order
            }

        approved_at = datetime.now()

        expires_at = approved_at + timedelta(
            days=SERVICE_DAYS
        )

        conn.execute("""
            UPDATE orders
            SET
                status = 'approved',
                subscription_id = ?,
                approved_at = ?,
                expires_at = ?
            WHERE id = ?
            AND status = 'pending'
        """, (
            subscription["id"],
            approved_at.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            expires_at.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            order_id,
        ))

        conn.execute("""
            UPDATE subscriptions
            SET used = 1
            WHERE id = ?
            AND used = 0
        """, (subscription["id"],))

        conn.commit()

        return {
            "status": "approved",
            "order": order,
            "link": subscription["link"],
            "expires_at": expires_at.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        }

    except Exception:

        conn.rollback()
        raise

    finally:

        conn.close()


def reject_order(order_id):

    conn = get_db()

    updated = conn.execute("""
        UPDATE orders
        SET status = 'rejected'
        WHERE id = ?
        AND status = 'pending'
    """, (order_id,))

    conn.commit()

    order = conn.execute("""
        SELECT *
        FROM orders
        WHERE id = ?
    """, (order_id,)).fetchone()

    conn.close()

    return updated.rowcount == 1, order


# =========================================================
# سرویس‌های کاربر
# =========================================================

def get_user_services(user_id):

    conn = get_db()

    rows = conn.execute("""
        SELECT
            o.id,
            o.volume,
            o.price,
            o.approved_at,
            o.expires_at,
            s.link
        FROM orders o
        LEFT JOIN subscriptions s
        ON o.subscription_id = s.id
        WHERE o.user_id = ?
        AND o.status = 'approved'
        ORDER BY o.id DESC
    """, (user_id,)).fetchall()

    conn.close()

    return rows


async def send_services_message(message, user_id):

    rows = get_user_services(user_id)

    if not rows:

        text = (
            "📦 سرویس‌های شما\n\n"
            "هنوز سرویس فعالی ندارید."
        )

    else:

        text = "📦 سرویس‌های شما\n\n"

        for row in rows:

            text += (
                f"🧾 سفارش #{row['id']}\n"
                f"📦 حجم: {row['volume']} گیگ\n"
                f"⏳ اعتبار تا: "
                f"{row['expires_at'] or '30 روز'}\n\n"
                f"🔗 لینک:\n"
                f"{row['link']}\n\n"
                "━━━━━━━━━━━━\n\n"
            )

    await message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔄 تمدید",
                    callback_data="renew"
                )
            ],
            [
                InlineKeyboardButton(
                    "🔙 منوی اصلی",
                    callback_data="home"
                )
            ]
        ])
    )


# =========================================================
# تمدید
# =========================================================

async def show_renew(query):

    rows = get_user_services(
        query.from_user.id
    )

    if not rows:

        await query.edit_message_text(
            "🔄 تمدید سرویس\n\n"
            "شما سرویس فعالی ندارید.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🛒 خرید سرویس",
                        callback_data="buy"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔙 بازگشت",
                        callback_data="home"
                    )
                ]
            ])
        )

        return

    keyboard = []

    for row in rows[:10]:

        keyboard.append([
            InlineKeyboardButton(
                f"🔄 تمدید #{row['id']} | {row['volume']} گیگ",
                callback_data=f"renew_{row['id']}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "🔙 بازگشت",
            callback_data="home"
        )
    ])

    await query.edit_message_text(
        "🔄 تمدید سرویس\n\n"
        "سرویسی که می‌خواهید تمدید کنید را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================================================
# کوپن
# =========================================================

def create_coupon(code, percent, max_uses):

    conn = get_db()

    try:

        conn.execute("""
            INSERT INTO coupons
            (
                code,
                percent,
                max_uses,
                created_at
            )
            VALUES (?, ?, ?, ?)
        """, (
            code.upper(),
            percent,
            max_uses,
            now_text()
        ))

        conn.commit()

        return True

    except sqlite3.IntegrityError:

        return False

    finally:

        conn.close()


def get_coupon(code):

    conn = get_db()

    row = conn.execute("""
        SELECT *
        FROM coupons
        WHERE code = ?
        AND active = 1
    """, (code.upper(),)).fetchone()

    conn.close()

    return row


def user_used_coupon(coupon_id, user_id):

    conn = get_db()

    row = conn.execute("""
        SELECT id
        FROM coupon_uses
        WHERE coupon_id = ?
        AND user_id = ?
    """, (
        coupon_id,
        user_id
    )).fetchone()

    conn.close()

    return row is not None


def apply_coupon(code, user_id, price):

    coupon = get_coupon(code)

    if not coupon:

        return {
            "status": "invalid"
        }

    if user_used_coupon(
        coupon["id"],
        user_id
    ):

        return {
            "status": "used"
        }

    if (
        coupon["max_uses"] > 0
        and coupon["used_count"] >= coupon["max_uses"]
    ):

        return {
            "status": "full"
        }

    new_price = int(
        price * (100 - coupon["percent"]) / 100
    )

    return {
        "status": "success",
        "coupon": coupon,
        "price": new_price
    }


def record_coupon_use(
    coupon_id,
    user_id,
    order_id
):

    conn = get_db()

    conn.execute("""
        INSERT OR IGNORE INTO coupon_uses
        (
            coupon_id,
            user_id,
            order_id,
            created_at
        )
        VALUES (?, ?, ?, ?)
    """, (
        coupon_id,
        user_id,
        order_id,
        now_text()
    ))

    conn.execute("""
        UPDATE coupons
        SET used_count = used_count + 1
        WHERE id = ?
    """, (coupon_id,))

    conn.commit()
    conn.close()


# =========================================================
# دعوت دوستان
# =========================================================

def referral_count(user_id):

    conn = get_db()

    count = conn.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE referred_by = ?
    """, (user_id,)).fetchone()[0]

    conn.close()

    return count


def referral_link(bot_username, user_id):

    return (
        f"https://t.me/{bot_username}"
        f"?start={user_id}"
    )


# =========================================================
# تیکت
# =========================================================

def create_ticket(user_id, subject="پشتیبانی"):

    conn = get_db()

    cursor = conn.execute("""
        INSERT INTO tickets
        (
            user_id,
            subject,
            status,
            created_at
        )
        VALUES (?, ?, 'open', ?)
    """, (
        user_id,
        subject,
        now_text()
    ))

    ticket_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return ticket_id


def get_open_ticket(user_id):

    conn = get_db()

    row = conn.execute("""
        SELECT *
        FROM tickets
        WHERE user_id = ?
        AND status = 'open'
        ORDER BY id DESC
        LIMIT 1
    """, (user_id,)).fetchone()

    conn.close()

    return row


def add_ticket_message(
    ticket_id,
    sender_id,
    message
):

    conn = get_db()

    conn.execute("""
        INSERT INTO ticket_messages
        (
            ticket_id,
            sender_id,
            message,
            created_at
        )
        VALUES (?, ?, ?, ?)
    """, (
        ticket_id,
        sender_id,
        message,
        now_text()
    ))

    conn.commit()
    conn.close()


# =========================================================
# آمار
# =========================================================

def get_stats():

    conn = get_db()

    total_users = conn.execute("""
        SELECT COUNT(*)
        FROM users
    """).fetchone()[0]

    total_orders = conn.execute("""
        SELECT COUNT(*)
        FROM orders
    """).fetchone()[0]

    approved = conn.execute("""
        SELECT COUNT(*)
        FROM orders
        WHERE status = 'approved'
    """).fetchone()[0]

    pending = conn.execute("""
        SELECT COUNT(*)
        FROM orders
        WHERE status = 'pending'
    """).fetchone()[0]

    rejected = conn.execute("""
        SELECT COUNT(*)
        FROM orders
        WHERE status = 'rejected'
    """).fetchone()[0]

    sales = conn.execute("""
        SELECT COALESCE(SUM(price), 0)
        FROM orders
        WHERE status = 'approved'
    """).fetchone()[0]

    trials = conn.execute("""
        SELECT COUNT(*)
        FROM free_trial_users
    """).fetchone()[0]

    referrals = conn.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE referred_by IS NOT NULL
    """).fetchone()[0]

    open_tickets = conn.execute("""
        SELECT COUNT(*)
        FROM tickets
        WHERE status = 'open'
    """).fetchone()[0]

    conn.close()

    return {
        "users": total_users,
        "orders": total_orders,
        "approved": approved,
        "pending": pending,
        "rejected": rejected,
        "sales": sales,
        "trials": trials,
        "referrals": referrals,
        "tickets": open_tickets,
    }


# =========================================================
# پنل مدیریت
# =========================================================

async def show_admin(query):

    keyboard = [
        [
            InlineKeyboardButton(
                "➕ افزودن لینک سرویس",
                callback_data="admin_add"
            )
        ],
        [
            InlineKeyboardButton(
                "🎁 مدیریت تست",
                callback_data="admin_trial"
            )
        ],
        [
            InlineKeyboardButton(
                "📦 موجودی",
                callback_data="admin_stock"
            ),
            InlineKeyboardButton(
                "🗑 حذف لینک",
                callback_data="admin_delete"
            )
        ],
        [
            InlineKeyboardButton(
                "🎟 کوپن‌ها",
                callback_data="admin_coupon"
            )
        ],
        [
            InlineKeyboardButton(
                "📢 پیام همگانی",
                callback_data="admin_broadcast"
            )
        ],
        [
            InlineKeyboardButton(
                "📊 آمار",
                callback_data="admin_stats"
            ),
            InlineKeyboardButton(
                "🧾 سفارش‌ها",
                callback_data="admin_orders"
            )
        ],
        [
            InlineKeyboardButton(
                "🎫 تیکت‌ها",
                callback_data="admin_tickets"
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
        "مدیریت کامل ربات:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_admin_stock(query):

    stock = get_stock()
    trial_stock = get_free_trial_stock()

    text = "📦 موجودی HanzuVPN\n\n"

    if stock:

        for volume, count in stock.items():

            text += (
                f"🔹 {volume} گیگ: "
                f"{count} عدد\n"
            )

    else:

        text += "❌ سرویس فروشی موجود نیست.\n"

    text += (
        "\n🎁 تست رایگان:\n"
        f"🔹 {trial_stock} عدد\n"
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔙 پنل مدیریت",
                    callback_data="admin"
                )
            ]
        ])
    )


async def show_admin_stats(query):

    s = get_stats()

    text = (
        "📊 آمار HanzuVPN\n\n"
        f"👥 کاربران: {s['users']}\n"
        f"🧾 کل سفارش‌ها: {s['orders']}\n"
        f"✅ تأییدشده: {s['approved']}\n"
        f"⏳ در انتظار: {s['pending']}\n"
        f"❌ ردشده: {s['rejected']}\n\n"
        f"💰 فروش: {s['sales']:,} تومان\n"
        f"🎁 تست‌های استفاده‌شده: {s['trials']}\n"
        f"👥 دعوت‌ها: {s['referrals']}\n"
        f"🎫 تیکت‌های باز: {s['tickets']}"
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔙 پنل مدیریت",
                    callback_data="admin"
                )
            ]
        ])
    )


async def show_admin_orders(query):

    conn = get_db()

    rows = conn.execute("""
        SELECT *
        FROM orders
        ORDER BY id DESC
        LIMIT 15
    """).fetchall()

    conn.close()

    if not rows:

        text = "🧾 سفارشی ثبت نشده است."

    else:

        text = "🧾 آخرین سفارش‌ها\n\n"

        for row in rows:

            status = {
                "pending": "⏳ در انتظار",
                "approved": "✅ تأیید",
                "rejected": "❌ رد"
            }.get(
                row["status"],
                row["status"]
            )

            text += (
                f"#{row['id']} | "
                f"{row['first_name'] or '-'}\n"
                f"📦 {row['volume']} گیگ | "
                f"{row['price']:,} تومان\n"
                f"{status}\n"
                f"🕐 {row['created_at']}\n\n"
            )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔙 پنل مدیریت",
                    callback_data="admin"
                )
            ]
        ])
    )


# =========================================================
# مدیریت تست
# =========================================================

async def show_admin_trial(query):

    stock = get_free_trial_stock()

    keyboard = [
        [
            InlineKeyboardButton(
                "➕ افزودن لینک تست",
                callback_data="admin_trial_add"
            )
        ],
        [
            InlineKeyboardButton(
                "🗑 حذف لینک تست",
                callback_data="admin_trial_delete"
            )
        ],
        [
            InlineKeyboardButton(
                "📦 موجودی تست",
                callback_data="admin_trial_stock"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 پنل مدیریت",
                callback_data="admin"
            )
        ]
    ]

    await query.edit_message_text(
        "🎁 مدیریت تست رایگان\n\n"
        "📦 حجم هر تست: 100 مگابایت\n"
        "⏳ مدت هر تست: 1 روز\n"
        f"📊 موجودی فعلی: {stock}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_admin_trial_delete(query):

    rows = get_free_trial_list()

    if not rows:

        await query.edit_message_text(
            "🗑 حذف تست\n\n"
            "❌ لینک تستی برای حذف وجود ندارد.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 مدیریت تست",
                        callback_data="admin_trial"
                    )
                ]
            ])
        )

        return

    keyboard = []

    for row in rows:

        keyboard.append([
            InlineKeyboardButton(
                f"🗑 تست #{row['id']}",
                callback_data=f"trial_delete_{row['id']}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "🔙 مدیریت تست",
            callback_data="admin_trial"
        )
    ])

    await query.edit_message_text(
        "🗑 لینک تست موردنظر را انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================================================
# حذف لینک سرویس
# =========================================================

async def show_delete_menu(query):

    rows = get_subscription_list()

    if not rows:

        await query.edit_message_text(
            "🗑 حذف لینک\n\n"
            "❌ لینک استفاده‌نشده‌ای وجود ندارد.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 پنل مدیریت",
                        callback_data="admin"
                    )
                ]
            ])
        )

        return

    keyboard = []

    for row in rows:

        keyboard.append([
            InlineKeyboardButton(
                f"🗑 #{row['id']} | {row['volume']} گیگ",
                callback_data=f"delete_{row['id']}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "🔙 پنل مدیریت",
            callback_data="admin"
        )
    ])

    await query.edit_message_text(
        "🗑 کدام لینک حذف شود؟",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================================================
# Callback Handler
# =========================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user = query.from_user
    user_id = user.id

    ensure_user(user)

    data = query.data

    # -------------------------
    # خانه
    # -------------------------

    if data == "home":

        await show_home(
            query,
            user_id
        )

        return

    # -------------------------
    # خرید
    # -------------------------

    if data == "buy":

        await show_buy_menu(query)

        return

    # -------------------------
    # پلن
    # -------------------------

    if data.startswith("plan_"):

        volume = data.split("_")[1]

        price = PLANS.get(volume)

        if price:

            await show_payment(
                query,
                volume,
                price
            )

        return

    # -------------------------
    # حجم دلخواه
    # -------------------------

    if data == "custom":

        context.user_data[
            "waiting_custom_volume"
        ] = True

        await query.edit_message_text(
            "✏️ حجم دلخواه\n\n"
            "حجم موردنظر را به گیگ وارد کن.\n\n"
            "مثال:\n"
            "25"
        )

        return

    # -------------------------
    # تست
    # -------------------------

    if data == "trial":

        result = claim_trial(user)

        if result["status"] == "already":

            await query.edit_message_text(
                "⚠️ شما قبلاً تست رایگان خود را دریافت کرده‌اید.\n\n"
                "هر کاربر فقط یک‌بار می‌تواند تست بگیرد.",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "🛒 خرید سرویس",
                            callback_data="buy"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🔙 بازگشت",
                            callback_data="home"
                        )
                    ]
                ])
            )

            return

        if result["status"] == "empty":

            await query.edit_message_text(
                "😔 فعلاً تست رایگان موجود نیست.\n\n"
                "بعداً دوباره امتحان کنید.",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "🔙 بازگشت",
                            callback_data="home"
                        )
                    ]
                ])
            )

            return

        await query.edit_message_text(
            "🎁 تست رایگان HanzuVPN\n\n"
            "📦 حجم: 100 مگابایت\n"
            "⏳ مدت: 1 روز\n\n"
            "🔗 لینک Subscription:\n\n"
            f"{result['link']}\n\n"
            "📌 لینک را در برنامه VPN خود وارد کنید.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🛒 خرید سرویس",
                        callback_data="buy"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔙 منوی اصلی",
                        callback_data="home"
                    )
                ]
            ])
        )

        return

    # -------------------------
    # سرویس‌های من
    # -------------------------

    if data == "my_services":

        rows = get_user_services(user_id)

        if not rows:

            text = (
                "📦 سرویس‌های شما\n\n"
                "هنوز سرویس فعالی ندارید."
            )

        else:

            text = "📦 سرویس‌های شما\n\n"

            for row in rows:

                text += (
                    f"🧾 سفارش #{row['id']}\n"
                    f"📦 {row['volume']} گیگ\n"
                    f"⏳ انقضا: "
                    f"{row['expires_at'] or '-'}\n\n"
                    f"🔗 {row['link']}\n\n"
                    "━━━━━━━━━━━━\n\n"
                )

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔄 تمدید",
                        callback_data="renew"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔙 بازگشت",
                        callback_data="home"
                    )
                ]
            ])
        )

        return

    # -------------------------
    # تمدید
    # -------------------------

    if data == "renew":

        await show_renew(query)

        return

    if data.startswith("renew_"):

        order_id = int(
            data.split("_")[1]
        )

        conn = get_db()

        order = conn.execute("""
            SELECT *
            FROM orders
            WHERE id = ?
            AND user_id = ?
            AND status = 'approved'
        """, (
            order_id,
            user_id
        )).fetchone()

        conn.close()

        if not order:

            await query.answer(
                "سرویس پیدا نشد.",
                show_alert=True
            )

            return

        volume = order["volume"]

        price = int(volume) * PRICE_PER_GB

        context.user_data[
            "renew_order_id"
        ] = order_id

        context.user_data[
            "renew_volume"
        ] = volume

        await query.edit_message_text(
            "🔄 تمدید سرویس\n\n"
            f"📦 حجم: {volume} گیگ\n"
            f"💰 مبلغ تمدید: {price:,} تومان\n"
            "⏳ مدت: 30 روز\n\n"
            "برای پرداخت روی دکمه زیر بزنید.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "💳 پرداخت تمدید",
                        callback_data=f"renewpay_{volume}_{price}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔙 بازگشت",
                        callback_data="renew"
                    )
                ]
            ])
        )

        return

    if data.startswith("renewpay_"):

        parts = data.split("_")

        volume = parts[1]
        price = int(parts[2])

        context.user_data[
            "renew_payment"
        ] = True

        await query.edit_message_text(
            "💳 پرداخت تمدید\n\n"
            f"📦 حجم: {volume} گیگ\n"
            f"💰 مبلغ: {price:,} تومان\n"
            "⏳ مدت: 30 روز\n\n"
            "💳 شماره کارت:\n"
            f"`{CARD_NUMBER}`\n\n"
            "بعد از پرداخت روی دکمه زیر بزنید.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "💳 پرداخت کردم",
                        callback_data=f"renewpaid_{volume}_{price}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔙 بازگشت",
                        callback_data="renew"
                    )
                ]
            ])
        )

        return

    if data.startswith("renewpaid_"):

        parts = data.split("_")

        volume = parts[1]
        price = int(parts[2])

        order_id = create_order(
            user,
            volume,
            price
        )

        context.user_data[
            "last_order_id"
        ] = order_id

        await query.edit_message_text(
            "✅ درخواست تمدید ثبت شد.\n\n"
            f"🧾 سفارش: #{order_id}\n"
            f"📦 حجم: {volume} گیگ\n"
            f"💰 مبلغ: {price:,} تومان\n\n"
            "📸 حالا تصویر رسید را ارسال کنید."
        )

        return

    # -------------------------
    # پشتیبانی
    # -------------------------

    if data == "support":

        await query.edit_message_text(
            "🎫 پشتیبانی HanzuVPN\n\n"
            "برای ارسال پیام به پشتیبانی تیکت ایجاد کنید.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🎫 ایجاد تیکت",
                        callback_data="new_ticket"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔙 بازگشت",
                        callback_data="home"
                    )
                ]
            ])
        )

        return

    if data == "new_ticket":

        ticket_id = create_ticket(
            user_id
        )

        context.user_data[
            "ticket_id"
        ] = ticket_id

        context.user_data[
            "waiting_ticket_message"
        ] = True

        await query.edit_message_text(
            f"🎫 تیکت #{ticket_id}\n\n"
            "پیام خود را ارسال کنید."
        )

        return

    # -------------------------
    # دعوت
    # -------------------------

    if data == "referral":

        try:

            bot = await context.bot.get_me()

            link = referral_link(
                bot.username,
                user_id
            )

            count = referral_count(
                user_id
            )

            await query.edit_message_text(
                "👥 دعوت دوستان\n\n"
                f"👤 تعداد دعوت‌ها: {count}\n\n"
                "لینک اختصاصی شما:\n"
                f"{link}\n\n"
                "لینک را برای دوستانت بفرست.",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "🔙 بازگشت",
                            callback_data="home"
                        )
                    ]
                ])
            )

        except Exception:

            await query.edit_message_text(
                "❌ خطا در ساخت لینک دعوت."
            )

        return

    # -------------------------
    # کوپن
    # -------------------------

    if data == "coupon":

        context.user_data[
            "waiting_coupon"
        ] = True

        await query.edit_message_text(
            "🎟 کد تخفیف\n\n"
            "کد تخفیف خود را ارسال کنید."
        )

        return

    # -------------------------
    # پنل ادمین
    # -------------------------

    if data == "admin":

        if user_id != ADMIN_ID:
            return

        await show_admin(query)

        return

    # -------------------------
    # موجودی
    # -------------------------

    if data == "admin_stock":

        if user_id != ADMIN_ID:
            return

        await show_admin_stock(query)

        return

    # -------------------------
    # آمار
    # -------------------------

    if data == "admin_stats":

        if user_id != ADMIN_ID:
            return

        await show_admin_stats(query)

        return

    # -------------------------
    # سفارش‌ها
    # -------------------------

    if data == "admin_orders":

        if user_id != ADMIN_ID:
            return

        await show_admin_orders(query)

        return

    # -------------------------
    # افزودن لینک
    # -------------------------

    if data == "admin_add":

        if user_id != ADMIN_ID:
            return

        context.user_data[
            "admin_waiting_volume"
        ] = True

        await query.edit_message_text(
            "➕ افزودن لینک سرویس\n\n"
            "حجم لینک را به گیگ وارد کن.\n\n"
            "مثال: 10"
        )

        return

    # -------------------------
    # حذف لینک
    # -------------------------

    if data == "admin_delete":

        if user_id != ADMIN_ID:
            return

        await show_delete_menu(query)

        return

    if data.startswith("delete_"):

        if user_id != ADMIN_ID:
            return

        subscription_id = int(
            data.split("_")[1]
        )

        delete_subscription(
            subscription_id
        )

        await query.edit_message_text(
            "✅ لینک حذف شد.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 پنل مدیریت",
                        callback_data="admin"
                    )
                ]
            ])
        )

        return

    # -------------------------
    # مدیریت تست
    # -------------------------

    if data == "admin_trial":

        if user_id != ADMIN_ID:
            return

        await show_admin_trial(query)

        return

    if data == "admin_trial_add":

        if user_id != ADMIN_ID:
            return

        context.user_data[
            "admin_waiting_trial_link"
        ] = True

        await query.edit_message_text(
            "➕ افزودن لینک تست\n\n"
            "لینک Subscription تست 100MB / 1 روز را ارسال کن."
        )

        return

    if data == "admin_trial_delete":

        if user_id != ADMIN_ID:
            return

        await show_admin_trial_delete(query)

        return

    if data.startswith("trial_delete_"):

        if user_id != ADMIN_ID:
            return

        trial_id = int(
            data.split("_")[2]
        )

        delete_free_trial(
            trial_id
        )

        await query.edit_message_text(
            "✅ لینک تست حذف شد.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 مدیریت تست",
                        callback_data="admin_trial"
                    )
                ]
            ])
        )

        return

    if data == "admin_trial_stock":

        if user_id != ADMIN_ID:
            return

        stock = get_free_trial_stock()

        await query.edit_message_text(
            "🎁 موجودی تست رایگان\n\n"
            "📦 حجم: 100 مگابایت\n"
            "⏳ مدت: 1 روز\n"
            f"🔢 موجودی: {stock}",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 مدیریت تست",
                        callback_data="admin_trial"
                    )
                ]
            ])
        )

        return

    # -------------------------
    # کوپن ادمین
    # -------------------------

    if data == "admin_coupon":

        if user_id != ADMIN_ID:
            return

        context.user_data[
            "admin_waiting_coupon"
        ] = True

        await query.edit_message_text(
            "🎟 ساخت کد تخفیف\n\n"
            "فرمت:\n"
            "CODE درصد تعداد\n\n"
            "مثال:\n"
            "HANZU20 20 100\n\n"
            "یعنی 20٪ تخفیف برای حداکثر 100 استفاده."
        )

        return

    # -------------------------
    # پیام همگانی
    # -------------------------

    if data == "admin_broadcast":

        if user_id != ADMIN_ID:
            return

        context.user_data[
            "admin_broadcast"
        ] = True

        await query.edit_message_text(
            "📢 پیام همگانی\n\n"
            "متنی که می‌خواهی برای کاربران ارسال شود را بفرست."
        )

        return

    # -------------------------
    # تیکت‌های ادمین
    # -------------------------

    if data == "admin_tickets":

        if user_id != ADMIN_ID:
            return

        conn = get_db()

        rows = conn.execute("""
            SELECT *
            FROM tickets
            WHERE status = 'open'
            ORDER BY id DESC
            LIMIT 20
        """).fetchall()

        conn.close()

        if not rows:

            text = "🎫 تیکت باز نداریم."

            keyboard = [
                [
                    InlineKeyboardButton(
                        "🔙 پنل مدیریت",
                        callback_data="admin"
                    )
                ]
            ]

        else:

            text = "🎫 تیکت‌های باز\n\n"

            keyboard = []

            for row in rows:

                text += (
                    f"#{row['id']} | "
                    f"User: {row['user_id']}\n"
                )

                keyboard.append([
                    InlineKeyboardButton(
                        f"🎫 تیکت #{row['id']}",
                        callback_data=f"ticket_{row['id']}"
                    )
                ])

            keyboard.append([
                InlineKeyboardButton(
                    "🔙 پنل مدیریت",
                    callback_data="admin"
                )
            ])

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return

    # -------------------------
    # باز کردن تیکت
    # -------------------------

    if data.startswith("ticket_"):

        if user_id != ADMIN_ID:
            return

        ticket_id = int(
            data.split("_")[1]
        )

        conn = get_db()

        ticket = conn.execute("""
            SELECT *
            FROM tickets
            WHERE id = ?
        """, (ticket_id,)).fetchone()

        messages = conn.execute("""
            SELECT *
            FROM ticket_messages
            WHERE ticket_id = ?
            ORDER BY id ASC
            LIMIT 10
        """, (ticket_id,)).fetchall()

        conn.close()

        if not ticket:
            return

        text = (
            f"🎫 تیکت #{ticket_id}\n"
            f"👤 User ID: {ticket['user_id']}\n\n"
        )

        for msg in messages:

            sender = (
                "کاربر"
                if msg["sender_id"] != ADMIN_ID
                else "ادمین"
            )

            text += (
                f"{sender}:\n"
                f"{msg['message']}\n\n"
            )

        context.user_data[
            "admin_ticket_id"
        ] = ticket_id

        context.user_data[
            "admin_waiting_ticket_reply"
        ] = True

        await query.edit_message_text(
            text +
            "\n✏️ پاسخ خود را ارسال کنید.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔒 بستن تیکت",
                        callback_data=f"close_ticket_{ticket_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔙 تیکت‌ها",
                        callback_data="admin_tickets"
                    )
                ]
            ])
        )

        return

    # -------------------------
    # بستن تیکت
    # -------------------------

    if data.startswith("close_ticket_"):

        if user_id != ADMIN_ID:
            return

        ticket_id = int(
            data.split("_")[2]
        )

        conn = get_db()

        ticket = conn.execute("""
            SELECT *
            FROM tickets
            WHERE id = ?
        """, (ticket_id,)).fetchone()

        conn.execute("""
            UPDATE tickets
            SET status = 'closed',
                closed_at = ?
            WHERE id = ?
        """, (
            now_text(),
            ticket_id
        ))

        conn.commit()
        conn.close()

        if ticket:

            try:

                await context.bot.send_message(
                    chat_id=ticket["user_id"],
                    text=(
                        f"🔒 تیکت #{ticket_id} بسته شد.\n\n"
                        "در صورت نیاز می‌توانید تیکت جدید ایجاد کنید."
                    )
                )

            except Exception:
                pass

        await query.edit_message_text(
            "✅ تیکت بسته شد.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 پنل مدیریت",
                        callback_data="admin"
                    )
                ]
            ])
        )

        return

    # -------------------------
    # تأیید سفارش
    # -------------------------

    if data.startswith("approve_"):

        if user_id != ADMIN_ID:
            return

        order_id = int(
            data.split("_")[1]
        )

        result = approve_order(
            order_id
        )

        if result["status"] == "not_found":

            await query.answer(
                "سفارش پیدا نشد.",
                show_alert=True
            )

            return

        if result["status"] == "already_processed":

            await query.answer(
                "این سفارش قبلاً پردازش شده.",
                show_alert=True
            )

            return

        if result["status"] == "no_stock":

            await query.answer(
                "برای این حجم لینک موجود نیست.",
                show_alert=True
            )

            return

        order = result["order"]

        await context.bot.send_message(
            chat_id=order["user_id"],
            text=(
                "✅ پرداخت شما تأیید شد.\n\n"
                "🌐 HanzuVPN\n\n"
                f"📦 حجم: {order['volume']} گیگ\n"
                "⏳ مدت: 30 روز\n"
                f"📅 انقضا: {result['expires_at']}\n"
                f"🧾 سفارش: #{order_id}\n\n"
                "🔗 لینک Subscription:\n\n"
                f"{result['link']}\n\n"
                "📌 لینک را در برنامه VPN خود وارد کنید."
            )
        )

        await query.edit_message_caption(
            caption=(
                f"✅ سفارش #{order_id} تأیید شد.\n\n"
                f"📦 {order['volume']} گیگ\n"
                f"💰 {order['price']:,} تومان\n"
                f"📅 انقضا: {result['expires_at']}"
            )
        )

        return

    # -------------------------
    # رد سفارش
    # -------------------------

    if data.startswith("reject_"):

        if user_id != ADMIN_ID:
            return

        order_id = int(
            data.split("_")[1]
        )

        changed, order = reject_order(
            order_id
        )

        if not order:

            await query.answer(
                "سفارش پیدا نشد.",
                show_alert=True
            )

            return

        if not changed:

            await query.answer(
                "این سفارش قبلاً پردازش شده.",
                show_alert=True
            )

            return

        await context.bot.send_message(
            chat_id=order["user_id"],
            text=(
                "❌ پرداخت سفارش شما تأیید نشد.\n\n"
                f"🧾 سفارش: #{order_id}\n\n"
                "در صورت اشتباه با پشتیبانی تماس بگیرید."
            )
        )

        await query.edit_message_caption(
            caption=(
                f"❌ سفارش #{order_id} رد شد.\n\n"
                f"📦 {order['volume']} گیگ\n"
                f"💰 {order['price']:,} تومان"
            )
        )

        return


# =========================================================
# پیام‌های متنی
# =========================================================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    text = update.message.text.strip()

    ensure_user(user)

    # -------------------------
    # پیام تیکت کاربر
    # -------------------------

    if context.user_data.get(
        "waiting_ticket_message"
    ):

        ticket_id = context.user_data.get(
            "ticket_id"
        )

        if not ticket_id:
            return

        add_ticket_message(
            ticket_id,
            user.id,
            text
        )

        context.user_data[
            "waiting_ticket_message"
        ] = False

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"🎫 تیکت جدید #{ticket_id}\n\n"
                f"👤 {user.first_name or '-'}\n"
                f"🆔 {user.id}\n\n"
                f"💬 {text}"
            ),
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🎫 مشاهده تیکت",
                        callback_data=f"ticket_{ticket_id}"
                    )
                ]
            ])
        )

        await update.message.reply_text(
            f"✅ پیام شما در تیکت #{ticket_id} ثبت شد.\n\n"
            "پشتیبانی آن را بررسی می‌کند."
        )

        return

    # -------------------------
    # پاسخ ادمین به تیکت
    # -------------------------

    if (
        user.id == ADMIN_ID
        and context.user_data.get(
            "admin_waiting_ticket_reply"
        )
    ):

        ticket_id = context.user_data.get(
            "admin_ticket_id"
        )

        conn = get_db()

        ticket = conn.execute("""
            SELECT *
            FROM tickets
            WHERE id = ?
        """, (ticket_id,)).fetchone()

        conn.close()

        if not ticket:
            return

        add_ticket_message(
            ticket_id,
            ADMIN_ID,
            text
        )

        await context.bot.send_message(
            chat_id=ticket["user_id"],
            text=(
                f"💬 پاسخ پشتیبانی\n\n"
                f"🎫 تیکت #{ticket_id}\n\n"
                f"{text}"
            )
        )

        await update.message.reply_text(
            "✅ پاسخ برای کاربر ارسال شد."
        )

        context.user_data[
            "admin_waiting_ticket_reply"
        ] = False

        return

    # -------------------------
    # پیام همگانی
    # -------------------------

    if (
        user.id == ADMIN_ID
        and context.user_data.get(
            "admin_broadcast"
        )
    ):

        context.user_data[
            "admin_broadcast"
        ] = False

        conn = get_db()

        users = conn.execute("""
            SELECT user_id
            FROM users
        """).fetchall()

        conn.close()

        sent = 0
        failed = 0

        for row in users:

            try:

                await context.bot.send_message(
                    chat_id=row["user_id"],
                    text=text
                )

                sent += 1

                await asyncio.sleep(0.05)

            except Exception:

                failed += 1

        await update.message.reply_text(
            "📢 ارسال همگانی تمام شد.\n\n"
            f"✅ ارسال موفق: {sent}\n"
            f"❌ ناموفق: {failed}"
        )

        return

    # -------------------------
    # ساخت کوپن
    # -------------------------

    if (
        user.id == ADMIN_ID
        and context.user_data.get(
            "admin_waiting_coupon"
        )
    ):

        parts = text.split()

        if len(parts) != 3:

            await update.message.reply_text(
                "❌ فرمت اشتباه است.\n\n"
                "مثال:\n"
                "HANZU20 20 100"
            )

            return

        code = parts[0].upper()

        try:

            percent = int(parts[1])
            max_uses = int(parts[2])

            if percent <= 0 or percent > 100:
                raise ValueError

            if max_uses < 0:
                raise ValueError

        except ValueError:

            await update.message.reply_text(
                "❌ درصد یا تعداد استفاده نامعتبر است."
            )

            return

        success = create_coupon(
            code,
            percent,
            max_uses
        )

        if success:

            await update.message.reply_text(
                "✅ کد تخفیف ساخته شد.\n\n"
                f"🎟 کد: {code}\n"
                f"💰 تخفیف: {percent}%\n"
                f"🔢 تعداد استفاده: "
                f"{'نامحدود' if max_uses == 0 else max_uses}"
            )

        else:

            await update.message.reply_text(
                "❌ این کد تخفیف قبلاً وجود دارد."
            )

        context.user_data[
            "admin_waiting_coupon"
        ] = False

        return

    # -------------------------
    # افزودن تست
    # -------------------------

    if (
        user.id == ADMIN_ID
        and context.user_data.get(
            "admin_waiting_trial_link"
        )
    ):

        if not (
            text.startswith("http://")
            or text.startswith("https://")
        ):

            await update.message.reply_text(
                "❌ لینک معتبر نیست."
            )

            return

        add_free_trial(text)

        context.user_data[
            "admin_waiting_trial_link"
        ] = False

        await update.message.reply_text(
            "✅ لینک تست اضافه شد.\n\n"
            "📦 حجم: 100 مگابایت\n"
            "⏳ مدت: 1 روز"
        )

        return

    # -------------------------
    # حجم دلخواه
    # -------------------------

    if context.user_data.get(
        "waiting_custom_volume"
    ):

        context.user_data[
            "waiting_custom_volume"
        ] = False

        try:

            volume = int(text)

            if volume <= 0 or volume > 1000:
                raise ValueError

        except ValueError:

            await update.message.reply_text(
                "❌ حجم نامعتبر است.\n\n"
                "مثلاً 25 وارد کن."
            )

            return

        price = volume * PRICE_PER_GB

        await update.message.reply_text(
            "🛒 سرویس دلخواه\n\n"
            f"📦 حجم: {volume} گیگ\n"
            f"💰 قیمت: {price:,} تومان\n"
            "⏳ مدت: 30 روز",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "💳 پرداخت کردم",
                        callback_data=f"paid_{volume}_{price}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔙 خرید",
                        callback_data="buy"
                    )
                ]
            ])
        )

        return

    # -------------------------
    # وارد کردن کوپن
    # -------------------------

    if context.user_data.get(
        "waiting_coupon"
    ):

        context.user_data[
            "waiting_coupon"
        ] = False

        coupon = get_coupon(
            text.upper()
        )

        if not coupon:

            await update.message.reply_text(
                "❌ کد تخفیف نامعتبر است."
            )

            return

        if user_used_coupon(
            coupon["id"],
            user.id
        ):

            await update.message.reply_text(
                "⚠️ شما قبلاً از این کد استفاده کرده‌اید."
            )

            return

        context.user_data[
            "coupon_code"
        ] = coupon["code"]

        await update.message.reply_text(
            "✅ کد تخفیف معتبر است.\n\n"
            f"🎟 کد: {coupon['code']}\n"
            f"💰 تخفیف: {coupon['percent']}%\n\n"
            "حالا سرویس موردنظر را انتخاب کنید:",
            reply_markup=buy_keyboard()
        )

        return

    # -------------------------
    # حجم لینک ادمین
    # -------------------------

    if (
        user.id == ADMIN_ID
        and context.user_data.get(
            "admin_waiting_volume"
        )
    ):

        try:

            volume = int(text)

            if volume <= 0 or volume > 1000:
                raise ValueError

        except ValueError:

            await update.message.reply_text(
                "❌ حجم نامعتبر است."
            )

            return

        context.user_data[
            "admin_waiting_volume"
        ] = False

        context.user_data[
            "admin_add_volume"
        ] = str(volume)

        context.user_data[
            "admin_waiting_link"
        ] = True

        await update.message.reply_text(
            f"✅ حجم {volume} گیگ ثبت شد.\n\n"
            "حالا لینک Subscription را ارسال کن."
        )

        return

    # -------------------------
    # لینک سرویس ادمین
    # -------------------------

    if (
        user.id == ADMIN_ID
        and context.user_data.get(
            "admin_waiting_link"
        )
    ):

        if not (
            text.startswith("http://")
            or text.startswith("https://")
        ):

            await update.message.reply_text(
                "❌ لینک معتبر نیست."
            )

            return

        volume = context.user_data.get(
            "admin_add_volume"
        )

        add_subscription(
            volume,
            text
        )

        context.user_data.pop(
            "admin_waiting_link",
            None
        )

        context.user_data.pop(
            "admin_add_volume",
            None
        )

        await update.message.reply_text(
            "✅ لینک اضافه شد.\n\n"
            f"📦 حجم: {volume} گیگ"
        )

        return


# =========================================================
# رسید پرداخت
# =========================================================

async def receipt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    ensure_user(user)

    order = get_latest_pending_order(
        user.id
    )

    if not order:

        await update.message.reply_text(
            "❌ سفارش در انتظار پرداختی پیدا نشد."
        )

        return

    caption = (
        "💳 رسید پرداخت جدید\n\n"
        f"🧾 سفارش: #{order['id']}\n"
        f"👤 نام: {user.first_name or '-'}\n"
        f"👤 Username: "
        f"@{user.username if user.username else '-'}\n"
        f"🆔 User ID: {user.id}\n\n"
        f"📦 حجم: {order['volume']} گیگ\n"
        f"💰 مبلغ: {order['price']:,} تومان\n"
        f"🕐 زمان: {order['created_at']}"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ تأیید پرداخت",
                callback_data=f"approve_{order['id']}"
            ),
            InlineKeyboardButton(
                "❌ رد پرداخت",
                callback_data=f"reject_{order['id']}"
            )
        ]
    ]

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=update.message.photo[-1].file_id,
        caption=caption,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    await update.message.reply_text(
        "✅ رسید شما دریافت شد.\n\n"
        f"🧾 سفارش #{order['id']}\n\n"
        "پس از بررسی توسط مدیریت، نتیجه برای شما ارسال می‌شود."
    )


# =========================================================
# یادآوری انقضا
# =========================================================

async def expiration_checker(application):

    while True:

        try:

            conn = get_db()

            rows = conn.execute("""
                SELECT *
                FROM orders
                WHERE status = 'approved'
                AND expires_at IS NOT NULL
            """).fetchall()

            conn.close()

            now = datetime.now()

            for row in rows:

                try:

                    expires = datetime.strptime(
                        row["expires_at"],
                        "%Y-%m-%d %H:%M:%S"
                    )

                except Exception:

                    continue

                remaining = expires - now
                days = remaining.total_seconds() / 86400

                reminder_type = None
                message = None

                if 2.5 <= days <= 3.5:
                    reminder_type = "3days"
                    message = (
                        "⚠️ یادآوری HanzuVPN\n\n"
                        f"سرویس #{row['id']} شما "
                        "حدود 3 روز دیگر منقضی می‌شود.\n\n"
                        "برای تمدید از بخش «🔄 تمدید» استفاده کنید."
                    )

                elif 0.5 <= days <= 1.5:
                    reminder_type = "1day"
                    message = (
                        "⏰ یادآوری HanzuVPN\n\n"
                        f"سرویس #{row['id']} شما "
                        "حدود 1 روز دیگر منقضی می‌شود.\n\n"
                        "برای تمدید سرویس اقدام کنید."
                    )

                if not reminder_type:
                    continue

                conn = get_db()

                exists = conn.execute("""
                    SELECT id
                    FROM reminders
                    WHERE order_id = ?
                    AND reminder_type = ?
                """, (
                    row["id"],
                    reminder_type
                )).fetchone()

                if not exists:

                    conn.execute("""
                        INSERT INTO reminders
                        (
                            order_id,
                            user_id,
                            reminder_type,
                            sent_at
                        )
                        VALUES (?, ?, ?, ?)
                    """, (
                        row["id"],
                        row["user_id"],
                        reminder_type,
                        now_text()
                    ))

                    conn.commit()

                    try:

                        await application.bot.send_message(
                            chat_id=row["user_id"],
                            text=message
                        )

                    except Exception:
                        pass

                conn.close()

        except Exception as e:

            print(
                "Expiration checker error:",
                e
            )

        await asyncio.sleep(6 * 60 * 60)


# =========================================================
# اجرای ربات
# =========================================================

async def post_init(application):

    await set_bot_commands(
        application
    )

    application.create_task(
        expiration_checker(
            application
        )
    )


def main():

    if not BOT_TOKEN:

        raise RuntimeError(
            "BOT_TOKEN تنظیم نشده است."
        )

    init_db()

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # دستورات
    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "buy",
            buy_command
        )
    )

    app.add_handler(
        CommandHandler(
            "services",
            services_command
        )
    )

    app.add_handler(
        CommandHandler(
            "trial",
            trial_command
        )
    )

    app.add_handler(
        CommandHandler(
            "support",
            support_command
        )
    )

    app.add_handler(
        CommandHandler(
            "help",
            help_command
        )
    )

    # دکمه‌ها
    app.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

    # رسید
    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            receipt_handler
        )
    )

    # متن
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