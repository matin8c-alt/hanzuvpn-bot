
import os
import sqlite3
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================
# تنظیمات
# =========================

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

PRICE_PER_GB = 3500


# =========================
# دیتابیس
# =========================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    # لینک‌های سرویس پولی
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
            approved_at TEXT
        )
    """)

    # لینک‌های تست رایگان
    conn.execute("""
        CREATE TABLE IF NOT EXISTS free_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link TEXT NOT NULL,
            used INTEGER DEFAULT 0
        )
    """)

    # کاربرانی که تست گرفته‌اند
    conn.execute("""
        CREATE TABLE IF NOT EXISTS free_test_users (
            user_id INTEGER PRIMARY KEY,
            test_id INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# =========================
# لینک‌های سرویس پولی
# =========================

def add_subscription(volume, link):
    conn = get_db()

    conn.execute(
        "INSERT INTO subscriptions (volume, link, used) VALUES (?, ?, 0)",
        (str(volume), link)
    )

    conn.commit()
    conn.close()


def get_available_subscription(volume):
    conn = get_db()

    row = conn.execute("""
        SELECT id, link
        FROM subscriptions
        WHERE volume = ? AND used = 0
        ORDER BY id ASC
        LIMIT 1
    """, (str(volume),)).fetchone()

    conn.close()
    return row


def delete_subscription(subscription_id):
    conn = get_db()

    conn.execute(
        "DELETE FROM subscriptions WHERE id = ? AND used = 0",
        (subscription_id,)
    )

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

    stock = {}

    for row in rows:
        stock[row["volume"]] = row["count"]

    return stock


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


# =========================
# تست رایگان
# =========================

def add_free_test(link):
    conn = get_db()

    conn.execute(
        "INSERT INTO free_tests (link, used) VALUES (?, 0)",
        (link,)
    )

    conn.commit()
    conn.close()


def get_free_test_stock():
    conn = get_db()

    count = conn.execute("""
        SELECT COUNT(*)
        FROM free_tests
        WHERE used = 0
    """).fetchone()[0]

    conn.close()

    return count


def get_available_free_test():
    conn = get_db()

    row = conn.execute("""
        SELECT id, link
        FROM free_tests
        WHERE used = 0
        ORDER BY id ASC
        LIMIT 1
    """).fetchone()

    conn.close()

    return row


def get_free_test_list():
    conn = get_db()

    rows = conn.execute("""
        SELECT id, link
        FROM free_tests
        WHERE used = 0
        ORDER BY id ASC
    """).fetchall()

    conn.close()

    return rows


def delete_free_test(test_id):
    conn = get_db()

    conn.execute("""
        DELETE FROM free_tests
        WHERE id = ?
        AND used = 0
    """, (test_id,))

    conn.commit()
    conn.close()


def user_already_got_test(user_id):
    conn = get_db()

    row = conn.execute("""
        SELECT user_id
        FROM free_test_users
        WHERE user_id = ?
    """, (user_id,)).fetchone()

    conn.close()

    return row is not None


def give_free_test(user_id):
    conn = get_db()

    try:
        conn.execute("BEGIN IMMEDIATE")

        # بررسی اینکه قبلاً تست گرفته یا نه
        existing = conn.execute("""
            SELECT user_id
            FROM free_test_users
            WHERE user_id = ?
        """, (user_id,)).fetchone()

        if existing:
            conn.rollback()
            return {
                "status": "already_used"
            }

        # پیدا کردن یک تست آزاد
        test = conn.execute("""
            SELECT id, link
            FROM free_tests
            WHERE used = 0
            ORDER BY id ASC
            LIMIT 1
        """).fetchone()

        if not test:
            conn.rollback()
            return {
                "status": "no_stock"
            }

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ثبت اینکه کاربر تست گرفته
        conn.execute("""
            INSERT INTO free_test_users
            (
                user_id,
                test_id,
                created_at
            )
            VALUES (?, ?, ?)
        """, (
            user_id,
            test["id"],
            now
        ))

        # مصرف تست
        conn.execute("""
            UPDATE free_tests
            SET used = 1
            WHERE id = ?
            AND used = 0
        """, (test["id"],))

        conn.commit()

        return {
            "status": "success",
            "link": test["link"]
        }

    except sqlite3.IntegrityError:
        conn.rollback()

        return {
            "status": "already_used"
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# =========================
# سفارش‌ها
# =========================

def create_order(user, volume, price):
    conn = get_db()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
        now,
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
            return {"status": "not_found"}

        if order["status"] != "pending":
            conn.rollback()

            return {
                "status": "already_processed",
                "order": order,
            }

        subscription = conn.execute("""
            SELECT id, link
            FROM subscriptions
            WHERE volume = ?
            AND used = 0
            ORDER BY id ASC
            LIMIT 1
        """, (order["volume"],)).fetchone()

        if not subscription:
            conn.rollback()

            return {
                "status": "no_stock",
                "order": order,
            }

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        updated = conn.execute("""
            UPDATE orders
            SET status = 'approved',
                subscription_id = ?,
                approved_at = ?
            WHERE id = ?
            AND status = 'pending'
        """, (
            subscription["id"],
            now,
            order_id,
        ))

        if updated.rowcount != 1:
            conn.rollback()

            return {
                "status": "already_processed"
            }

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


# =========================
# آمار
# =========================

def get_stats():
    conn = get_db()

    total_orders = conn.execute("""
        SELECT COUNT(*)
        FROM orders
    """).fetchone()[0]

    approved_orders = conn.execute("""
        SELECT COUNT(*)
        FROM orders
        WHERE status = 'approved'
    """).fetchone()[0]

    pending_orders = conn.execute("""
        SELECT COUNT(*)
        FROM orders
        WHERE status = 'pending'
    """).fetchone()[0]

    rejected_orders = conn.execute("""
        SELECT COUNT(*)
        FROM orders
        WHERE status = 'rejected'
    """).fetchone()[0]

    total_sales = conn.execute("""
        SELECT COALESCE(SUM(price), 0)
        FROM orders
        WHERE status = 'approved'
    """).fetchone()[0]

    customers = conn.execute("""
        SELECT COUNT(DISTINCT user_id)
        FROM orders
    """).fetchone()[0]

    conn.close()

    return {
        "total_orders": total_orders,
        "approved_orders": approved_orders,
        "pending_orders": pending_orders,
        "rejected_orders": rejected_orders,
        "total_sales": total_sales,
        "customers": customers,
    }


# =========================
# منوی اصلی
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
                "🎁 تست رایگان",
                callback_data="free_test"
            )
        ],
        [
            InlineKeyboardButton(
                "📦 سرویس‌های من",
                callback_data="my_services"
            ),
            InlineKeyboardButton(
                "💬 پشتیبانی",
                callback_data="support"
            ),
        ],
    ]

    if update.effective_user.id == ADMIN_ID:
        keyboard.append([
            InlineKeyboardButton(
                "⚙️ پنل مدیریت",
                callback_data="admin"
            )
        ])

    await update.message.reply_text(
        "🌐 HanzuVPN\n\n"
        "به ربات فروش خودکار HanzuVPN خوش آمدید ❤️\n\n"
        "از منوی زیر انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================
# خرید
# =========================

async def show_buy_menu(query):

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
                "✏️ حجم دلخواه",
                callback_data="custom"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="home"
            )
        ],
    ]

    await query.edit_message_text(
        "🛒 انتخاب سرویس\n\n"
        "⏳ مدت تمام سرویس‌ها: 30 روز\n\n"
        "حجم موردنظر خود را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_payment(query, volume, price):

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
        ],
    ]

    await query.edit_message_text(
        "💳 اطلاعات پرداخت\n\n"
        f"📦 حجم: {volume} گیگ\n"
        f"💰 مبلغ: {price:,} تومان\n"
        "⏳ مدت: 30 روز\n\n"
        "💳 شماره کارت:\n"
        f"`{CARD_NUMBER}`\n\n"
        "بعد از انتقال مبلغ، روی دکمه «پرداخت کردم» بزنید "
        "و سپس تصویر رسید را ارسال کنید.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================
# پنل مدیریت
# =========================

async def show_admin(query):

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
            ),
            InlineKeyboardButton(
                "🗑 حذف لینک",
                callback_data="admin_delete"
            ),
        ],
        [
            InlineKeyboardButton(
                "🎁 مدیریت تست رایگان",
                callback_data="admin_tests"
            )
        ],
        [
            InlineKeyboardButton(
                "📊 آمار فروش",
                callback_data="admin_stats"
            )
        ],
        [
            InlineKeyboardButton(
                "🧾 سفارش‌ها",
                callback_data="admin_orders"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="home"
            )
        ],
    ]

    await query.edit_message_text(
        "⚙️ پنل مدیریت HanzuVPN\n\n"
        "مدیریت فروش، سرویس‌ها و تست رایگان:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_stock(query):

    stock = get_stock()

    text = "📦 موجودی سرویس‌ها\n\n"

    if not stock:
        text += "❌ موجودی خالی است."
    else:
        for volume, count in stock.items():
            text += f"🔹 {volume} گیگ: {count} عدد\n"

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


async def show_stats(query):

    stats = get_stats()

    text = (
        "📊 آمار فروش HanzuVPN\n\n"
        f"🧾 کل سفارش‌ها: {stats['total_orders']}\n"
        f"✅ سفارش‌های تأییدشده: {stats['approved_orders']}\n"
        f"⏳ در انتظار پرداخت: {stats['pending_orders']}\n"
        f"❌ ردشده: {stats['rejected_orders']}\n\n"
        f"👥 تعداد مشتری‌ها: {stats['customers']}\n"
        f"💰 مجموع فروش: {stats['total_sales']:,} تومان"
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


async def show_orders(query):

    conn = get_db()

    rows = conn.execute("""
        SELECT *
        FROM orders
        ORDER BY id DESC
        LIMIT 15
    """).fetchall()

    conn.close()

    if not rows:
        text = "🧾 هنوز سفارشی ثبت نشده است."

    else:
        text = "🧾 آخرین سفارش‌ها\n\n"

        for row in rows:

            status = {
                "pending": "⏳ در انتظار",
                "approved": "✅ تأیید",
                "rejected": "❌ رد",
            }.get(
                row["status"],
                row["status"]
            )

            name = row["first_name"] or "بدون نام"

            text += (
                f"#{row['id']} | {name}\n"
                f"📦 {row['volume']} گیگ | "
                f"💰 {row['price']:,} تومان\n"
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


async def show_delete_menu(query):

    rows = get_subscription_list()

    if not rows:

        await query.edit_message_text(
            "🗑 حذف لینک\n\n"
            "❌ هیچ لینک استفاده‌نشده‌ای وجود ندارد.",
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


# =========================
# مدیریت تست رایگان
# =========================

async def show_test_admin(query):

    stock = get_free_test_stock()

    keyboard = [
        [
            InlineKeyboardButton(
                "➕ افزودن لینک تست",
                callback_data="admin_test_add"
            )
        ],
        [
            InlineKeyboardButton(
                "📦 موجودی تست",
                callback_data="admin_test_stock"
            )
        ],
        [
            InlineKeyboardButton(
                "🗑 حذف تست",
                callback_data="admin_test_delete"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 پنل مدیریت",
                callback_data="admin"
            )
        ],
    ]

    await query.edit_message_text(
        "🎁 مدیریت تست رایگان\n\n"
        "📦 حجم هر تست: 100 مگابایت\n"
        "⏳ اعتبار: 1 روز\n"
        f"📊 موجودی فعلی: {stock} عدد",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_test_stock(query):

    stock = get_free_test_stock()

    await query.edit_message_text(
        "🎁 موجودی تست رایگان\n\n"
        f"📦 تست‌های آماده: {stock} عدد\n\n"
        "هر تست:\n"
        "📦 100 مگابایت\n"
        "⏳ 1 روز",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔙 مدیریت تست",
                    callback_data="admin_tests"
                )
            ]
        ])
    )


async def show_test_delete(query):

    rows = get_free_test_list()

    if not rows:

        await query.edit_message_text(
            "🗑 حذف تست\n\n"
            "❌ تست آماده‌ای برای حذف وجود ندارد.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 مدیریت تست",
                        callback_data="admin_tests"
                    )
                ]
            ])
        )

        return

    keyboard = []

    for row in rows:

        keyboard.append([
            InlineKeyboardButton(
                f"🗑 حذف تست #{row['id']}",
                callback_data=f"delete_test_{row['id']}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "🔙 مدیریت تست",
            callback_data="admin_tests"
        )
    ])

    await query.edit_message_text(
        "🗑 کدام تست حذف شود؟",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================
# Callback ها
# =========================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = query.from_user.id

    # =========================
    # صفحه اصلی
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
                    "🎁 تست رایگان",
                    callback_data="free_test"
                )
            ],
            [
                InlineKeyboardButton(
                    "📦 سرویس‌های من",
                    callback_data="my_services"
                ),
                InlineKeyboardButton(
                    "💬 پشتیبانی",
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

        await query.edit_message_text(
            "🌐 HanzuVPN\n\n"
            "منوی اصلی:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return

    # =========================
    # تست رایگان
    # =========================

    if data == "free_test":

        if user_already_got_test(user_id):

            await query.edit_message_text(
                "❌ شما قبلاً تست رایگان خود را دریافت کرده‌اید.\n\n"
                "🎁 هر کاربر فقط یک بار می‌تواند تست رایگان بگیرد.\n\n"
                "برای خرید سرویس می‌توانید از منوی خرید استفاده کنید.",
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

        stock = get_free_test_stock()

        if stock <= 0:

            await query.edit_message_text(
                "😔 متأسفانه در حال حاضر تست رایگان موجود نیست.\n\n"
                "لطفاً بعداً دوباره امتحان کنید.",
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

        keyboard = [
            [
                InlineKeyboardButton(
                    "🎁 دریافت تست",
                    callback_data="get_free_test"
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ انصراف",
                    callback_data="home"
                )
            ]
        ]

        await query.edit_message_text(
            "🎁 تست رایگان HanzuVPN\n\n"
            "📦 حجم: 100 مگابایت\n"
            "⏳ اعتبار: 1 روز\n\n"
            "⚠️ هر کاربر فقط یک بار می‌تواند تست رایگان دریافت کند.\n\n"
            "آیا می‌خواهید تست رایگان خود را دریافت کنید؟",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return

    # =========================
    # دریافت تست
    # =========================

    if data == "get_free_test":

        result = give_free_test(user_id)

        if result["status"] == "already_used":

            await query.edit_message_text(
                "❌ شما قبلاً تست رایگان دریافت کرده‌اید.",
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

        if result["status"] == "no_stock":

            await query.edit_message_text(
                "❌ متأسفانه تست رایگان تمام شده است.",
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

        test_link = result["link"]

        await query.edit_message_text(
            "🎉 تست رایگان شما فعال شد!\n\n"
            "🌐 HanzuVPN\n\n"
            "📦 حجم: 100 مگابایت\n"
            "⏳ اعتبار: 1 روز\n\n"
            "🔗 لینک Subscription:\n\n"
            f"{test_link}\n\n"
            "📌 لینک را در برنامه VPN خود وارد کنید.\n\n"
            "⚠️ هر کاربر فقط یک بار می‌تواند تست رایگان دریافت کند.",
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

    # =========================
    # خرید
    # =========================

    if data == "buy":

        await show_buy_menu(query)
        return

    # =========================
    # پلن‌ها
    # =========================

    if data.startswith("plan_"):

        volume = data.split("_")[1]
        price = PLANS.get(volume)

        if not price:
            return

        await show_payment(
            query,
            volume,
            price
        )

        return

    # =========================
    # حجم دلخواه
    # =========================

    if data == "custom":

        context.user_data["waiting_custom_volume"] = True

        await query.edit_message_text(
            "✏️ حجم دلخواه\n\n"
            "لطفاً حجم موردنظر را به گیگ وارد کنید.\n\n"
            "مثال:\n"
            "25"
        )

        return

    # =========================
    # پرداخت کردم
    # =========================

    if data.startswith("paid_"):

        parts = data.split("_")

        if len(parts) != 3:
            return

        volume = parts[1]
        price = int(parts[2])

        order_id = create_order(
            query.from_user,
            volume,
            price
        )

        context.user_data["last_order_id"] = order_id

        await query.edit_message_text(
            "✅ سفارش شما ثبت شد.\n\n"
            f"📦 حجم: {volume} گیگ\n"
            f"💰 مبلغ: {price:,} تومان\n"
            f"🧾 شماره سفارش: #{order_id}\n\n"
            "📸 حالا تصویر رسید پرداخت را همینجا ارسال کنید.\n\n"
            "پس از بررسی، سرویس برای شما ارسال می‌شود."
        )

        return

    # =========================
    # سرویس‌های من
    # =========================

    if data == "my_services":

        conn = get_db()

        rows = conn.execute("""
            SELECT
                o.id,
                o.volume,
                o.price,
                o.approved_at,
                s.link
            FROM orders o
            LEFT JOIN subscriptions s
            ON o.subscription_id = s.id
            WHERE o.user_id = ?
            AND o.status = 'approved'
            ORDER BY o.id DESC
        """, (user_id,)).fetchall()

        conn.close()

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
                    f"⏳ مدت: 30 روز\n"
                    f"🕐 تاریخ: {row['approved_at']}\n\n"
                    f"🔗 لینک:\n{row['link']}\n\n"
                    "━━━━━━━━━━━━\n\n"
                )

        await query.edit_message_text(
            text,
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

    # =========================
    # پشتیبانی
    # =========================

    if data == "support":

        await query.edit_message_text(
            "💬 پشتیبانی HanzuVPN\n\n"
            "در صورت وجود مشکل در خرید یا فعال‌سازی سرویس، "
            "پیام خود را برای پشتیبانی ارسال کنید.",
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

    # =========================
    # پنل مدیریت
    # =========================

    if data == "admin":

        if user_id != ADMIN_ID:
            return

        await show_admin(query)
        return

    # =========================
    # مدیریت تست
    # =========================

    if data == "admin_tests":

        if user_id != ADMIN_ID:
            return

        await show_test_admin(query)
        return

    # افزودن تست
    if data == "admin_test_add":

        if user_id != ADMIN_ID:
            return

        context.user_data["admin_waiting_test_link"] = True

        await query.edit_message_text(
            "➕ افزودن لینک تست رایگان\n\n"
            "لینک Subscription تست را ارسال کن.\n\n"
            "⚠️ مشخصات تست:\n"
            "📦 100 مگابایت\n"
            "⏳ 1 روز"
        )

        return

    # موجودی تست
    if data == "admin_test_stock":

        if user_id != ADMIN_ID:
            return

        await show_test_stock(query)
        return

    # حذف تست
    if data == "admin_test_delete":

        if user_id != ADMIN_ID:
            return

        await show_test_delete(query)
        return

    # حذف تست مشخص
    if data.startswith("delete_test_"):

        if user_id != ADMIN_ID:
            return

        test_id = int(
            data.replace(
                "delete_test_",
                ""
            )
        )

        delete_free_test(test_id)

        await query.edit_message_text(
            "✅ تست با موفقیت حذف شد.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 مدیریت تست",
                        callback_data="admin_tests"
                    )
                ]
            ])
        )

        return

    # =========================
    # موجودی سرویس
    # =========================

    if data == "admin_stock":

        if user_id != ADMIN_ID:
            return

        await show_stock(query)
        return

    # =========================
    # آمار
    # =========================

    if data == "admin_stats":

        if user_id != ADMIN_ID:
            return

        await show_stats(query)
        return

    # =========================
    # سفارش‌ها
    # =========================

    if data == "admin_orders":

        if user_id != ADMIN_ID:
            return

        await show_orders(query)
        return

    # =========================
    # افزودن لینک سرویس
    # =========================

    if data == "admin_add":

        if user_id != ADMIN_ID:
            return

        context.user_data["admin_waiting_volume"] = True

        await query.edit_message_text(
            "➕ افزودن لینک ساب\n\n"
            "حجم لینک را به گیگ وارد کن.\n\n"
            "مثال:\n"
            "10\n"
            "20\n"
            "50\n"
            "یا حتی حجم دلخواه مثل 25"
        )

        return

    # =========================
    # حذف سرویس
    # =========================

    if data == "admin_delete":

        if user_id != ADMIN_ID:
            return

        await show_delete_menu(query)
        return

    # حذف لینک مشخص
    if data.startswith("delete_"):

        if user_id != ADMIN_ID:
            return

        subscription_id = int(
            data.split("_")[1]
        )

        delete_subscription(subscription_id)

        await query.edit_message_text(
            "✅ لینک با موفقیت حذف شد.",
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

    # =========================
    # تأیید سفارش
    # =========================

    if data.startswith("approve_"):

        if user_id != ADMIN_ID:
            return

        order_id = int(
            data.split("_")[1]
        )

        result = approve_order(order_id)

        if result["status"] == "not_found":

            await query.edit_message_caption(
                caption="❌ سفارش پیدا نشد."
            )

            return

        if result["status"] == "already_processed":

            status = result["order"]["status"]

            if status == "approved":
                message = "⚠️ این سفارش قبلاً تأیید شده است."

            elif status == "rejected":
                message = "⚠️ این سفارش قبلاً رد شده است."

            else:
                message = "⚠️ این سفارش قبلاً پردازش شده است."

            await query.answer(
                message,
                show_alert=True
            )

            return

        if result["status"] == "no_stock":

            await query.answer(
                "❌ برای این حجم لینک موجود نیست.",
                show_alert=True
            )

            await query.message.reply_text(
                f"⚠️ سفارش #{order_id}\n\n"
                "پرداخت هنوز تأیید نشده چون لینک این حجم موجود نیست.\n"
                "ابتدا لینک مناسب را از پنل مدیریت اضافه کن."
            )

            return

        order = result["order"]
        subscription_link = result["link"]

        await context.bot.send_message(
            chat_id=order["user_id"],
            text=(
                "✅ پرداخت شما تأیید شد.\n\n"
                "🌐 HanzuVPN\n\n"
                f"📦 حجم: {order['volume']} گیگ\n"
                "⏳ مدت: 30 روز\n"
                f"🧾 شماره سفارش: #{order_id}\n\n"
                "🔗 لینک Subscription:\n\n"
                f"{subscription_link}\n\n"
                "📌 لینک را در برنامه VPN خود وارد کنید."
            )
        )

        await query.edit_message_caption(
            caption=(
                f"✅ پرداخت سفارش #{order_id} تأیید شد.\n\n"
                f"📦 حجم: {order['volume']} گیگ\n"
                f"💰 مبلغ: {order['price']:,} تومان\n\n"
                "🔗 لینک برای مشتری ارسال شد."
            )
        )

        return

    # =========================
    # رد سفارش
    # =========================

    if data.startswith("reject_"):

        if user_id != ADMIN_ID:
            return

        order_id = int(
            data.split("_")[1]
        )

        changed, order = reject_order(order_id)

        if not order:

            await query.answer(
                "❌ سفارش پیدا نشد.",
                show_alert=True
            )

            return

        if not changed:

            await query.answer(
                "⚠️ این سفارش قبلاً پردازش شده است.",
                show_alert=True
            )

            return

        await context.bot.send_message(
            chat_id=order["user_id"],
            text=(
                "❌ پرداخت سفارش شما تأیید نشد.\n\n"
                f"🧾 شماره سفارش: #{order_id}\n\n"
                "در صورت اشتباه، لطفاً با پشتیبانی تماس بگیرید."
            )
        )

        await query.edit_message_caption(
            caption=(
                f"❌ سفارش #{order_id} رد شد.\n\n"
                f"📦 حجم: {order['volume']} گیگ\n"
                f"💰 مبلغ: {order['price']:,} تومان"
            )
        )

        return


# =========================
# پیام‌های متنی
# =========================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    text = update.message.text.strip()

    # =========================
    # افزودن لینک تست
    # =========================

    if (
        user.id == ADMIN_ID
        and context.user_data.get("admin_waiting_test_link")
    ):

        link = text

        if not (
            link.startswith("http://")
            or link.startswith("https://")
        ):

            await update.message.reply_text(
                "❌ لینک معتبر نیست.\n\n"
                "لینک باید با http:// یا https:// شروع شود."
            )

            return

        add_free_test(link)

        context.user_data.pop(
            "admin_waiting_test_link",
            None
        )

        stock = get_free_test_stock()

        await update.message.reply_text(
            "✅ لینک تست با موفقیت اضافه شد.\n\n"
            "📦 حجم: 100 مگابایت\n"
            "⏳ اعتبار: 1 روز\n\n"
            f"📊 موجودی تست: {stock} عدد"
        )

        return

    # =========================
    # حجم دلخواه مشتری
    # =========================

    if context.user_data.get("waiting_custom_volume"):

        context.user_data["waiting_custom_volume"] = False

        try:

            volume = int(text)

            if volume <= 0 or volume > 1000:
                raise ValueError

        except ValueError:

            await update.message.reply_text(
                "❌ حجم واردشده صحیح نیست.\n\n"
                "لطفاً یک عدد معتبر وارد کنید.\n"
                "مثلاً: 25"
            )

            return

        price = volume * PRICE_PER_GB

        keyboard = [
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
            ],
        ]

        await update.message.reply_text(
            "🛒 سرویس دلخواه شما\n\n"
            f"📦 حجم: {volume} گیگ\n"
            f"💰 قیمت: {price:,} تومان\n"
            "⏳ مدت: 30 روز\n\n"
            "برای ادامه روی «پرداخت کردم» بزنید.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return

    # =========================
    # حجم لینک برای ادمین
    # =========================

    if (
        user.id == ADMIN_ID
        and context.user_data.get("admin_waiting_volume")
    ):

        try:

            volume = int(text)

            if volume <= 0 or volume > 1000:
                raise ValueError

        except ValueError:

            await update.message.reply_text(
                "❌ حجم نامعتبر است.\n"
                "مثلاً 10 یا 20 یا 50 وارد کن."
            )

            return

        context.user_data["admin_waiting_volume"] = False
        context.user_data["admin_add_volume"] = str(volume)
        context.user_data["admin_waiting_link"] = True

        await update.message.reply_text(
            f"✅ حجم {volume} گیگ ثبت شد.\n\n"
            "حالا لینک Subscription را ارسال کن."
        )

        return

    # =========================
    # لینک جدید ادمین
    # =========================

    if (
        user.id == ADMIN_ID
        and context.user_data.get("admin_waiting_link")
    ):

        link = text

        if not (
            link.startswith("http://")
            or link.startswith("https://")
        ):

            await update.message.reply_text(
                "❌ لینک معتبر نیست.\n\n"
                "لینک باید با http:// یا https:// شروع شود."
            )

            return

        volume = context.user_data.get(
            "admin_add_volume"
        )

        add_subscription(
            volume,
            link
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
            "✅ لینک با موفقیت به موجودی اضافه شد.\n\n"
            f"📦 حجم: {volume} گیگ"
        )

        return


# =========================
# دریافت رسید
# =========================

async def receipt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    order = get_latest_pending_order(
        user.id
    )

    if not order:

        await update.message.reply_text(
            "❌ سفارش در انتظار پرداختی برای شما پیدا نشد.\n\n"
            "ابتدا از بخش خرید، سرویس موردنظر را انتخاب کنید."
        )

        return

    caption = (
        "💳 رسید پرداخت جدید\n\n"
        f"🧾 سفارش: #{order['id']}\n"
        f"👤 نام: {user.first_name or '-'}\n"
        f"👤 Username: @{user.username if user.username else '-'}\n"
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
            ),
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
        f"🧾 شماره سفارش: #{order['id']}\n\n"
        "رسید توسط مدیریت بررسی می‌شود و پس از تأیید، "
        "لینک سرویس برای شما ارسال خواهد شد."
    )


# =========================
# اجرای ربات
# =========================

def main():

    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN تنظیم نشده است."
        )

    init_db()

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
            button_handler
        )
    )

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            receipt_handler
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