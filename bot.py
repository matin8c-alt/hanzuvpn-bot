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
# ترجمه
# =========================================================

LANGUAGES = {
    "fa": "🇮🇷 فارسی",
    "ku": "🟢 کوردی",
    "en": "🇬🇧 English",
}


TEXTS = {

    "fa": {
        "language_title":
            "🌐 انتخاب زبان\n\nزبان موردنظر خود را انتخاب کنید:",

        "language_changed":
            "✅ زبان با موفقیت تغییر کرد.",

        "welcome":
            "🌐 HanzuVPN\n\n"
            "به ربات HanzuVPN خوش آمدید ❤️\n\n"
            "از منوی زیر انتخاب کنید:",

        "buy": "🛒 خرید سرویس",
        "trial": "🎁 تست رایگان",
        "services": "📦 سرویس‌های من",
        "renew": "🔄 تمدید",
        "coupon": "🎟 کد تخفیف",
        "referral": "👥 دعوت دوستان",
        "support": "🎫 پشتیبانی",
        "language": "🌐 تغییر زبان",
        "admin": "⚙️ پنل مدیریت",
        "back": "🔙 بازگشت",
        "main_menu": "🔙 منوی اصلی",

        "buy_title":
            "🛒 انتخاب سرویس\n\n"
            "⏳ مدت تمام سرویس‌ها: 30 روز\n\n"
            "حجم موردنظر خود را انتخاب کنید:",

        "custom":
            "✏️ حجم دلخواه",

        "trial_already":
            "⚠️ شما قبلاً تست رایگان خود را دریافت کرده‌اید.\n\n"
            "هر کاربر فقط یک‌بار می‌تواند از تست رایگان استفاده کند.",

        "trial_empty":
            "😔 در حال حاضر تست رایگان موجود نیست.\n\n"
            "لطفاً بعداً دوباره امتحان کنید.",

        "trial_success":
            "🎁 تست رایگان HanzuVPN\n\n"
            "📦 حجم: 100 مگابایت\n"
            "⏳ مدت: 1 روز\n\n"
            "🔗 لینک Subscription:\n\n"
            "{link}\n\n"
            "📌 لینک را در برنامه VPN خود وارد کنید.",

        "payment":
            "💳 اطلاعات پرداخت\n\n"
            "📦 حجم: {volume} گیگ\n"
            "💰 مبلغ: {price:,} تومان\n"
            "⏳ مدت: 30 روز\n",

        "original_price":
            "\n🏷 مبلغ اصلی: {original:,} تومان\n"
            "🎟 کد تخفیف: {coupon}\n",

        "card":
            "\n💳 شماره کارت:\n"
            "`{card}`\n\n"
            "بعد از انتقال مبلغ، روی «پرداخت کردم» بزنید "
            "و سپس تصویر رسید را ارسال کنید.",

        "paid": "💳 پرداخت کردم",

        "order_created":
            "✅ درخواست شما ثبت شد.\n\n"
            "🧾 سفارش: #{order}\n"
            "📦 حجم: {volume} گیگ\n"
            "💰 مبلغ: {price:,} تومان\n\n"
            "📸 حالا تصویر رسید را ارسال کنید.",

        "receipt_received":
            "✅ رسید شما دریافت شد.\n\n"
            "🧾 سفارش #{order}\n\n"
            "پس از بررسی توسط مدیریت، نتیجه برای شما ارسال می‌شود.",

        "no_pending":
            "❌ سفارش در انتظار پرداختی پیدا نشد.",

        "services_title":
            "📦 سرویس‌های شما\n\n",

        "no_services":
            "📦 سرویس‌های شما\n\n"
            "هنوز سرویس فعالی ندارید.",

        "service_item":
            "🧾 سفارش #{id}\n"
            "📦 حجم: {volume} گیگ\n"
            "⏳ انقضا: {expires}\n\n"
            "🔗 لینک:\n{link}\n\n"
            "━━━━━━━━━━━━\n\n",

        "renew_no_services":
            "🔄 تمدید سرویس\n\n"
            "شما سرویس فعالی ندارید.",

        "renew_choose":
            "🔄 تمدید سرویس\n\n"
            "سرویسی که می‌خواهید تمدید کنید را انتخاب کنید:",

        "renew_payment":
            "🔄 تمدید سرویس\n\n"
            "📦 حجم: {volume} گیگ\n"
            "💰 مبلغ تمدید: {price:,} تومان\n"
            "⏳ مدت: 30 روز\n\n"
            "برای پرداخت روی دکمه زیر بزنید.",

        "renew_paid":
            "💳 پرداخت تمدید\n\n"
            "📦 حجم: {volume} گیگ\n"
            "💰 مبلغ: {price:,} تومان\n"
            "⏳ مدت: 30 روز\n\n"
            "💳 شماره کارت:\n"
            "`{card}`\n\n"
            "بعد از پرداخت روی دکمه زیر بزنید.",

        "renew_created":
            "✅ درخواست تمدید ثبت شد.\n\n"
            "🧾 سفارش: #{order}\n"
            "📦 حجم: {volume} گیگ\n"
            "💰 مبلغ: {price:,} تومان\n\n"
            "📸 حالا تصویر رسید را ارسال کنید.",

        "custom_prompt":
            "✏️ حجم دلخواه\n\n"
            "حجم موردنظر را به گیگ وارد کن.\n\n"
            "مثال:\n25",

        "invalid_volume":
            "❌ حجم نامعتبر است.\n\nمثلاً 25 وارد کن.",

        "custom_summary":
            "🛒 سرویس دلخواه\n\n"
            "📦 حجم: {volume} گیگ\n"
            "💰 قیمت: {price:,} تومان\n"
            "⏳ مدت: 30 روز",

        "support_title":
            "🎫 پشتیبانی HanzuVPN\n\n"
            "برای ارسال پیام به پشتیبانی تیکت ایجاد کنید.",

        "create_ticket": "🎫 ایجاد تیکت",

        "ticket_prompt":
            "🎫 تیکت #{id}\n\n"
            "پیام خود را ارسال کنید.",

        "ticket_created":
            "✅ پیام شما در تیکت #{id} ثبت شد.\n\n"
            "پشتیبانی آن را بررسی می‌کند.",

        "ticket_closed":
            "🔒 تیکت #{id} بسته شد.\n\n"
            "در صورت نیاز می‌توانید تیکت جدید ایجاد کنید.",

        "referral_title":
            "👥 دعوت دوستان\n\n"
            "👤 تعداد دعوت‌ها: {count}\n\n"
            "لینک اختصاصی شما:\n"
            "{link}\n\n"
            "لینک را برای دوستانت بفرست.",

        "referral_error":
            "❌ خطا در ساخت لینک دعوت.",

        "coupon_prompt":
            "🎟 کد تخفیف\n\n"
            "کد تخفیف خود را ارسال کنید.",

        "coupon_invalid":
            "❌ کد تخفیف نامعتبر است.",

        "coupon_used":
            "⚠️ شما قبلاً از این کد استفاده کرده‌اید.",

        "coupon_valid":
            "✅ کد تخفیف معتبر است.\n\n"
            "🎟 کد: {code}\n"
            "💰 تخفیف: {percent}%\n\n"
            "حالا سرویس موردنظر را انتخاب کنید:",

        "help":
            "📚 راهنمای HanzuVPN\n\n"
            "/start - منوی اصلی\n"
            "/buy - خرید سرویس\n"
            "/services - سرویس‌های من\n"
            "/trial - تست رایگان\n"
            "/support - پشتیبانی\n"
            "/help - راهنما\n\n"
            "تمام امکانات از طریق منوی اصلی نیز قابل استفاده هستند.",

        "payment_confirmed":
            "✅ پرداخت شما تأیید شد.\n\n"
            "🌐 HanzuVPN\n\n"
            "📦 حجم: {volume} گیگ\n"
            "⏳ مدت: 30 روز\n"
            "📅 انقضا: {expires}\n"
            "🧾 سفارش: #{order}\n\n"
            "🔗 لینک Subscription:\n\n"
            "{link}\n\n"
            "📌 لینک را در برنامه VPN خود وارد کنید.",

        "payment_rejected":
            "❌ پرداخت سفارش شما تأیید نشد.\n\n"
            "🧾 سفارش: #{order}\n\n"
            "در صورت اشتباه با پشتیبانی تماس بگیرید.",

        "reminder_3":
            "⚠️ یادآوری HanzuVPN\n\n"
            "سرویس #{order} شما حدود 3 روز دیگر منقضی می‌شود.\n\n"
            "برای تمدید از بخش «🔄 تمدید» استفاده کنید.",

        "reminder_1":
            "⏰ یادآوری HanzuVPN\n\n"
            "سرویس #{order} شما حدود 1 روز دیگر منقضی می‌شود.\n\n"
            "برای تمدید سرویس اقدام کنید.",

        "select_language":
            "🌐 زبان / زمان\n\n"
            "زبان موردنظر خود را انتخاب کنید:",
    },


    "ku": {
        "language_title":
            "🌐 هەڵبژاردنی زمان\n\n"
            "تکایە زمانی خۆت هەڵبژێرە:",

        "language_changed":
            "✅ زمان بە سەرکەوتوویی گۆڕدرا.",

        "welcome":
            "🌐 HanzuVPN\n\n"
            "بەخێربێیت بۆ HanzuVPN ❤️\n\n"
            "لە خوارەوە هەڵبژاردەیەک هەڵبژێرە:",

        "buy": "🛒 کڕینی خزمەتگوزاری",
        "trial": "🎁 تاقیکردنەوەی بەخۆڕایی",
        "services": "📦 خزمەتگوزارییەکانم",
        "renew": "🔄 نوێکردنەوە",
        "coupon": "🎟 کۆدی داشکان",
        "referral": "👥 بانگهێشتکردنی هاوڕێکان",
        "support": "🎫 پشتگیری",
        "language": "🌐 گۆڕینی زمان",
        "admin": "⚙️ بەڕێوەبردن",
        "back": "🔙 گەڕانەوە",
        "main_menu": "🔙 پەڕەی سەرەکی",

        "buy_title":
            "🛒 هەڵبژاردنی خزمەتگوزاری\n\n"
            "⏳ ماوەی هەموو خزمەتگوزارییەکان: 30 ڕۆژ\n\n"
            "قەبارەی خۆت هەڵبژێرە:",

        "custom": "✏️ قەبارەی دڵخواز",

        "trial_already":
            "⚠️ پێشتر تاقیکردنەوەی بەخۆڕاییت وەرگرتووە.\n\n"
            "هەر بەکارهێنەرێک تەنها جارێک دەتوانێت تاقیکردنەوە وەربگرێت.",

        "trial_empty":
            "😔 لە ئێستادا تاقیکردنەوەی بەخۆڕایی بەردەست نییە.\n\n"
            "تکایە دواتر هەوڵ بدەوە.",

        "trial_success":
            "🎁 تاقیکردنەوەی بەخۆڕایی HanzuVPN\n\n"
            "📦 قەبارە: 100 مێگابایت\n"
            "⏳ ماوە: 1 ڕۆژ\n\n"
            "🔗 بەستەری Subscription:\n\n"
            "{link}\n\n"
            "📌 بەستەرەکە لە بەرنامەی VPN ـەکەت دابنێ.",

        "payment":
            "💳 زانیاری پارەدان\n\n"
            "📦 قەبارە: {volume} گیگ\n"
            "💰 بڕی پارە: {price:,} تومان\n"
            "⏳ ماوە: 30 ڕۆژ\n",

        "original_price":
            "\n🏷 بڕی سەرەکی: {original:,} تومان\n"
            "🎟 کۆدی داشکان: {coupon}\n",

        "card":
            "\n💳 ژمارەی کارت:\n"
            "`{card}`\n\n"
            "دوای ناردنی پارە، «پارەم داوە» هەڵبژێرە "
            "و پاشان وێنەی پسوڵەکە بنێرە.",

        "paid": "💳 پارەم داوە",

        "order_created":
            "✅ داواکارییەکەت تۆمار کرا.\n\n"
            "🧾 داواکاری: #{order}\n"
            "📦 قەبارە: {volume} گیگ\n"
            "💰 بڕ: {price:,} تومان\n\n"
            "📸 ئێستا وێنەی پسوڵەکە بنێرە.",

        "receipt_received":
            "✅ پسوڵەکەت وەرگیرا.\n\n"
            "🧾 داواکاری #{order}\n\n"
            "دوای پشکنینی بەڕێوەبەرایەتی ئەنجامەکە بۆت دەنێردرێت.",

        "no_pending":
            "❌ هیچ داواکارییەکی چاوەڕوانی پارەدان نەدۆزرایەوە.",

        "services_title":
            "📦 خزمەتگوزارییەکانت\n\n",

        "no_services":
            "📦 خزمەتگوزارییەکانت\n\n"
            "هێشتا هیچ خزمەتگوزارییەکی چالاکت نییە.",

        "service_item":
            "🧾 داواکاری #{id}\n"
            "📦 قەبارە: {volume} گیگ\n"
            "⏳ بەسەرچوون: {expires}\n\n"
            "🔗 بەستەر:\n{link}\n\n"
            "━━━━━━━━━━━━\n\n",

        "renew_no_services":
            "🔄 نوێکردنەوەی خزمەتگوزاری\n\n"
            "هیچ خزمەتگوزارییەکی چالاکت نییە.",

        "renew_choose":
            "🔄 نوێکردنەوەی خزمەتگوزاری\n\n"
            "ئەو خزمەتگوزارییە هەڵبژێرە کە دەتەوێت نوێی بکەیتەوە:",

        "renew_payment":
            "🔄 نوێکردنەوەی خزمەتگوزاری\n\n"
            "📦 قەبارە: {volume} گیگ\n"
            "💰 بڕی نوێکردنەوە: {price:,} تومان\n"
            "⏳ ماوە: 30 ڕۆژ\n\n"
            "بۆ پارەدان دوگمەی خوارەوە هەڵبژێرە.",

        "renew_paid":
            "💳 پارەدانی نوێکردنەوە\n\n"
            "📦 قەبارە: {volume} گیگ\n"
            "💰 بڕ: {price:,} تومان\n"
            "⏳ ماوە: 30 ڕۆژ\n\n"
            "💳 ژمارەی کارت:\n"
            "`{card}`\n\n"
            "دوای پارەدان دوگمەی خوارەوە هەڵبژێرە.",

        "renew_created":
            "✅ داواکاریی نوێکردنەوە تۆمار کرا.\n\n"
            "🧾 داواکاری: #{order}\n"
            "📦 قەبارە: {volume} گیگ\n"
            "💰 بڕ: {price:,} تومان\n\n"
            "📸 ئێستا وێنەی پسوڵەکە بنێرە.",

        "custom_prompt":
            "✏️ قەبارەی دڵخواز\n\n"
            "قەبارەکە بە گیگ بنووسە.\n\n"
            "نموونە:\n25",

        "invalid_volume":
            "❌ قەبارە نادروستە.\n\nنموونە 25 بنووسە.",

        "custom_summary":
            "🛒 خزمەتگوزاریی دڵخواز\n\n"
            "📦 قەبارە: {volume} گیگ\n"
            "💰 نرخ: {price:,} تومان\n"
            "⏳ ماوە: 30 ڕۆژ",

        "support_title":
            "🎫 پشتگیری HanzuVPN\n\n"
            "بۆ پەیوەندی لەگەڵ پشتگیری تیکەت دروست بکە.",

        "create_ticket": "🎫 دروستکردنی تیکەت",

        "ticket_prompt":
            "🎫 تیکەتی #{id}\n\n"
            "نامەکەت بنێرە.",

        "ticket_created":
            "✅ نامەکەت لە تیکەتی #{id} تۆمار کرا.\n\n"
            "پشتگیری پشکنینی دەکات.",

        "ticket_closed":
            "🔒 تیکەتی #{id} داخرا.\n\n"
            "ئەگەر پێویست بوو دەتوانیت تیکەتی نوێ دروست بکەیت.",

        "referral_title":
            "👥 بانگهێشتکردنی هاوڕێکان\n\n"
            "👤 ژمارەی بانگهێشتەکان: {count}\n\n"
            "بەستەری تایبەتی تۆ:\n"
            "{link}\n\n"
            "بەستەرەکە بۆ هاوڕێکانت بنێرە.",

        "referral_error":
            "❌ هەڵە لە دروستکردنی بەستەری بانگهێشت.",

        "coupon_prompt":
            "🎟 کۆدی داشکان\n\n"
            "کۆدی داشکانەکەت بنێرە.",

        "coupon_invalid":
            "❌ کۆدی داشکان نادروستە.",

        "coupon_used":
            "⚠️ پێشتر ئەم کۆدە بەکارهێناوە.",

        "coupon_valid":
            "✅ کۆدی داشکان دروستە.\n\n"
            "🎟 کۆد: {code}\n"
            "💰 داشکان: {percent}%\n\n"
            "ئێستا خزمەتگوزارییەکە هەڵبژێرە:",

        "help":
            "📚 ڕێنمایی HanzuVPN\n\n"
            "/start - پەڕەی سەرەکی\n"
            "/buy - کڕینی خزمەتگوزاری\n"
            "/services - خزمەتگوزارییەکانم\n"
            "/trial - تاقیکردنەوە\n"
            "/support - پشتگیری\n"
            "/help - ڕێنمایی",

        "payment_confirmed":
            "✅ پارەدانەکەت پشتڕاست کرایەوە.\n\n"
            "🌐 HanzuVPN\n\n"
            "📦 قەبارە: {volume} گیگ\n"
            "⏳ ماوە: 30 ڕۆژ\n"
            "📅 بەسەرچوون: {expires}\n"
            "🧾 داواکاری: #{order}\n\n"
            "🔗 بەستەری Subscription:\n\n"
            "{link}\n\n"
            "📌 بەستەرەکە لە بەرنامەی VPN ـەکەت دابنێ.",

        "payment_rejected":
            "❌ پارەدانی داواکارییەکەت پشتڕاست نەکرایەوە.\n\n"
            "🧾 داواکاری: #{order}\n\n"
            "ئەگەر هەڵەیەک هەیە لەگەڵ پشتگیری پەیوەندی بکە.",

        "reminder_3":
            "⚠️ بیرخستنەوەی HanzuVPN\n\n"
            "خزمەتگوزاری #{order} ـەکەت نزیکەی 3 ڕۆژی تر بەسەر دەچێت.\n\n"
            "بۆ نوێکردنەوە بەشی «🔄 نوێکردنەوە» بەکاربهێنە.",

        "reminder_1":
            "⏰ بیرخستنەوەی HanzuVPN\n\n"
            "خزمەتگوزاری #{order} ـەکەت نزیکەی 1 ڕۆژی تر بەسەر دەچێت.\n\n"
            "بۆ نوێکردنەوەی خزمەتگوزاری هەنگاو بنێ.",

        "select_language":
            "🌐 زمان\n\n"
            "تکایە زمانی خۆت هەڵبژێرە:",
    },


    "en": {
        "language_title":
            "🌐 Choose Language\n\nPlease select your language:",

        "language_changed":
            "✅ Language changed successfully.",

        "welcome":
            "🌐 HanzuVPN\n\n"
            "Welcome to HanzuVPN ❤️\n\n"
            "Choose an option below:",

        "buy": "🛒 Buy Service",
        "trial": "🎁 Free Trial",
        "services": "📦 My Services",
        "renew": "🔄 Renew",
        "coupon": "🎟 Coupon",
        "referral": "👥 Invite Friends",
        "support": "🎫 Support",
        "language": "🌐 Change Language",
        "admin": "⚙️ Admin Panel",
        "back": "🔙 Back",
        "main_menu": "🔙 Main Menu",

        "buy_title":
            "🛒 Choose a Service\n\n"
            "⏳ All services are valid for 30 days.\n\n"
            "Choose your desired volume:",

        "custom": "✏️ Custom Volume",

        "trial_already":
            "⚠️ You have already received your free trial.\n\n"
            "Each user can receive the free trial only once.",

        "trial_empty":
            "😔 No free trials are currently available.\n\n"
            "Please try again later.",

        "trial_success":
            "🎁 HanzuVPN Free Trial\n\n"
            "📦 Volume: 100 MB\n"
            "⏳ Duration: 1 day\n\n"
            "🔗 Subscription link:\n\n"
            "{link}\n\n"
            "📌 Add this link to your VPN application.",

        "payment":
            "💳 Payment Information\n\n"
            "📦 Volume: {volume} GB\n"
            "💰 Price: {price:,} Toman\n"
            "⏳ Duration: 30 days\n",

        "original_price":
            "\n🏷 Original price: {original:,} Toman\n"
            "🎟 Coupon: {coupon}\n",

        "card":
            "\n💳 Card number:\n"
            "`{card}`\n\n"
            "After transferring the money, tap "
            "«I Paid» and send the payment receipt.",

        "paid": "💳 I Paid",

        "order_created":
            "✅ Your request has been registered.\n\n"
            "🧾 Order: #{order}\n"
            "📦 Volume: {volume} GB\n"
            "💰 Price: {price:,} Toman\n\n"
            "📸 Now send the payment receipt.",

        "receipt_received":
            "✅ Your receipt has been received.\n\n"
            "🧾 Order #{order}\n\n"
            "The result will be sent after admin review.",

        "no_pending":
            "❌ No pending payment order was found.",

        "services_title":
            "📦 Your Services\n\n",

        "no_services":
            "📦 Your Services\n\n"
            "You don't have any active services yet.",

        "service_item":
            "🧾 Order #{id}\n"
            "📦 Volume: {volume} GB\n"
            "⏳ Expires: {expires}\n\n"
            "🔗 Link:\n{link}\n\n"
            "━━━━━━━━━━━━\n\n",

        "renew_no_services":
            "🔄 Renew Service\n\n"
            "You don't have any active services.",

        "renew_choose":
            "🔄 Renew Service\n\n"
            "Choose the service you want to renew:",

        "renew_payment":
            "🔄 Renew Service\n\n"
            "📦 Volume: {volume} GB\n"
            "💰 Renewal price: {price:,} Toman\n"
            "⏳ Duration: 30 days\n\n"
            "Tap the button below to pay.",

        "renew_paid":
            "💳 Renewal Payment\n\n"
            "📦 Volume: {volume} GB\n"
            "💰 Price: {price:,} Toman\n"
            "⏳ Duration: 30 days\n\n"
            "💳 Card number:\n"
            "`{card}`\n\n"
            "After payment, tap the button below.",

        "renew_created":
            "✅ Renewal request registered.\n\n"
            "🧾 Order: #{order}\n"
            "📦 Volume: {volume} GB\n"
            "💰 Price: {price:,} Toman\n\n"
            "📸 Now send the payment receipt.",

        "custom_prompt":
            "✏️ Custom Volume\n\n"
            "Enter the desired volume in GB.\n\n"
            "Example:\n25",

        "invalid_volume":
            "❌ Invalid volume.\n\nPlease enter something like 25.",

        "custom_summary":
            "🛒 Custom Service\n\n"
            "📦 Volume: {volume} GB\n"
            "💰 Price: {price:,} Toman\n"
            "⏳ Duration: 30 days",

        "support_title":
            "🎫 HanzuVPN Support\n\n"
            "Create a ticket to contact support.",

        "create_ticket": "🎫 Create Ticket",

        "ticket_prompt":
            "🎫 Ticket #{id}\n\n"
            "Send your message.",

        "ticket_created":
            "✅ Your message was added to ticket #{id}.\n\n"
            "Support will review it.",

        "ticket_closed":
            "🔒 Ticket #{id} has been closed.\n\n"
            "You can create a new ticket if needed.",

        "referral_title":
            "👥 Invite Friends\n\n"
            "👤 Referrals: {count}\n\n"
            "Your personal link:\n"
            "{link}\n\n"
            "Send this link to your friends.",

        "referral_error":
            "❌ Error creating referral link.",

        "coupon_prompt":
            "🎟 Coupon\n\n"
            "Send your coupon code.",

        "coupon_invalid":
            "❌ Invalid coupon code.",

        "coupon_used":
            "⚠️ You have already used this coupon.",

        "coupon_valid":
            "✅ Coupon is valid.\n\n"
            "🎟 Code: {code}\n"
            "💰 Discount: {percent}%\n\n"
            "Now choose your service:",

        "help":
            "📚 HanzuVPN Help\n\n"
            "/start - Main menu\n"
            "/buy - Buy service\n"
            "/services - My services\n"
            "/trial - Free trial\n"
            "/support - Support\n"
            "/help - Help\n\n"
            "All features are also available from the main menu.",

        "payment_confirmed":
            "✅ Your payment has been approved.\n\n"
            "🌐 HanzuVPN\n\n"
            "📦 Volume: {volume} GB\n"
            "⏳ Duration: 30 days\n"
            "📅 Expires: {expires}\n"
            "🧾 Order: #{order}\n\n"
            "🔗 Subscription link:\n\n"
            "{link}\n\n"
            "📌 Add this link to your VPN application.",

        "payment_rejected":
            "❌ Your payment was not approved.\n\n"
            "🧾 Order: #{order}\n\n"
            "Please contact support if you think this is an error.",

        "reminder_3":
            "⚠️ HanzuVPN Reminder\n\n"
            "Your service #{order} expires in about 3 days.\n\n"
            "Use «🔄 Renew» to renew it.",

        "reminder_1":
            "⏰ HanzuVPN Reminder\n\n"
            "Your service #{order} expires in about 1 day.\n\n"
            "Please renew your service.",

        "select_language":
            "🌐 Language\n\n"
            "Please select your language:",
    }
}


def t(lang, key, **kwargs):
    if lang not in TEXTS:
        lang = "fa"

    text = TEXTS[lang].get(
        key,
        TEXTS["fa"].get(key, key)
    )

    try:
        return text.format(**kwargs)
    except Exception:
        return text


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
            created_at,
            language
        )
        VALUES (?, ?, ?, ?, NULL)
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


def get_user_language(user_id):
    if user_id == ADMIN_ID:
        return "fa"

    conn = get_db()

    row = conn.execute("""
        SELECT language
        FROM users
        WHERE user_id = ?
    """, (user_id,)).fetchone()

    conn.close()

    if row and row["language"] in LANGUAGES:
        return row["language"]

    return None


def set_user_language(user_id, language):
    if language not in LANGUAGES:
        return

    conn = get_db()

    conn.execute("""
        UPDATE users
        SET language = ?
        WHERE user_id = ?
    """, (
        language,
        user_id
    ))

    conn.commit()
    conn.close()


def language_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🇮🇷 فارسی",
                callback_data="lang_fa"
            )
        ],
        [
            InlineKeyboardButton(
                "🟢 کوردی",
                callback_data="lang_ku"
            )
        ],
        [
            InlineKeyboardButton(
                "🇬🇧 English",
                callback_data="lang_en"
            )
        ]
    ])


async def show_language_selector_message(message):
    await message.reply_text(
        TEXTS["fa"]["language_title"],
        reply_markup=language_keyboard()
    )


def clear_user_states(context):
    """پاک کردن stateهای موقت کاربر"""
    keys_to_remove = [
        "waiting_custom_volume",
        "waiting_coupon",
        "waiting_ticket_message",
        "ticket_id",
        "custom_volume",
        "custom_price",
        "coupon_code",
        "renew_order_id",
        "renew_payment",
        "admin_waiting_volume",
        "admin_waiting_link",
        "admin_add_volume",
        "admin_waiting_trial_link",
        "admin_waiting_coupon",
        "admin_broadcast",
        "admin_ticket_id",
        "admin_waiting_ticket_reply",
        "last_order_id",
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)


# =========================================================
# دیتابیس
# =========================================================

def init_db():

    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            volume TEXT NOT NULL,
            link TEXT NOT NULL,
            used INTEGER DEFAULT 0
        )
    """)

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

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            created_at TEXT NOT NULL,
            referred_by INTEGER,
            referral_rewarded INTEGER DEFAULT 0,
            language TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS free_trials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link TEXT NOT NULL,
            used INTEGER DEFAULT 0
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS free_trial_users (
            user_id INTEGER PRIMARY KEY,
            trial_id INTEGER,
            claimed_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )
    """)

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

    # سازگاری دیتابیس قبلی
    try:
        conn.execute("ALTER TABLE orders ADD COLUMN expires_at TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER")
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("ALTER TABLE users ADD COLUMN referral_rewarded INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("ALTER TABLE users ADD COLUMN language TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


# =========================================================
# منوی اصلی
# =========================================================

def home_keyboard(user_id):

    lang = get_user_language(user_id) or "fa"

    keyboard = [
        [
            InlineKeyboardButton(
                t(lang, "buy"),
                callback_data="buy"
            )
        ],
        [
            InlineKeyboardButton(
                t(lang, "trial"),
                callback_data="trial"
            )
        ],
        [
            InlineKeyboardButton(
                t(lang, "services"),
                callback_data="my_services"
            ),
            InlineKeyboardButton(
                t(lang, "renew"),
                callback_data="renew"
            ),
        ],
        [
            InlineKeyboardButton(
                t(lang, "coupon"),
                callback_data="coupon"
            ),
            InlineKeyboardButton(
                t(lang, "referral"),
                callback_data="referral"
            ),
        ],
        [
            InlineKeyboardButton(
                t(lang, "support"),
                callback_data="support"
            ),
        ],
        [
            InlineKeyboardButton(
                t(lang, "language"),
                callback_data="language"
            )
        ]
    ]

    if user_id == ADMIN_ID:
        keyboard.append([
            InlineKeyboardButton(
                t("fa", "admin"),
                callback_data="admin"
            )
        ])

    return InlineKeyboardMarkup(keyboard)


async def show_home(query, user_id):

    lang = get_user_language(user_id) or "fa"

    await query.edit_message_text(
        t(lang, "welcome"),
        reply_markup=home_keyboard(user_id)
    )


async def send_home(message, user_id):

    lang = get_user_language(user_id) or "fa"

    await message.reply_text(
        t(lang, "welcome"),
        reply_markup=home_keyboard(user_id)
    )


# =========================================================
# دستورات
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    ensure_user(user)
    clear_user_states(context)

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

    lang = get_user_language(user.id)

    if not lang and user.id != ADMIN_ID:

        await show_language_selector_message(
            update.message
        )

        return

    if user.id == ADMIN_ID:
        set_user_language(user.id, "fa")

    await send_home(
        update.message,
        user.id
    )


async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    ensure_user(user)
    clear_user_states(context)

    if not get_user_language(user.id):
        await show_language_selector_message(update.message)
        return

    await send_buy_message(update.message)


async def services_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    ensure_user(user)
    clear_user_states(context)

    if not get_user_language(user.id):
        await show_language_selector_message(update.message)
        return

    await send_services_message(
        update.message,
        user.id
    )


async def trial_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    ensure_user(user)
    clear_user_states(context)

    lang = get_user_language(user.id)

    if not lang:
        await show_language_selector_message(update.message)
        return

    result = claim_trial(user)

    if result["status"] == "already":

        await update.message.reply_text(
            t(lang, "trial_already")
        )

        return

    if result["status"] == "empty":

        await update.message.reply_text(
            t(lang, "trial_empty")
        )

        return

    await update.message.reply_text(
        t(
            lang,
            "trial_success",
            link=result["link"]
        )
    )


async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    ensure_user(user)
    clear_user_states(context)

    lang = get_user_language(user.id)

    if not lang:
        await show_language_selector_message(update.message)
        return

    await update.message.reply_text(
        t(lang, "support_title"),
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    t(lang, "create_ticket"),
                    callback_data="new_ticket"
                )
            ],
            [
                InlineKeyboardButton(
                    t(lang, "main_menu"),
                    callback_data="home"
                )
            ]
        ])
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    ensure_user(user)

    lang = get_user_language(user.id)

    if not lang:
        await show_language_selector_message(update.message)
        return

    await update.message.reply_text(
        t(lang, "help")
    )


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    ensure_user(user)

    await show_language_selector_message(
        update.message
    )


# =========================================================
# دستورات تلگرام
# =========================================================

async def set_bot_commands(application):

    commands = [
        BotCommand("start", "Start / شروع"),
        BotCommand("buy", "Buy Service / خرید سرویس"),
        BotCommand("services", "My Services / سرویس‌های من"),
        BotCommand("trial", "Free Trial / تست رایگان"),
        BotCommand("support", "Support / پشتیبانی"),
        BotCommand("language", "Change Language / تغییر زبان"),
        BotCommand("help", "Help / راهنما"),
    ]

    await application.bot.set_my_commands(commands)


# =========================================================
# خرید
# =========================================================

def buy_keyboard(user_id):

    lang = get_user_language(user_id) or "fa"

    if lang == "en":
        buttons = [
            ("10 GB | 35,000 Toman", "plan_10"),
            ("20 GB | 70,000 Toman", "plan_20"),
            ("30 GB | 105,000 Toman", "plan_30"),
            ("40 GB | 140,000 Toman", "plan_40"),
            ("50 GB | 175,000 Toman", "plan_50"),
        ]
    elif lang == "ku":
        buttons = [
            ("10 گیگ | 35,000 تومان", "plan_10"),
            ("20 گیگ | 70,000 تومان", "plan_20"),
            ("30 گیگ | 105,000 تومان", "plan_30"),
            ("40 گیگ | 140,000 تومان", "plan_40"),
            ("50 گیگ | 175,000 تومان", "plan_50"),
        ]
    else:  # fa
        buttons = [
            ("10 گیگ | 35,000 تومان", "plan_10"),
            ("20 گیگ | 70,000 تومان", "plan_20"),
            ("30 گیگ | 105,000 تومان", "plan_30"),
            ("40 گیگ | 140,000 تومان", "plan_40"),
            ("50 گیگ | 175,000 تومان", "plan_50"),
        ]

    keyboard = [
        [InlineKeyboardButton(text, callback_data=cb)]
        for text, cb in buttons
    ]

    keyboard.append([
        InlineKeyboardButton(
            t(lang, "custom"),
            callback_data="custom"
        )
    ])
    keyboard.append([
        InlineKeyboardButton(
            t(lang, "back"),
            callback_data="home"
        )
    ])

    return InlineKeyboardMarkup(keyboard)


async def send_buy_message(message):

    user_id = message.from_user.id
    lang = get_user_language(user_id) or "fa"

    await message.reply_text(
        t(lang, "buy_title"),
        reply_markup=buy_keyboard(user_id)
    )


async def show_buy_menu(query):

    lang = get_user_language(query.from_user.id) or "fa"

    await query.edit_message_text(
        t(lang, "buy_title"),
        reply_markup=buy_keyboard(query.from_user.id)
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

    user_id = query.from_user.id
    lang = get_user_language(user_id) or "fa"

    if original_price is None:
        original_price = price

    caption = t(
        lang,
        "payment",
        volume=volume,
        price=price
    )

    if original_price != price and coupon_code:

        caption += t(
            lang,
            "original_price",
            original=original_price,
            coupon=coupon_code
        )

    caption += t(
        lang,
        "card",
        card=CARD_NUMBER
    )

    # فقط volume رو در callback می‌ذاریم (قیمت دوباره محاسبه می‌شه)
    keyboard = [
        [
            InlineKeyboardButton(
                t(lang, "paid"),
                callback_data=f"paid_{volume}"
            )
        ],
        [
            InlineKeyboardButton(
                t(lang, "back"),
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

            return {"status": "already"}

        trial = conn.execute("""
            SELECT id, link
            FROM free_trials
            WHERE used = 0
            ORDER BY id
            LIMIT 1
        """).fetchone()

        if not trial:

            conn.rollback()

            return {"status": "empty"}

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
            claimed_at.strftime("%Y-%m-%d %H:%M:%S"),
            expires_at.strftime("%Y-%m-%d %H:%M:%S"),
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

def cancel_pending_orders(user_id):
    """لغو تمام سفارش‌های pending قبلی کاربر"""
    conn = get_db()
    conn.execute("""
        UPDATE orders
        SET status = 'cancelled'
        WHERE user_id = ?
        AND status = 'pending'
    """, (user_id,))
    conn.commit()
    conn.close()


def create_order(user, volume, price, coupon_code=None):

    # لغو سفارش‌های pending قبلی
    cancel_pending_orders(user.id)

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

    # ثبت استفاده از کوپن (اگر وجود داشته باشد)
    if coupon_code:
        coupon = get_coupon(coupon_code)
        if coupon:
            try:
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
                    coupon["id"],
                    user.id,
                    order_id,
                    now_text()
                ))

                conn.execute("""
                    UPDATE coupons
                    SET used_count = used_count + 1
                    WHERE id = ?
                """, (coupon["id"],))
            except Exception:
                pass

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
            return {"status": "not_found"}

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
            approved_at.strftime("%Y-%m-%d %H:%M:%S"),
            expires_at.strftime("%Y-%m-%d %H:%M:%S"),
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

    lang = get_user_language(user_id) or "fa"

    rows = get_user_services(user_id)

    if not rows:

        text = t(lang, "no_services")

    else:

        text = t(lang, "services_title")

        for row in rows:

            text += t(
                lang,
                "service_item",
                id=row["id"],
                volume=row["volume"],
                expires=row["expires_at"] or "-",
                link=row["link"]
            )

    await message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    t(lang, "renew"),
                    callback_data="renew"
                )
            ],
            [
                InlineKeyboardButton(
                    t(lang, "main_menu"),
                    callback_data="home"
                )
            ]
        ])
    )


# =========================================================
# تمدید
# =========================================================

async def show_renew(query):

    user_id = query.from_user.id
    lang = get_user_language(user_id) or "fa"

    rows = get_user_services(user_id)

    if not rows:

        await query.edit_message_text(
            t(lang, "renew_no_services"),
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        t(lang, "buy"),
                        callback_data="buy"
                    )
                ],
                [
                    InlineKeyboardButton(
                        t(lang, "back"),
                        callback_data="home"
                    )
                ]
            ])
        )

        return

    keyboard = []

    for row in rows[:10]:

        label = (
            f"🔄 Renew #{row['id']} | {row['volume']} GB"
            if lang == "en"
            else f"🔄 تمدید #{row['id']} | {row['volume']} گیگ"
        )

        keyboard.append([
            InlineKeyboardButton(
                label,
                callback_data=f"renew_{row['id']}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            t(lang, "back"),
            callback_data="home"
        )
    ])

    await query.edit_message_text(
        t(lang, "renew_choose"),
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
        return {"status": "invalid"}

    if user_used_coupon(coupon["id"], user_id):
        return {"status": "used"}

    if (
        coupon["max_uses"] > 0
        and coupon["used_count"] >= coupon["max_uses"]
    ):
        return {"status": "full"}

    new_price = int(
        price * (100 - coupon["percent"]) / 100
    )

    return {
        "status": "success",
        "coupon": coupon,
        "price": max(new_price, 0)  # جلوگیری از قیمت منفی
    }


# =========================================================
# دعوت
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

    return f"https://t.me/{bot_username}?start={user_id}"


# =========================================================
# تیکت
# =========================================================

def create_ticket(user_id, subject="Support"):

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


def add_ticket_message(ticket_id, sender_id, message):

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

    total_users = conn.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]

    total_orders = conn.execute(
        "SELECT COUNT(*) FROM orders"
    ).fetchone()[0]

    approved = conn.execute(
        "SELECT COUNT(*) FROM orders WHERE status='approved'"
    ).fetchone()[0]

    pending = conn.execute(
        "SELECT COUNT(*) FROM orders WHERE status='pending'"
    ).fetchone()[0]

    rejected = conn.execute(
        "SELECT COUNT(*) FROM orders WHERE status='rejected'"
    ).fetchone()[0]

    sales = conn.execute(
        "SELECT COALESCE(SUM(price),0) FROM orders WHERE status='approved'"
    ).fetchone()[0]

    trials = conn.execute(
        "SELECT COUNT(*) FROM free_trial_users"
    ).fetchone()[0]

    referrals = conn.execute(
        "SELECT COUNT(*) FROM users WHERE referred_by IS NOT NULL"
    ).fetchone()[0]

    open_tickets = conn.execute(
        "SELECT COUNT(*) FROM tickets WHERE status='open'"
    ).fetchone()[0]

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

            text += f"🔹 {volume} گیگ: {count} عدد\n"

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
                "rejected": "❌ رد",
                "cancelled": "🚫 لغو شده"
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

    # =====================================================
    # زبان
    # =====================================================

    if data == "language":

        await query.edit_message_text(
            TEXTS["fa"]["language_title"],
            reply_markup=language_keyboard()
        )

        return

    if data.startswith("lang_"):

        language = data.split("_", 1)[1]

        if language not in LANGUAGES:
            return

        set_user_language(
            user_id,
            language
        )

        clear_user_states(context)

        await query.edit_message_text(
            t(language, "language_changed") +
            "\n\n" +
            t(language, "welcome"),
            reply_markup=home_keyboard(user_id)
        )

        return

    # اگر زبان انتخاب نشده
    lang = get_user_language(user_id)

    if not lang and user_id != ADMIN_ID:

        await query.edit_message_text(
            TEXTS["fa"]["language_title"],
            reply_markup=language_keyboard()
        )

        return

    if user_id == ADMIN_ID:
        lang = "fa"

    # =====================================================
    # خانه
    # =====================================================

    if data == "home":

        clear_user_states(context)
        await show_home(
            query,
            user_id
        )

        return

    # =====================================================
    # خرید
    # =====================================================

    if data == "buy":

        clear_user_states(context)
        await show_buy_menu(query)

        return

    # =====================================================
    # پلن
    # =====================================================

    if data.startswith("plan_"):

        volume = data.split("_")[1]
        base_price = PLANS.get(volume)

        if not base_price:
            return

        # بررسی کوپن
        coupon_code = context.user_data.get("coupon_code")
        price = base_price
        original_price = base_price

        if coupon_code:

            result = apply_coupon(
                coupon_code,
                user_id,
                base_price
            )

            if result["status"] == "success":
                price = result["price"]
            else:
                # کوپن نامعتبر شد → پاکش کن
                context.user_data.pop("coupon_code", None)
                coupon_code = None

        await show_payment(
            query,
            volume,
            price,
            original_price,
            coupon_code
        )

        return

    # =====================================================
    # پرداخت خرید (امن)
    # =====================================================

    if data.startswith("paid_"):

        parts = data.split("_")
        if len(parts) < 2:
            return

        volume = parts[1]

        # محاسبه امن قیمت
        if volume in PLANS:
            base_price = PLANS[volume]
        else:
            # حجم دلخواه
            custom_volume = context.user_data.get("custom_volume")
            custom_price = context.user_data.get("custom_price")

            if not custom_volume or str(custom_volume) != str(volume):
                await query.answer("سفارش نامعتبر است. دوباره انتخاب کنید.", show_alert=True)
                return

            base_price = custom_price

        # اعمال کوپن (اگر هنوز معتبر باشد)
        coupon_code = context.user_data.get("coupon_code")
        price = base_price

        if coupon_code:
            result = apply_coupon(coupon_code, user_id, base_price)
            if result["status"] == "success":
                price = result["price"]
            else:
                coupon_code = None
                context.user_data.pop("coupon_code", None)

        order_id = create_order(
            user,
            volume,
            price,
            coupon_code
        )

        # پاک کردن stateها
        context.user_data.pop("coupon_code", None)
        context.user_data.pop("custom_volume", None)
        context.user_data.pop("custom_price", None)
        context.user_data["last_order_id"] = order_id

        await query.edit_message_text(
            t(
                lang,
                "order_created",
                order=order_id,
                volume=volume,
                price=price
            )
        )

        return

    # =====================================================
    # حجم دلخواه
    # =====================================================

    if data == "custom":

        context.user_data["waiting_custom_volume"] = True
        # پاک کردن کوپن قبلی برای جلوگیری از تداخل (اختیاری)
        # context.user_data.pop("coupon_code", None)

        await query.edit_message_text(
            t(lang, "custom_prompt")
        )

        return

    # =====================================================
    # تست
    # =====================================================

    if data == "trial":

        result = claim_trial(user)

        if result["status"] == "already":

            await query.edit_message_text(
                t(lang, "trial_already"),
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            t(lang, "buy"),
                            callback_data="buy"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            t(lang, "back"),
                            callback_data="home"
                        )
                    ]
                ])
            )

            return

        if result["status"] == "empty":

            await query.edit_message_text(
                t(lang, "trial_empty"),
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            t(lang, "back"),
                            callback_data="home"
                        )
                    ]
                ])
            )

            return

        await query.edit_message_text(
            t(
                lang,
                "trial_success",
                link=result["link"]
            ),
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        t(lang, "buy"),
                        callback_data="buy"
                    )
                ],
                [
                    InlineKeyboardButton(
                        t(lang, "main_menu"),
                        callback_data="home"
                    )
                ]
            ])
        )

        return

    # =====================================================
    # سرویس‌های من
    # =====================================================

    if data == "my_services":

        rows = get_user_services(user_id)

        if not rows:

            text = t(lang, "no_services")

        else:

            text = t(lang, "services_title")

            for row in rows:

                text += t(
                    lang,
                    "service_item",
                    id=row["id"],
                    volume=row["volume"],
                    expires=row["expires_at"] or "-",
                    link=row["link"]
                )

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        t(lang, "renew"),
                        callback_data="renew"
                    )
                ],
                [
                    InlineKeyboardButton(
                        t(lang, "back"),
                        callback_data="home"
                    )
                ]
            ])
        )

        return

    # =====================================================
    # تمدید
    # =====================================================

    if data == "renew":

        await show_renew(query)

        return

    if data.startswith("renew_") and not data.startswith("renewpay_") and not data.startswith("renewpaid_"):

        try:
            order_id = int(data.split("_")[1])
        except ValueError:
            return

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
        # قیمت امن محاسبه می‌شود
        try:
            price = int(float(volume)) * PRICE_PER_GB
        except (ValueError, TypeError):
            await query.answer("حجم نامعتبر است.", show_alert=True)
            return

        context.user_data["renew_order_id"] = order_id
        context.user_data["renew_volume"] = volume
        context.user_data["renew_price"] = price

        await query.edit_message_text(
            t(
                lang,
                "renew_payment",
                volume=volume,
                price=price
            ),
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        t(lang, "paid"),
                        callback_data=f"renewpay_{volume}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        t(lang, "back"),
                        callback_data="renew"
                    )
                ]
            ])
        )

        return

    if data.startswith("renewpay_"):

        parts = data.split("_")
        if len(parts) < 2:
            return

        volume = parts[1]

        # بررسی امن
        stored_volume = context.user_data.get("renew_volume")
        stored_price = context.user_data.get("renew_price")

        if not stored_volume or str(stored_volume) != str(volume) or not stored_price:
            await query.answer("سفارش نامعتبر است.", show_alert=True)
            return

        price = stored_price

        await query.edit_message_text(
            t(
                lang,
                "renew_paid",
                volume=volume,
                price=price,
                card=CARD_NUMBER
            ),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        t(lang, "paid"),
                        callback_data=f"renewpaid_{volume}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        t(lang, "back"),
                        callback_data="renew"
                    )
                ]
            ])
        )

        return

    if data.startswith("renewpaid_"):

        parts = data.split("_")
        if len(parts) < 2:
            return

        volume = parts[1]

        stored_volume = context.user_data.get("renew_volume")
        stored_price = context.user_data.get("renew_price")

        if not stored_volume or str(stored_volume) != str(volume) or not stored_price:
            await query.answer("سفارش نامعتبر است.", show_alert=True)
            return

        price = stored_price

        order_id = create_order(
            user,
            volume,
            price,
            coupon_code=None  # تمدید فعلاً کوپن ندارد
        )

        context.user_data["last_order_id"] = order_id
        context.user_data.pop("renew_volume", None)
        context.user_data.pop("renew_price", None)
        context.user_data.pop("renew_order_id", None)

        await query.edit_message_text(
            t(
                lang,
                "renew_created",
                order=order_id,
                volume=volume,
                price=price
            )
        )

        return

    # =====================================================
    # پشتیبانی
    # =====================================================

    if data == "support":

        await query.edit_message_text(
            t(lang, "support_title"),
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        t(lang, "create_ticket"),
                        callback_data="new_ticket"
                    )
                ],
                [
                    InlineKeyboardButton(
                        t(lang, "back"),
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

        context.user_data["ticket_id"] = ticket_id
        context.user_data["waiting_ticket_message"] = True

        await query.edit_message_text(
            t(
                lang,
                "ticket_prompt",
                id=ticket_id
            )
        )

        return

    # =====================================================
    # دعوت
    # =====================================================

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
                t(
                    lang,
                    "referral_title",
                    count=count,
                    link=link
                ),
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            t(lang, "back"),
                            callback_data="home"
                        )
                    ]
                ])
            )

        except Exception:

            await query.edit_message_text(
                t(lang, "referral_error")
            )

        return

    # =====================================================
    # کوپن
    # =====================================================

    if data == "coupon":

        context.user_data["waiting_coupon"] = True

        await query.edit_message_text(
            t(lang, "coupon_prompt")
        )

        return

    # =====================================================
    # پنل ادمین
    # =====================================================

    if data == "admin":

        if user_id != ADMIN_ID:
            return

        await show_admin(query)

        return

    if data == "admin_stock":

        if user_id != ADMIN_ID:
            return

        await show_admin_stock(query)

        return

    if data == "admin_stats":

        if user_id != ADMIN_ID:
            return

        await show_admin_stats(query)

        return

    if data == "admin_orders":

        if user_id != ADMIN_ID:
            return

        await show_admin_orders(query)

        return

    # =====================================================
    # افزودن لینک
    # =====================================================

    if data == "admin_add":

        if user_id != ADMIN_ID:
            return

        context.user_data["admin_waiting_volume"] = True

        await query.edit_message_text(
            "➕ افزودن لینک سرویس\n\n"
            "حجم لینک را به گیگ وارد کن.\n\n"
            "مثال: 10"
        )

        return

    if data == "admin_delete":

        if user_id != ADMIN_ID:
            return

        await show_delete_menu(query)

        return

    if data.startswith("delete_"):

        if user_id != ADMIN_ID:
            return

        try:
            subscription_id = int(data.split("_")[1])
        except ValueError:
            return

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

    # =====================================================
    # مدیریت تست
    # =====================================================

    if data == "admin_trial":

        if user_id != ADMIN_ID:
            return

        await show_admin_trial(query)

        return

    if data == "admin_trial_add":

        if user_id != ADMIN_ID:
            return

        context.user_data["admin_waiting_trial_link"] = True

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

        try:
            trial_id = int(data.split("_")[2])
        except ValueError:
            return

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

    # =====================================================
    # کوپن ادمین
    # =====================================================

    if data == "admin_coupon":

        if user_id != ADMIN_ID:
            return

        context.user_data["admin_waiting_coupon"] = True

        await query.edit_message_text(
            "🎟 ساخت کد تخفیف\n\n"
            "فرمت:\n"
            "CODE درصد تعداد\n\n"
            "مثال:\n"
            "HANZU20 20 100"
        )

        return

    # =====================================================
    # پیام همگانی
    # =====================================================

    if data == "admin_broadcast":

        if user_id != ADMIN_ID:
            return

        context.user_data["admin_broadcast"] = True

        await query.edit_message_text(
            "📢 پیام همگانی\n\n"
            "متنی که می‌خواهی برای کاربران ارسال شود را بفرست."
        )

        return

    # =====================================================
    # تیکت‌های ادمین
    # =====================================================

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

    # =====================================================
    # باز کردن تیکت
    # =====================================================

    if data.startswith("ticket_"):

        if user_id != ADMIN_ID:
            return

        try:
            ticket_id = int(data.split("_")[1])
        except ValueError:
            return

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

        context.user_data["admin_ticket_id"] = ticket_id
        context.user_data["admin_waiting_ticket_reply"] = True

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

    # =====================================================
    # بستن تیکت
    # =====================================================

    if data.startswith("close_ticket_"):

        if user_id != ADMIN_ID:
            return

        try:
            ticket_id = int(data.split("_")[2])
        except ValueError:
            return

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

                recipient_lang = (
                    get_user_language(ticket["user_id"])
                    or "fa"
                )

                await context.bot.send_message(
                    chat_id=ticket["user_id"],
                    text=t(
                        recipient_lang,
                        "ticket_closed",
                        id=ticket_id
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

    # =====================================================
    # تأیید سفارش
    # =====================================================

    if data.startswith("approve_"):

        if user_id != ADMIN_ID:
            return

        try:
            order_id = int(data.split("_")[1])
        except ValueError:
            return

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

        recipient_lang = (
            get_user_language(order["user_id"])
            or "fa"
        )

        await context.bot.send_message(
            chat_id=order["user_id"],
            text=t(
                recipient_lang,
                "payment_confirmed",
                volume=order["volume"],
                expires=result["expires_at"],
                order=order_id,
                link=result["link"]
            )
        )

        try:
            await query.edit_message_caption(
                caption=(
                    f"✅ سفارش #{order_id} تأیید شد.\n\n"
                    f"📦 {order['volume']} گیگ\n"
                    f"💰 {order['price']:,} تومان\n"
                    f"📅 انقضا: {result['expires_at']}"
                )
            )
        except Exception:
            await query.edit_message_text(
                f"✅ سفارش #{order_id} تأیید شد.\n\n"
                f"📦 {order['volume']} گیگ\n"
                f"💰 {order['price']:,} تومان\n"
                f"📅 انقضا: {result['expires_at']}"
            )

        return

    # =====================================================
    # رد سفارش
    # =====================================================

    if data.startswith("reject_"):

        if user_id != ADMIN_ID:
            return

        try:
            order_id = int(data.split("_")[1])
        except ValueError:
            return

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

        recipient_lang = (
            get_user_language(order["user_id"])
            or "fa"
        )

        await context.bot.send_message(
            chat_id=order["user_id"],
            text=t(
                recipient_lang,
                "payment_rejected",
                order=order_id
            )
        )

        try:
            await query.edit_message_caption(
                caption=(
                    f"❌ سفارش #{order_id} رد شد.\n\n"
                    f"📦 {order['volume']} گیگ\n"
                    f"💰 {order['price']:,} تومان"
                )
            )
        except Exception:
            await query.edit_message_text(
                f"❌ سفارش #{order_id} رد شد.\n\n"
                f"📦 {order['volume']} گیگ\n"
                f"💰 {order['price']:,} تومان"
            )

        return


# =========================================================
# پیام‌های متنی
# =========================================================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    text = update.message.text.strip()

    ensure_user(user)

    lang = get_user_language(user.id)

    if not lang:

        await show_language_selector_message(
            update.message
        )

        return

    # =====================================================
    # پیام تیکت کاربر
    # =====================================================

    if context.user_data.get("waiting_ticket_message"):

        ticket_id = context.user_data.get("ticket_id")

        if not ticket_id:
            return

        add_ticket_message(
            ticket_id,
            user.id,
            text
        )

        context.user_data["waiting_ticket_message"] = False

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
            t(
                lang,
                "ticket_created",
                id=ticket_id
            )
        )

        return

    # =====================================================
    # پاسخ ادمین
    # =====================================================

    if (
        user.id == ADMIN_ID
        and context.user_data.get("admin_waiting_ticket_reply")
    ):

        ticket_id = context.user_data.get("admin_ticket_id")

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

        recipient_lang = (
            get_user_language(ticket["user_id"])
            or "fa"
        )

        await context.bot.send_message(
            chat_id=ticket["user_id"],
            text=(
                "💬 پاسخ پشتیبانی\n\n"
                f"🎫 تیکت #{ticket_id}\n\n"
                f"{text}"
            )
        )

        await update.message.reply_text(
            "✅ پاسخ برای کاربر ارسال شد."
        )

        context.user_data["admin_waiting_ticket_reply"] = False

        return

    # =====================================================
    # پیام همگانی
    # =====================================================

    if (
        user.id == ADMIN_ID
        and context.user_data.get("admin_broadcast")
    ):

        context.user_data["admin_broadcast"] = False

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

    # =====================================================
    # ساخت کوپن
    # =====================================================

    if (
        user.id == ADMIN_ID
        and context.user_data.get("admin_waiting_coupon")
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

        context.user_data["admin_waiting_coupon"] = False

        return

    # =====================================================
    # افزودن تست
    # =====================================================

    if (
        user.id == ADMIN_ID
        and context.user_data.get("admin_waiting_trial_link")
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

        context.user_data["admin_waiting_trial_link"] = False

        await update.message.reply_text(
            "✅ لینک تست اضافه شد.\n\n"
            "📦 حجم: 100 مگابایت\n"
            "⏳ مدت: 1 روز"
        )

        return

    # =====================================================
    # حجم دلخواه
    # =====================================================

    if context.user_data.get("waiting_custom_volume"):

        context.user_data["waiting_custom_volume"] = False

        try:

            volume = int(text)

            if volume <= 0 or volume > 1000:
                raise ValueError

        except ValueError:

            await update.message.reply_text(
                t(lang, "invalid_volume")
            )

            return

        price = volume * PRICE_PER_GB

        # ذخیره امن در user_data
        context.user_data["custom_volume"] = volume
        context.user_data["custom_price"] = price

        # اعمال کوپن اگر وجود داشته باشد
        coupon_code = context.user_data.get("coupon_code")
        final_price = price
        original_price = price

        if coupon_code:
            result = apply_coupon(coupon_code, user.id, price)
            if result["status"] == "success":
                final_price = result["price"]
            else:
                context.user_data.pop("coupon_code", None)
                coupon_code = None

        caption = t(
            lang,
            "custom_summary",
            volume=volume,
            price=final_price
        )

        if original_price != final_price and coupon_code:
            caption += t(
                lang,
                "original_price",
                original=original_price,
                coupon=coupon_code
            )

        await update.message.reply_text(
            caption,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        t(lang, "paid"),
                        callback_data=f"paid_{volume}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        t(lang, "back"),
                        callback_data="buy"
                    )
                ]
            ])
        )

        return

    # =====================================================
    # کوپن کاربر
    # =====================================================

    if context.user_data.get("waiting_coupon"):

        context.user_data["waiting_coupon"] = False

        coupon = get_coupon(
            text.upper()
        )

        if not coupon:

            await update.message.reply_text(
                t(lang, "coupon_invalid")
            )

            return

        if user_used_coupon(
            coupon["id"],
            user.id
        ):

            await update.message.reply_text(
                t(lang, "coupon_used")
            )

            return

        # بررسی ظرفیت
        if coupon["max_uses"] > 0 and coupon["used_count"] >= coupon["max_uses"]:
            await update.message.reply_text(
                t(lang, "coupon_invalid")
            )
            return

        context.user_data["coupon_code"] = coupon["code"]

        await update.message.reply_text(
            t(
                lang,
                "coupon_valid",
                code=coupon["code"],
                percent=coupon["percent"]
            ),
            reply_markup=buy_keyboard(user.id)
        )

        return

    # =====================================================
    # حجم لینک ادمین
    # =====================================================

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
                "❌ حجم نامعتبر است."
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

    # =====================================================
    # لینک سرویس ادمین
    # =====================================================

    if (
        user.id == ADMIN_ID
        and context.user_data.get("admin_waiting_link")
    ):

        if not (
            text.startswith("http://")
            or text.startswith("https://")
        ):

            await update.message.reply_text(
                "❌ لینک معتبر نیست."
            )

            return

        volume = context.user_data.get("admin_add_volume")

        add_subscription(
            volume,
            text
        )

        context.user_data.pop("admin_waiting_link", None)
        context.user_data.pop("admin_add_volume", None)

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

    lang = get_user_language(user.id) or "fa"

    order = get_latest_pending_order(
        user.id
    )

    if not order:

        await update.message.reply_text(
            t(lang, "no_pending")
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
        t(
            lang,
            "receipt_received",
            order=order["id"]
        )
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

                lang = (
                    get_user_language(row["user_id"])
                    or "fa"
                )

                if 2.5 <= days <= 3.5:

                    reminder_type = "3days"

                    message = t(
                        lang,
                        "reminder_3",
                        order=row["id"]
                    )

                elif 0.5 <= days <= 1.5:

                    reminder_type = "1day"

                    message = t(
                        lang,
                        "reminder_1",
                        order=row["id"]
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
            "language",
            language_command
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
            filters.TEXT &\~filters.COMMAND,
            text_handler
        )
    )

    print(
        "HanzuVPN Bot is running..."
    )

    app.run_polling()


if __name__ == "__main__":
    main()