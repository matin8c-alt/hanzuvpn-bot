import os
import re
import sqlite3
import asyncio
import json
import base64
import hashlib
import hmac
import threading
import tempfile
from urllib.parse import parse_qsl, unquote, urljoin, quote
from urllib import request as urlrequest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timedelta

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CopyTextButton,
    MessageEntity,
    BotCommand,
    MenuButtonWebApp,
    WebAppInfo,
    InputFile,
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
    "1": 3500,
    "10": 35000,
    "15": 52500,
    "20": 70000,
    "30": 105000,
    "40": 140000,
    "50": 175000,
    "100": 350000,
}

SERVICE_DAYS = 30
TRIAL_DAYS = 1
MIN_CHARGE = 10000  # حداقل مبلغ شارژ کیف پول
TARIFF_PLANS = {"1": 3500, "10": 35000, "15": 52500, "20": 70000, "30": 105000, "40": 140000, "50": 175000, "100": 350000}
MINI_APP_URL = "https://hanzuvpn-app2.matin8c.workers.dev"
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("PORT", os.getenv("API_PORT", "8080")))

UNLIMITED_PLANS = {
    "UNLIMITED_1": {"label_fa": "تک کاربره", "label_en": "Single User", "label_ku": "یەک بەکارهێنەر", "price": 150000, "hwid": 1},
    "UNLIMITED_2": {"label_fa": "دو کاربره", "label_en": "Two Users", "label_ku": "دوو بەکارهێنەر", "price": 250000, "hwid": 2},
    "UNLIMITED_3": {"label_fa": "سه کاربره", "label_en": "Three Users", "label_ku": "سێ بەکارهێنەر", "price": 350000, "hwid": 3},
}


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
        "language_title": "🌐 انتخاب زبان\n\nزبان موردنظر خود را انتخاب کنید:",
        "language_changed": "✅ زبان با موفقیت تغییر کرد.",
        "welcome": "🌐 HanzuVPN\n\nخوش آمدید 👋\n\nاز منوی زیر یک گزینه را انتخاب کنید:",
        "buy": "🛒 خرید سرویس",
        "trial": "🎁 تست رایگان",
        "services": "📦 سرویس‌های من",
        "renew": "🔄 تمدید",
        "coupon": "🎟 کد تخفیف",
        "referral": "👥 دعوت دوستان",
        "support": "🎫 پشتیبانی",
    "plan_1": "📦 پلن ۱ گیگ",
    "plan_10": "📦 پلن ۱۰ گیگ",
    "plan_15": "📦 پلن ۱۵ گیگ",
    "plan_20": "📦 پلن ۲۰ گیگ",
    "plan_30": "📦 پلن ۳۰ گیگ",
    "plan_40": "📦 پلن ۴۰ گیگ",
    "plan_50": "📦 پلن ۵۰ گیگ",
    "plan_100": "📦 پلن ۱۰۰ گیگ",
    "copy_card": "📋 کپی شماره کارت",
        "language": "🌐 تغییر زبان",
        "admin": "⚙️ پنل مدیریت",
        "back": "🔙 بازگشت",
        "main_menu": "🔙 منوی اصلی",
        "wallet": "💰 کیف پول",
        "buy_title": "🛒 <b>خرید سرویس</b>\n\n⏳ اعتبار همه سرویس‌ها: <b>۳۰ روز</b>\n\n📦 حجم موردنظر خود را انتخاب کنید:",
        "custom": "✏️ حجم دلخواه",
        "trial_already": "⚠️ شما قبلاً تست رایگان خود را دریافت کرده‌اید.\n\nهر کاربر فقط یک‌بار می‌تواند از تست رایگان استفاده کند.",
        "trial_empty": "😔 در حال حاضر تست رایگان موجود نیست.\n\nلطفاً بعداً دوباره امتحان کنید.",
        "trial_success": "🎁 تست رایگان HanzuVPN\n\n📦 حجم: 100 مگابایت\n⏳ مدت: 1 روز\n\n🔗 لینک Subscription:\n\n{link}\n\n📌 لینک را در برنامه VPN خود وارد کنید.",
        "payment": "💳 <b>اطلاعات پرداخت</b>\n\n📦 حجم سرویس: <b>{volume} گیگ</b>\n💰 مبلغ: <b>{price:,} تومان</b>\n⏳ مدت اعتبار: <b>۳۰ روز</b>\n",
        "original_price": "\n🏷 مبلغ اصلی: {original:,} تومان\n🎟 کد تخفیف: {coupon}\n",
        "card": "\n💳 شماره کارت:\n`{card}`\n\nبعد از انتقال مبلغ، روی «پرداخت کردم» بزنید و سپس تصویر رسید را ارسال کنید.",
        "paid": "💳 پرداخت کردم",
        "pay": "💳 پرداخت",
        "pay_wallet": "💰 پرداخت از کیف پول",
        "order_created": "✅ درخواست شما ثبت شد.\n\n🧾 سفارش: #{order}\n📦 حجم: {volume} گیگ\n💰 مبلغ: {price:,} تومان\n\n📸 حالا تصویر رسید را ارسال کنید.",
        "receipt_received": "✅ رسید شما دریافت شد.\n\n🧾 سفارش #{order}\n\nپس از بررسی توسط مدیریت، نتیجه برای شما ارسال می‌شود.",
        "no_pending": "❌ سفارش در انتظار پرداختی پیدا نشد.",
        "services_title": "📦 <b>سرویس‌های من</b>\n\nسرویس‌های فعال شما در ادامه نمایش داده می‌شوند:",
        "no_services": "📦 <b>سرویس‌های من</b>\n\nهنوز سرویس فعالی ندارید.\n\n🛒 برای شروع، یک سرویس جدید تهیه کنید.",
        "service_item": "🧾 سفارش #{id}\n📦 حجم: {volume} گیگ\n⏳ انقضا: {expires}\n\n🔗 لینک:\n{link}\n\n",
        "renew_no_services": "🔄 تمدید سرویس\n\nشما سرویس فعالی ندارید.",
        "renew_choose": "🔄 تمدید سرویس\n\nسرویسی که می‌خواهید تمدید کنید را انتخاب کنید:",
        "renew_payment": "🔄 تمدید سرویس\n\n📦 حجم: {volume} گیگ\n💰 مبلغ تمدید: {price:,} تومان\n⏳ مدت: 30 روز\n\nبرای پرداخت روی دکمه زیر بزنید.",
        "renew_paid": "💳 پرداخت تمدید\n\n📦 حجم: {volume} گیگ\n💰 مبلغ: {price:,} تومان\n⏳ مدت: 30 روز\n\n💳 شماره کارت:\n`{card}`\n\nبعد از پرداخت روی دکمه زیر بزنید.",
        "renew_created": "✅ درخواست تمدید ثبت شد.\n\n🧾 سفارش: #{order}\n📦 حجم: {volume} گیگ\n💰 مبلغ: {price:,} تومان\n\n📸 حالا تصویر رسید را ارسال کنید.",
        "custom_prompt": "✏️ حجم دلخواه\n\nحجم موردنظر را به گیگ وارد کن.\n\nمثال:\n25",
        "invalid_volume": "❌ حجم نامعتبر است.\n\nمثلاً 25 وارد کن.",
        "custom_summary": "🛒 سرویس دلخواه\n\n📦 حجم: {volume} گیگ\n💰 قیمت: {price:,} تومان\n⏳ مدت: 30 روز",
        "support_title": "🎫 <b>پشتیبانی HanzuVPN</b>\n\nاگر مشکلی دارید یا به راهنمایی نیاز دارید، از طریق تیکت با ما در ارتباط باشید.",
        "create_ticket": "🎫 ایجاد تیکت",
        "ticket_prompt": "🎫 تیکت #{id}\n\nپیام خود را ارسال کنید.",
        "ticket_created": "✅ پیام شما در تیکت #{id} ثبت شد.\n\nپشتیبانی آن را بررسی می‌کند.",
        "ticket_closed": "🔒 تیکت #{id} بسته شد.\n\nدر صورت نیاز می‌توانید تیکت جدید ایجاد کنید.",
        "referral_title": "👥 <b>دعوت دوستان</b>\n\n👤 تعداد دعوت‌های شما: <b>{count}</b>\n\n🔗 لینک دعوت اختصاصی\n{link}\n\nلینک را برای دوستانتان ارسال کنید و از مزایای دعوت استفاده کنید.",
        "referral_error": "❌ خطا در ساخت لینک دعوت.",
        "coupon_prompt": "🎟 کد تخفیف\n\nکد تخفیف خود را ارسال کنید.",
        "coupon_invalid": "❌ کد تخفیف نامعتبر است.",
        "coupon_used": "⚠️ شما قبلاً از این کد استفاده کرده‌اید.",
        "coupon_valid": "✅ کد تخفیف معتبر است.\n\n🎟 کد: {code}\n💰 تخفیف: {percent}%\n\nحالا سرویس موردنظر را انتخاب کنید:",
        "help": "📚 راهنمای HanzuVPN\n\n/start - منوی اصلی\n/buy - خرید سرویس\n/services - سرویس‌های من\n/trial - تست رایگان\n/support - پشتیبانی\n/help - راهنما",
        "payment_confirmed": "✅ پرداخت شما تأیید شد.\n\n🌐 HanzuVPN\n\n📦 حجم: {volume} گیگ\n⏳ مدت: 30 روز\n📅 انقضا: {expires}\n🧾 سفارش: #{order}\n\n🔗 لینک Subscription:\n\n{link}\n\n📌 لینک را در برنامه VPN خود وارد کنید.",
        "payment_rejected": "❌ پرداخت سفارش شما تأیید نشد.\n\n🧾 سفارش: #{order}\n\nدر صورت اشتباه با پشتیبانی تماس بگیرید.",
        "reminder_3": "⚠️ یادآوری HanzuVPN\n\nسرویس #{order} شما حدود 3 روز دیگر منقضی می‌شود.\n\nبرای تمدید از بخش «🔄 تمدید» استفاده کنید.",
        "reminder_1": "⏰ یادآوری HanzuVPN\n\nسرویس #{order} شما حدود 1 روز دیگر منقضی می‌شود.\n\nبرای تمدید سرویس اقدام کنید.",
        "wallet_title": "💰 <b>کیف پول</b>\n\n💵 موجودی فعلی\n<b>{balance:,} تومان</b>\n\nاز گزینه‌های زیر انتخاب کنید:",
        "charge_wallet": "➕ شارژ کیف پول",
        "wallet_history": "📜 تاریخچه تراکنش‌ها",
        "charge_prompt": "💰 شارژ کیف پول\n\nمبلغ مورد نظر را به تومان وارد کنید.\n\nحداقل مبلغ: {min:,} تومان\n\nمثال:\n50000",
        "invalid_charge": "❌ مبلغ نامعتبر است.\n\nحداقل مبلغ شارژ {min:,} تومان است.",
        "charge_payment": "💰 شارژ کیف پول\n\n💵 مبلغ: {amount:,} تومان\n\n💳 شماره کارت:\n`{card}`\n\nبعد از واریز، روی «پرداخت کردم» بزنید و رسید را ارسال کنید.",
        "charge_created": "✅ درخواست شارژ ثبت شد.\n\n🧾 شماره: #{order}\n💰 مبلغ: {amount:,} تومان\n\n📸 حالا تصویر رسید را ارسال کنید.",
        "charge_success": "✅ شارژ کیف پول با موفقیت انجام شد.\n\n💰 مبلغ: {amount:,} تومان\n💵 موجودی جدید: {balance:,} تومان",
        "not_enough_balance": "❌ موجودی کیف پول شما کافی نیست.",
        "paid_from_wallet": "✅ پرداخت از کیف پول با موفقیت انجام شد.\n\n💰 مبلغ کسر شده: {price:,} تومان\n💵 موجودی باقی‌مانده: {balance:,} تومان",
        "no_history": "📜 تاریخچه تراکنش‌ها\n\nهنوز تراکنشی ثبت نشده است.",
        "history_title": "📜 آخرین تراکنش‌های شما\n\n",
        "history_item": "{emoji} {amount:,} تومان\n📝 {desc}\n🕐 {date}\n\n",
        'admin_add': '➕ افزودن لینک سرویس',
        'admin_trial': '🎁 مدیریت تست',
        'admin_stock': '📦 موجودی',
        'admin_delete': '🗑 حذف لینک',
        'admin_coupon': '🎟 کوپن\u200cها',
        'admin_balance': '💰 مدیریت موجودی کاربر',
        'admin_broadcast': '📢 پیام همگانی',
        'admin_stats': '📊 آمار',
        'admin_orders': '🧾 سفارش\u200cها',
        'admin_tickets': '🎫 تیکت\u200cها',
        'admin_panel': '🔙 پنل مدیریت',
        'admin_trial_add': '➕ افزودن لینک تست',
        'admin_trial_delete': '🗑 حذف لینک تست',
        'admin_trial_stock': '📦 موجودی تست',
        'admin_ticket_view': '🎫 مشاهده تیکت',
        'admin_close_ticket': '🔒 بستن تیکت',
        'approve_payment': '✅ تأیید پرداخت',
        'reject_payment': '❌ رد پرداخت',
        'renew_item': '🔄 تمدید #{id}',
        'trial_item': '🗑 تست #{id}',
        'delete_item': '🗑 #{id} | {volume} گیگ',
        'ticket_item': '🎫 تیکت #{id}',
        'volume_label': '📦 {volume} گیگ',
    },
    "ku": {
        "language_title": "🌐 هەڵبژاردنی زمان\n\nتکایە زمانی خۆت هەڵبژێرە:",
        "language_changed": "✅ زمان بە سەرکەوتوویی گۆڕدرا.",
        "welcome": "🌐 HanzuVPN\n\nبەخێربێیت 👋\n\nلە خوارەوە یەک هەڵبژاردە هەڵبژێرە:",
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
        "wallet": "💰 جزدان",
        "buy_title": "🛒 هەڵبژاردنی خزمەتگوزاری\n\n⏳ ماوەی هەموو خزمەتگوزارییەکان: 30 ڕۆژ\n\nقەبارەی خۆت هەڵبژێرە:",
        "custom": "✏️ قەبارەی دڵخواز",
        "trial_already": "⚠️ پێشتر تاقیکردنەوەی بەخۆڕاییت وەرگرتووە.",
        "trial_empty": "😔 لە ئێستادا تاقیکردنەوەی بەخۆڕایی بەردەست نییە.",
        "trial_success": "🎁 تاقیکردنەوەی بەخۆڕایی\n\n📦 قەبارە: 100 مێگابایت\n⏳ ماوە: 1 ڕۆژ\n\n🔗 بەستەر:\n{link}",
        "payment": "💳 زانیاری پارەدان\n\n📦 قەبارە: {volume} گیگ\n💰 بڕ: {price:,} تومان\n⏳ ماوە: 30 ڕۆژ\n",
        "original_price": "\n🏷 بڕی سەرەکی: {original:,} تومان\n🎟 کۆد: {coupon}\n",
        "card": "\n💳 ژمارەی کارت:\n`{card}`\n\nدوای پارەدان «پارەم داوە» هەڵبژێرە و وێنەی پسوڵە بنێرە.",
        "paid": "💳 پارەم داوە",
        "pay": "💳 پارەدان",
        "pay_wallet": "💰 پارەدان لە جزدان",
        "order_created": "✅ داواکاری تۆمار کرا.\n\n🧾 #{order}\n📦 {volume} گیگ\n💰 {price:,} تومان\n\n📸 وێنەی پسوڵە بنێرە.",
        "receipt_received": "✅ پسوڵە وەرگیرا.\n\n🧾 #{order}",
        "no_pending": "❌ هیچ داواکارییەکی چاوەڕوان نەدۆزرایەوە.",
        "services_title": "📦 خزمەتگوزارییەکانت\n\n",
        "no_services": "📦 هیچ خزمەتگوزارییەکی چالاکت نییە.",
        "service_item": "🧾 #{id}\n📦 {volume} گیگ\n⏳ {expires}\n\n🔗 {link}\n\n",
        "renew_no_services": "🔄 هیچ خزمەتگوزارییەکی چالاکت نییە.",
        "renew_choose": "🔄 خزمەتگوزارییەک هەڵبژێرە بۆ نوێکردنەوە:",
        "renew_payment": "🔄 نوێکردنەوە\n\n📦 {volume} گیگ\n💰 {price:,} تومان",
        "renew_paid": "💳 پارەدانی نوێکردنەوە\n\n📦 {volume} گیگ\n💰 {price:,} تومان\n\n💳 `{card}`",
        "renew_created": "✅ داواکاری نوێکردنەوە تۆمار کرا.\n\n🧾 #{order}",
        "custom_prompt": "✏️ قەبارە بە گیگ بنووسە:\n\nنموونە: 25",
        "invalid_volume": "❌ قەبارە نادروستە.",
        "custom_summary": "🛒 خزمەتگوزاری دڵخواز\n\n📦 {volume} گیگ\n💰 {price:,} تومان",
        "support_title": "🎫 پشتگیری\n\nتیکەت دروست بکە.",
        "create_ticket": "🎫 دروستکردنی تیکەت",
        "ticket_prompt": "🎫 تیکەتی #{id}\n\nنامەکەت بنێرە.",
        "ticket_created": "✅ نامە تۆمار کرا لە تیکەتی #{id}",
        "ticket_closed": "🔒 تیکەتی #{id} داخرا.",
        "referral_title": "👥 بانگهێشت\n\n👤 ژمارە: {count}\n\nبەستەر:\n{link}",
        "referral_error": "❌ هەڵە لە دروستکردنی بەستەر.",
        "coupon_prompt": "🎟 کۆدی داشکان بنێرە.",
        "coupon_invalid": "❌ کۆد نادروستە.",
        "coupon_used": "⚠️ پێشتر بەکارت هێناوە.",
        "coupon_valid": "✅ کۆد دروستە.\n\n🎟 {code}\n💰 {percent}%",
        "help": "📚 ڕێنمایی\n\n/start - سەرەکی\n/buy - کڕین\n/services - خزمەتگوزارییەکان\n/trial - تاقیکردنەوە\n/support - پشتگیری",
        "payment_confirmed": "✅ پارەدان پشتڕاست کرایەوە.\n\n📦 {volume} گیگ\n📅 {expires}\n🧾 #{order}\n\n🔗 {link}",
        "payment_rejected": "❌ پارەدان ڕەتکرایەوە.\n\n🧾 #{order}",
        "reminder_3": "⚠️ خزمەتگوزاری #{order} نزیکەی 3 ڕۆژی تر بەسەر دەچێت.",
        "reminder_1": "⏰ خزمەتگوزاری #{order} نزیکەی 1 ڕۆژی تر بەسەر دەچێت.",
        "wallet_title": "💰 جزدان\n\n💵 موجودی: {balance:,} تومان",
        "charge_wallet": "➕ شارژکردنی جزدان",
        "wallet_history": "📜 مێژووی مامەڵەکان",
        "charge_prompt": "💰 شارژ\n\nبڕ بنووسە (کەمترین: {min:,})",
        "invalid_charge": "❌ بڕ نادروستە.",
        "charge_payment": "💰 شارژ\n\n💵 {amount:,} تومان\n\n💳 `{card}`",
        "charge_created": "✅ داواکاری شارژ تۆمار کرا.\n\n🧾 #{order}",
        "charge_success": "✅ شارژ سەرکەوتوو بوو.\n\n💰 {amount:,}\n💵 موجودی نوێ: {balance:,}",
        "not_enough_balance": "❌ موجودی بەس نییە.",
        "paid_from_wallet": "✅ پارەدان لە جزدان سەرکەوتوو بوو.\n\n💰 {price:,}\n💵 ماوە: {balance:,}",
        "no_history": "📜 هیچ مامەڵەیەک نییە.",
        "history_title": "📜 دوایین مامەڵەکان\n\n",
        "history_item": "{emoji} {amount:,}\n📝 {desc}\n🕐 {date}\n\n",
        'admin_add': '➕ زیادکردنی بەستەر',
        'admin_trial': '🎁 بەڕێوەبردنی تاقیکردنەوە',
        'admin_stock': '📦 کۆگا',
        'admin_delete': '🗑 سڕینەوەی بەستەر',
        'admin_coupon': '🎟 کۆدەکانی داشکاندن',
        'admin_balance': '💰 بەڕێوەبردنی باڵانسی بەکارهێنەر',
        'admin_broadcast': '📢 پەیامی گشتی',
        'admin_stats': '📊 ئامار',
        'admin_orders': '🧾 داواکارییەکان',
        'admin_tickets': '🎫 تیکەتەکان',
        'admin_panel': '🔙 پانێڵی بەڕێوەبردن',
        'admin_trial_add': '➕ زیادکردنی بەستەری تاقیکردنەوە',
        'admin_trial_delete': '🗑 سڕینەوەی تاقیکردنەوە',
        'admin_trial_stock': '📦 کۆگای تاقیکردنەوە',
        'admin_ticket_view': '🎫 بینینی تیکەت',
        'admin_close_ticket': '🔒 داخستنی تیکەت',
        'approve_payment': '✅ پشتڕاستکردنەوەی پارەدان',
        'reject_payment': '❌ ڕەتکردنەوەی پارەدان',
        'renew_item': '🔄 نوێکردنەوە #{id}',
        'trial_item': '🗑 تاقیکردنەوە #{id}',
        'delete_item': '🗑 #{id} | {volume} گیگ',
        'ticket_item': '🎫 تیکەتی #{id}',
        'volume_label': '📦 {volume} گیگ',
    },
    "en": {
        "language_title": "🌐 Choose Language\n\nPlease select your language:",
        "language_changed": "✅ Language changed successfully.",
        "welcome": "🌐 HanzuVPN\n\nWelcome 👋\n\nChoose an option below:",
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
        "wallet": "💰 Wallet",
        "buy_title": "🛒 Choose a Service\n\n⏳ All services are valid for 30 days.\n\nChoose your desired volume:",
        "custom": "✏️ Custom Volume",
        "trial_already": "⚠️ You have already received your free trial.",
        "trial_empty": "😔 No free trials are currently available.",
        "trial_success": "🎁 Free Trial\n\n📦 100 MB\n⏳ 1 day\n\n🔗 {link}",
        "payment": "💳 Payment Information\n\n📦 Volume: {volume} GB\n💰 Price: {price:,} Toman\n⏳ 30 days\n",
        "original_price": "\n🏷 Original: {original:,} Toman\n🎟 Coupon: {coupon}\n",
        "card": "\n💳 Card number:\n`{card}`\n\nAfter payment, tap «I Paid» and send the receipt.",
        "paid": "💳 I Paid",
        "pay": "💳 Pay",
        "pay_wallet": "💰 Pay from Wallet",
        "order_created": "✅ Request registered.\n\n🧾 Order: #{order}\n📦 {volume} GB\n💰 {price:,} Toman\n\n📸 Send the receipt.",
        "receipt_received": "✅ Receipt received.\n\n🧾 Order #{order}",
        "no_pending": "❌ No pending order found.",
        "services_title": "📦 Your Services\n\n",
        "no_services": "📦 You don't have any active services.",
        "service_item": "🧾 Order #{id}\n📦 {volume} GB\n⏳ {expires}\n\n🔗 {link}\n\n",
        "renew_no_services": "🔄 You don't have any active services.",
        "renew_choose": "🔄 Choose the service to renew:",
        "renew_payment": "🔄 Renew\n\n📦 {volume} GB\n💰 {price:,} Toman",
        "renew_paid": "💳 Renewal Payment\n\n📦 {volume} GB\n💰 {price:,} Toman\n\n💳 `{card}`",
        "renew_created": "✅ Renewal request registered.\n\n🧾 #{order}",
        "custom_prompt": "✏️ Enter volume in GB:\n\nExample: 25",
        "invalid_volume": "❌ Invalid volume.",
        "custom_summary": "🛒 Custom Service\n\n📦 {volume} GB\n💰 {price:,} Toman",
        "support_title": "🎫 Support\n\nCreate a ticket.",
        "create_ticket": "🎫 Create Ticket",
        "ticket_prompt": "🎫 Ticket #{id}\n\nSend your message.",
        "ticket_created": "✅ Message added to ticket #{id}",
        "ticket_closed": "🔒 Ticket #{id} closed.",
        "referral_title": "👥 Invite Friends\n\n👤 Referrals: {count}\n\nYour link:\n{link}",
        "referral_error": "❌ Error creating link.",
        "coupon_prompt": "🎟 Send your coupon code.",
        "coupon_invalid": "❌ Invalid coupon.",
        "coupon_used": "⚠️ You have already used this coupon.",
        "coupon_valid": "✅ Coupon valid.\n\n🎟 {code}\n💰 {percent}%",
        "help": "📚 Help\n\n/start - Main menu\n/buy - Buy\n/services - My services\n/trial - Trial\n/support - Support",
        "payment_confirmed": "✅ Payment approved.\n\n📦 {volume} GB\n📅 {expires}\n🧾 #{order}\n\n🔗 {link}",
        "payment_rejected": "❌ Payment rejected.\n\n🧾 #{order}",
        "reminder_3": "⚠️ Service #{order} expires in about 3 days.",
        "reminder_1": "⏰ Service #{order} expires in about 1 day.",
        "wallet_title": "💰 Your Wallet\n\n💵 Balance: {balance:,} Toman",
        "charge_wallet": "➕ Charge Wallet",
        "wallet_history": "📜 Transaction History",
        "charge_prompt": "💰 Charge Wallet\n\nEnter amount in Toman.\n\nMinimum: {min:,}",
        "invalid_charge": "❌ Invalid amount.\n\nMinimum is {min:,} Toman.",
        "charge_payment": "💰 Charge Wallet\n\n💵 Amount: {amount:,} Toman\n\n💳 `{card}`",
        "charge_created": "✅ Charge request registered.\n\n🧾 #{order}\n💰 {amount:,} Toman",
        "charge_success": "✅ Wallet charged successfully.\n\n💰 {amount:,} Toman\n💵 New balance: {balance:,}",
        "not_enough_balance": "❌ Insufficient wallet balance.",
        "paid_from_wallet": "✅ Paid from wallet successfully.\n\n💰 Deducted: {price:,}\n💵 Remaining: {balance:,}",
        "no_history": "📜 No transactions yet.",
        "history_title": "📜 Your recent transactions\n\n",
        "history_item": "{emoji} {amount:,} Toman\n📝 {desc}\n🕐 {date}\n\n",
        'admin_add': '➕ Add Service Link',
        'admin_trial': '🎁 Trial Management',
        'admin_stock': '📦 Stock',
        'admin_delete': '🗑 Delete Link',
        'admin_coupon': '🎟 Coupons',
        'admin_balance': '💰 User Balance',
        'admin_broadcast': '📢 Broadcast',
        'admin_stats': '📊 Statistics',
        'admin_orders': '🧾 Orders',
        'admin_tickets': '🎫 Tickets',
        'admin_panel': '🔙 Admin Panel',
        'admin_trial_add': '➕ Add Trial Link',
        'admin_trial_delete': '🗑 Delete Trial Link',
        'admin_trial_stock': '📦 Trial Stock',
        'admin_ticket_view': '🎫 View Ticket',
        'admin_close_ticket': '🔒 Close Ticket',
        'approve_payment': '✅ Approve Payment',
        'reject_payment': '❌ Reject Payment',
        'renew_item': '🔄 Renew #{id}',
        'trial_item': '🗑 Trial #{id}',
        'delete_item': '🗑 #{id} | {volume} GB',
        'ticket_item': '🎫 Ticket #{id}',
        'volume_label': '📦 {volume} GB',
    }
}


# منوی اصلی جمع‌وجور و مناسب موبایل؛ دو دکمه در هر ردیف.
MENU_ONE_PER_ROW = False

TEXTS["fa"].update({
    "panel": "پنل کاربری",
    "panel_btn": "📊 پنل کاربری",
    "dash_title": "📊 پنل کاربری\n\n👋 سلام {name}\n\n💰 موجودی: {balance:,} تومان\n📦 سرویس‌های فعال: {count} عدد\n\nیک گزینه را انتخاب کنید:",
    "dash_first_service": "➕ خرید اولین سرویس خود",
    "dash_balance": "👛 موجودی: {balance:,} تومان",
    "dash_new_service": "🛒 خرید سرویس جدید",
    "dash_back": "بازگشت به منوی اصلی",
})
TEXTS["ku"].update({
    "panel": "پانێلی بەکارهێنەر",
    "panel_btn": "📊 پانێلی بەکارهێنەر",
    "dash_title": "📊 پانێلی بەکارهێنەر\n\n👋 بەخێربێیت {name}\n\n💰 موجودی: {balance:,} تومان\n📦 خزمەتگوزارییە چالاکەکان: {count}\n\nیەکێک لە هەڵبژاردەکان هەڵبژێرە:",
    "dash_first_service": "➕ یەکەم خزمەتگوزاریت بکڕە",
    "dash_balance": "👛 موجودی: {balance:,} تومان",
    "dash_new_service": "🛒 کڕینی خزمەتگوزاری نوێ",
    "dash_back": "گەڕانەوە بۆ لیستی سەرەکی",
})
TEXTS["en"].update({
    "panel": "Dashboard",
    "panel_btn": "📊 Dashboard",
    "dash_title": "📊 User Dashboard\n\n👋 Hello {name}\n\n💰 Balance: {balance:,} Toman\n📦 Active services: {count}\n\nChoose an option below:",
    "dash_first_service": "➕ Buy your first service",
    "dash_balance": "👛 Balance: {balance:,} Toman",
    "dash_new_service": "🛒 Buy a new service",
    "dash_back": "Back to main menu",
})


def t(lang, key, **kwargs):
    if lang not in TEXTS:
        lang = "fa"
    text = TEXTS[lang].get(key, TEXTS["fa"].get(key, key))
    try:
        return text.format(**kwargs)
    except Exception:
        return text


# =========================================================
# ابزارهای عمومی
# =========================================================

BUTTON_STYLE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "button_style.json")
BUTTON_COLOR_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "button_colors.json")

BUTTON_STYLE_OPTIONS = {
    "default": "⚪ پیش‌فرض",
    "success": "🟢 سبز",
    "danger": "🔴 قرمز",
    "primary": "🔵 آبی",
}

# دکمه‌های اصلی قابل تنظیم از پنل مدیریت.
# مقدار callback_data همان چیزی است که خود ربات برای آن دکمه استفاده می‌کند.
BUTTON_COLOR_TARGETS = {
    "buy": "🛒 خرید سرویس",
    "trial": "🎁 تست رایگان",
    "my_services": "📦 سرویس‌های من",
    "renew": "🔄 تمدید سرویس",
    "referral": "👥 دعوت دوستان",
    "wallet": "💰 کیف پول",
    "support": "🎫 پشتیبانی",
    "language": "🌐 تغییر زبان",
    "charge_wallet": "💳 شارژ کیف پول",
    "wallet_history": "📜 تاریخچه کیف پول",
    "buy_monthly": "📅 خرید ماهانه",
    "unlimited": "♾️ سرویس نامحدود",
    "custom": "⚙️ سرویس سفارشی",
    "coupon": "🎟️ کد تخفیف",
    "new_ticket": "🎫 تیکت جدید",
    "home": "🏠 بازگشت / منوی اصلی",
    "dashboard": "📊 پنل کاربری",
    "admin_backup": "💾 بکاپ",
    "admin_add": "➕ افزودن سرویس",
    "admin_trial": "🎁 مدیریت تست",
    "admin_stock": "📦 موجودی",
    "admin_delete": "🗑 حذف سرویس",
    "admin_coupon": "🎟️ مدیریت کوپن",
    "admin_balance": "💰 موجودی کاربران",
    "admin_broadcast": "📢 ارسال همگانی",
    "admin_stats": "📊 آمار",
    "admin_orders": "🧾 سفارش‌ها",
    "admin_tickets": "🎫 تیکت‌ها",
}

# الگوهای دکمه‌های پویا؛ مثلاً paid_10 یا renewpaid_20.
BUTTON_COLOR_PATTERNS = {
    "pay_*": "💳 پرداخت",
    "paid_*": "✅ پرداخت ثبت‌شده",
    "renewpaid_*": "🔄 پرداخت تمدید",
    "walletpay_*": "💰 پرداخت از کیف پول",
    "approve_*": "✅ تأیید پرداخت",
    "reject_*": "❌ رد پرداخت",
    "paymentback_*": "↩️ بازگشت پرداخت",
    "delete_*": "🗑 حذف مورد",
    "renewminus_*": "➖ کاهش حجم تمدید",
}

def get_button_style():
    try:
        with open(BUTTON_STYLE_FILE, "r", encoding="utf-8") as f:
            value = json.load(f).get("style", "default")
            return value if value in BUTTON_STYLE_OPTIONS else "default"
    except Exception:
        return "default"

def set_button_style(style):
    if style not in BUTTON_STYLE_OPTIONS:
        style = "default"
    with open(BUTTON_STYLE_FILE, "w", encoding="utf-8") as f:
        json.dump({"style": style}, f, ensure_ascii=False, indent=2)
    return style

def get_button_color_map():
    try:
        with open(BUTTON_COLOR_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def set_button_color(callback_key, style):
    colors = get_button_color_map()
    if style == "default":
        colors.pop(callback_key, None)
    else:
        colors[callback_key] = style
    with open(BUTTON_COLOR_FILE, "w", encoding="utf-8") as f:
        json.dump(colors, f, ensure_ascii=False, indent=2)
    return style

def get_button_color(callback_data):
    data = str(callback_data or "")
    colors = get_button_color_map()

    # اولویت با تنظیم اختصاصی همان دکمه است.
    if data in colors and colors[data] in BUTTON_STYLE_OPTIONS:
        return colors[data]

    # بعد الگوهای اختصاصی دکمه‌های پویا.
    for pattern, _label in BUTTON_COLOR_PATTERNS.items():
        prefix = pattern[:-1] if pattern.endswith("*") else pattern
        if data.startswith(prefix) and pattern in colors and colors[pattern] in BUTTON_STYLE_OPTIONS:
            return colors[pattern]

    # اگر تنظیم اختصاصی نبود، استایل سراسری قبلی اعمال می‌شود.
    selected = get_button_style()
    if selected != "default":
        return selected

    # رفتار خودکار قبلی برای حالت پیش‌فرض.
    success_prefixes = ("pay_", "paid_", "renewpaid_", "walletpay_", "approve_")
    danger_prefixes = ("paymentback_", "reject_")
    success_exact = {"buy", "buy_monthly", "unlimited", "custom", "charge_wallet"}

    if data in success_exact or data.startswith(success_prefixes):
        return "success"
    if data == "home" or data.startswith(danger_prefixes):
        return "danger"

    return "default"

BUTTON_ICON_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "button_icons.json")

# آیکن (ایموجی پرمیوم) دکمه‌ها.
# کلید = callback_data دکمه (مثل buy) یا الگو (مثل pay_*)، مقدار = custom_emoji_id.
# از پنل ادمین/دستور /seticon هم می‌شود تنظیمش کرد؛ این دیکشنری فقط مقدار پیش‌فرض است.
DEFAULT_BUTTON_ICONS = {
    # "buy": "5368324170671202286",
}


def get_button_icon_map():
    icons = dict(DEFAULT_BUTTON_ICONS)
    try:
        with open(BUTTON_ICON_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                icons.update({str(k): str(v) for k, v in data.items() if str(v).isdigit()})
    except Exception:
        pass
    return icons


def set_button_icon(key, emoji_id):
    try:
        with open(BUTTON_ICON_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                data = {}
    except Exception:
        data = {}
    if emoji_id:
        data[key] = str(emoji_id)
    else:
        data.pop(key, None)
    with open(BUTTON_ICON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_button_icon(callback_data):
    data = str(callback_data or "")
    if not data:
        return None
    icons = get_button_icon_map()
    if data in icons:
        return icons[data]
    for key, emoji_id in icons.items():
        if key.endswith("*") and data.startswith(key[:-1]):
            return emoji_id
    return None


def strip_leading_emoji(text):
    # وقتی آیکن پرمیوم روی دکمه هست، ایموجی معمولیِ ابتدای متن حذف می‌شود تا دوتا نشان داده نشود.
    stripped = re.sub(r"^[^\w]+", "", text or "")
    return stripped or text


BUTTON_PACK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "button_pack.json")
_PACK_CACHE = {"mtime": None, "data": {"set": "", "map": {}}}


def _norm_emoji(value):
    return (value or "").replace("\ufe0f", "").strip()


def get_icon_pack():
    """پک ایموجی پرمیومِ فعال: {"set": نام پک, "map": {ایموجی معمولی: custom_emoji_id}}"""
    empty = {"set": "", "map": {}}
    try:
        mtime = os.path.getmtime(BUTTON_PACK_FILE)
    except OSError:
        return empty
    if _PACK_CACHE["mtime"] != mtime:
        try:
            with open(BUTTON_PACK_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict) or not isinstance(data.get("map"), dict):
                data = empty
        except Exception:
            data = empty
        _PACK_CACHE["mtime"] = mtime
        _PACK_CACHE["data"] = data
    return _PACK_CACHE["data"]


def set_icon_pack(name, mapping):
    with open(BUTTON_PACK_FILE, "w", encoding="utf-8") as f:
        json.dump({"set": name, "map": mapping}, f, ensure_ascii=False)
    _PACK_CACHE["mtime"] = None


def clear_icon_pack():
    try:
        os.remove(BUTTON_PACK_FILE)
    except OSError:
        pass
    _PACK_CACHE["mtime"] = None


def resolve_button_icon(text, key=None):
    """
    آیکن دکمه را تعیین می‌کند و (متن جدید، آیدی ایموجی یا None) برمی‌گرداند.
    اولویت: ۱) آیکنی که برای همین دکمه دستی تنظیم شده  ۲) ایموجیِ ابتدای متن، اگر در پک فعال باشد.
    """
    text = text or ""
    icon = get_button_icon(key) if key else None
    if icon:
        return strip_leading_emoji(text), icon
    head, sep, rest = text.partition(" ")
    if sep and rest.strip():
        icon = get_icon_pack()["map"].get(_norm_emoji(head))
        if icon:
            return rest.strip(), icon
    return text, None


def styled_copy_card_button():
    style = get_button_color("copy_card")
    kwargs = {"copy_text": CopyTextButton(CARD_NUMBER)}
    text = "📋 کپی شماره کارت"
    if style != "default":
        kwargs["style"] = style
    text, icon = resolve_button_icon(text, "copy_card")
    if icon:
        kwargs["icon_custom_emoji_id"] = icon
    return InlineKeyboardButton(text, **kwargs)

def button_style_icon(style):
    return {
        "default": "⚪",
        "success": "🟢",
        "danger": "🔴",
        "primary": "🔵",
    }.get(style, "⚪")

def styled_inline_button(text, callback_data=None, force_style=None, icon_key=None, **kwargs):
    style = force_style or get_button_color(callback_data)
    if style != "default":
        kwargs["style"] = style
    if "icon_custom_emoji_id" not in kwargs:
        text, icon = resolve_button_icon(text, icon_key or callback_data)
        if icon:
            kwargs["icon_custom_emoji_id"] = icon
    return InlineKeyboardButton(text=text, callback_data=callback_data, **kwargs)

def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# =========================================================
# Telegram Rich Messages (Bot API 10.1+)
# =========================================================
#
# Rich Messages are sent directly through Bot API because older/newer
# python-telegram-bot installations may not expose the new methods yet.
# If Telegram rejects a rich request, we transparently fall back to the
# normal python-telegram-bot message API so the bot remains usable.
RICH_MESSAGES_ENABLED = os.getenv("RICH_MESSAGES_ENABLED", "true").lower() not in {
    "0", "false", "no", "off"
}
RICH_API_TIMEOUT = float(os.getenv("RICH_API_TIMEOUT", "20"))


def _rich_button_html(button):
    """Convert an InlineKeyboardButton into Telegram Rich HTML."""
    import html

    label = html.escape(getattr(button, "text", "") or "Button")
    custom_emoji_id = getattr(button, "icon_custom_emoji_id", None)
    if custom_emoji_id:
        label = f'<tg-emoji emoji-id="{html.escape(str(custom_emoji_id))}">🔘</tg-emoji> {label}'

    style = getattr(button, "style", None)
    style_attr = f' style="{html.escape(style)}"' if style in {
        "danger", "success", "primary", "link"
    } else ""

    # URL button
    url = getattr(button, "url", None)
    if url:
        return f'<tg-button type="url"{style_attr} url="{html.escape(url, quote=True)}">{label}</tg-button>'

    # Web App button
    web_app = getattr(button, "web_app", None)
    if web_app and getattr(web_app, "url", None):
        return f'<tg-button type="web_app"{style_attr} url="{html.escape(web_app.url, quote=True)}">{label}</tg-button>'

    # Copy-text button
    copy_text = getattr(button, "copy_text", None)
    if copy_text and getattr(copy_text, "text", None) is not None:
        return f'<tg-button type="copy_text"{style_attr} text="{html.escape(copy_text.text, quote=True)}">{label}</tg-button>'

    # Callback button
    callback_data = getattr(button, "callback_data", None)
    if callback_data is not None:
        return f'<tg-button type="callback_data"{style_attr} data="{html.escape(str(callback_data), quote=True)}">{label}</tg-button>'

    # Login URL / switch-query buttons if present in the installed PTB version.
    login_url = getattr(button, "login_url", None)
    if login_url and getattr(login_url, "url", None):
        return f'<tg-button type="login_url"{style_attr} url="{html.escape(login_url.url, quote=True)}">{label}</tg-button>'

    switch_inline = getattr(button, "switch_inline_query", None)
    if switch_inline is not None:
        return f'<tg-button type="switch_inline_query"{style_attr} query="{html.escape(str(switch_inline), quote=True)}">{label}</tg-button>'

    switch_current = getattr(button, "switch_inline_query_current_chat", None)
    if switch_current is not None:
        return f'<tg-button type="switch_inline_query_current_chat"{style_attr} query="{html.escape(str(switch_current), quote=True)}">{label}</tg-button>'

    return None


def _rich_markup_html(reply_markup):
    """Turn only InlineKeyboardMarkup into Rich Message button rows."""
    if not isinstance(reply_markup, InlineKeyboardMarkup):
        return None

    rows = []
    for row in (reply_markup.inline_keyboard or []):
        buttons = []
        for button in row:
            rendered = _rich_button_html(button)
            if rendered:
                buttons.append(rendered)
        if buttons:
            rows.append("<tg-button-row>" + "".join(buttons) + "</tg-button-row>")
    return "\n".join(rows) if rows else None


def _polish_bot_text(text):
    """Make bot text clean and mobile-friendly: no decorative separator lines or raw formatting tags."""
    import re
    text = "" if text is None else str(text)
    # Remove decorative separator-only lines (━, ─, —, _, -, =, etc.).
    text = re.sub(r"(?m)^[ \t]*(?:[━─—_\-=]){3,}[ \t]*$", "", text)
    # Never let legacy Telegram formatting tags leak as visible text.
    text = re.sub(r"</?(?:b|strong|i|em|u|ins|s|strike|del)>", "", text, flags=re.I)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _rich_html_from_mixed_text(text):
    """Escape user text while preserving the bot's intentional simple HTML tags."""
    import html
    import re
    placeholders = {}
    allowed = re.compile(r"</?(?:b|strong|i|em|u|s|code|pre|blockquote|p|br|ul|ol|li|details|summary)(?:\s[^>]*)?>", re.I)

    def hold(match):
        key = f"\x00RICH_TAG_{len(placeholders)}\x00"
        placeholders[key] = match.group(0)
        return key

    held = allowed.sub(hold, text)
    escaped = html.escape(held, quote=False)
    for key, tag in placeholders.items():
        escaped = escaped.replace(html.escape(key, quote=False), tag)
    return escaped


def _is_rtl_text(text):
    import re
    return bool(re.search(r"[\u0600-\u06ff]", text or ""))


def _rich_content(text, parse_mode=None, reply_markup=None):
    """Build clean Telegram Rich Message content with correct RTL handling."""
    import html

    text = _polish_bot_text(text)
    mode = str(parse_mode or "").upper()

    if mode in {"MARKDOWN", "MARKDOWNV2"}:
        content = text
        field = "markdown"
    elif mode == "HTML":
        content = text
        field = "html"
    else:
        content = _rich_html_from_mixed_text(text)
        field = "html"

    button_html = _rich_markup_html(reply_markup)
    if button_html:
        content += "\n\n" + button_html

    return {field: content, "is_rtl": _is_rtl_text(text)}


def _telegram_api_call(method, payload):
    """Synchronous low-level Bot API call used by the Rich Message bridge."""
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN تنظیم نشده است.")
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urlrequest.Request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urlrequest.urlopen(req, timeout=RICH_API_TIMEOUT) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("ok"):
        raise RuntimeError(result.get("description", f"Telegram {method} failed"))
    return result.get("result")


def _rich_only_inline_markup(reply_markup):
    """Disable ordinary Telegram reply keyboards; keep only inline Rich buttons."""
    return reply_markup if isinstance(reply_markup, InlineKeyboardMarkup) else None


async def send_rich_message(bot, chat_id, text, reply_markup=None,
                            parse_mode=None, **kwargs):
    """Send a persistent Telegram Rich Message, with automatic fallback."""
    reply_markup = _rich_only_inline_markup(reply_markup)
    if not RICH_MESSAGES_ENABLED:
        return await bot.send_message(
            chat_id=chat_id, text=text, reply_markup=reply_markup,
            parse_mode=parse_mode, **kwargs
        )

    payload = {
        "chat_id": chat_id,
        "rich_message": _rich_content(text, parse_mode, reply_markup),
    }
    for key in (
        "disable_notification", "protect_content", "message_thread_id",
        "business_connection_id", "direct_messages_topic_id",
        "message_effect_id", "allow_paid_broadcast",
    ):
        if key in kwargs and kwargs[key] is not None:
            payload[key] = kwargs[key]

    try:
        result = await asyncio.to_thread(_telegram_api_call, "sendRichMessage", payload)
        return result
    except Exception as rich_error:
        print(f"Rich send fallback: {type(rich_error).__name__}: {rich_error}")
        fallback_text = _polish_bot_text(text)
        fallback_mode = parse_mode
        if str(fallback_mode or "").upper() == "HTML":
            fallback_text = re.sub(r"</?(?:b|strong|i|em|u|ins|s|strike|del)(?:\s[^>]*)?>", "", fallback_text, flags=re.I)
            fallback_mode = None
        return await bot.send_message(
            chat_id=chat_id, text=fallback_text, reply_markup=reply_markup,
            parse_mode=fallback_mode, **kwargs
        )


async def rich_reply(message, text, reply_markup=None, parse_mode=None, **kwargs):
    return await send_rich_message(
        message.get_bot(), message.chat_id, text,
        reply_markup=reply_markup, parse_mode=parse_mode, **kwargs
    )


async def rich_edit(query, text, reply_markup=None, parse_mode=None, **kwargs):
    """Edit an existing bot message as a Rich Message, with fallback."""
    if not RICH_MESSAGES_ENABLED:
        return await query.message.edit_text(
            text=text, reply_markup=reply_markup,
            parse_mode=parse_mode, **kwargs
        )

    message = query.message
    if not message:
        return await query.answer("پیام قابل ویرایش نیست.", show_alert=True)

    payload = {
        "chat_id": message.chat_id,
        "message_id": message.message_id,
        "rich_message": _rich_content(text, parse_mode, reply_markup),
    }
    if message.business_connection_id:
        payload["business_connection_id"] = message.business_connection_id

    try:
        result = await asyncio.to_thread(_telegram_api_call, "editMessageText", payload)
        return result
    except Exception as rich_error:
        print(f"Rich edit fallback: {type(rich_error).__name__}: {rich_error}")
        fallback_text = _polish_bot_text(text)
        fallback_mode = parse_mode
        if str(fallback_mode or "").upper() == "HTML":
            fallback_text = re.sub(r"</?(?:b|strong|i|em|u|ins|s|strike|del)(?:\s[^>]*)?>", "", fallback_text, flags=re.I)
            fallback_mode = None
        return await message.edit_text(
            text=fallback_text, reply_markup=reply_markup,
            parse_mode=fallback_mode, **kwargs
        )


async def rich_reply_text(message, text, reply_markup=None, parse_mode=None, **kwargs):
    """Drop-in replacement for Message.reply_text for textual bot replies."""
    return await rich_reply(
        message, text, reply_markup=reply_markup,
        parse_mode=parse_mode, **kwargs
    )


async def rich_draft(bot, chat_id, draft_id, html, can_stop=True, keep_on_stop=False):
    """Stream a temporary Rich Message draft (useful for AI-generated replies)."""
    payload = {
        "chat_id": chat_id,
        "draft_id": int(draft_id) or 1,
        "rich_message": {"html": html},
        "can_stop": bool(can_stop),
        "keep_on_stop": bool(keep_on_stop),
    }
    return await asyncio.to_thread(
        _telegram_api_call, "sendRichMessageDraft", payload
    )


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
        (user_id, username, first_name, created_at, language, balance)
        VALUES (?, ?, ?, ?, NULL, 0)
    """, (user.id, user.username or "", user.first_name or "", now_text()))
    conn.execute("""
        UPDATE users SET username = ?, first_name = ? WHERE user_id = ?
    """, (user.username or "", user.first_name or "", user.id))
    conn.commit()
    conn.close()


def get_user_language(user_id):
    conn = get_db()
    row = conn.execute("SELECT language FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    if row and row["language"] in LANGUAGES:
        return row["language"]
    return None


def set_user_language(user_id, language):
    if language not in LANGUAGES:
        return
    conn = get_db()
    conn.execute("UPDATE users SET language = ? WHERE user_id = ?", (language, user_id))
    conn.commit()
    conn.close()


def language_keyboard():
    return InlineKeyboardMarkup([
        [styled_inline_button("🇮🇷 فارسی", callback_data="language_fa")],
        [styled_inline_button("🟢 کوردی", callback_data="language_ku")],
        [styled_inline_button("🇬🇧 English", callback_data="language_en")],
    ])


async def show_language_selector_message(message):
    await rich_reply_text(message, TEXTS["fa"]["language_title"], reply_markup=language_keyboard())


def clear_user_states(context):
    keys = [
        "waiting_custom_volume", "waiting_coupon", "waiting_ticket_message",
        "ticket_id", "custom_volume", "custom_price", "coupon_code",
        "renew_order_id", "renew_volume", "renew_price",
        "admin_waiting_volume", "admin_waiting_link", "admin_add_volume",
        "admin_waiting_trial_link", "admin_waiting_coupon", "admin_broadcast",
        "admin_ticket_id", "admin_waiting_ticket_reply", "last_order_id",
        "waiting_charge_amount", "charge_amount", "admin_waiting_balance_user",
        "admin_balance_user_id", "admin_waiting_balance_amount",
        "pg_waiting_url", "pg_waiting_username", "pg_waiting_password"
    ]
    for key in keys:
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
            expires_at TEXT,
            is_charge INTEGER DEFAULT 0,
            pg_username TEXT,
            pg_subscription_url TEXT,
            unlimited_hwid INTEGER
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
            language TEXT,
            balance INTEGER DEFAULT 0
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

    conn.execute("""
        CREATE TABLE IF NOT EXISTS wallet_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            type TEXT NOT NULL,
            description TEXT,
            order_id INTEGER,
            created_at TEXT NOT NULL
        )
    """)

    # اتصال اختیاری PasarGuard؛ حالت پیش‌فرض همچنان «دستی» است.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pasarguard_config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            base_url TEXT NOT NULL,
            username TEXT NOT NULL,
            password_enc TEXT NOT NULL,
            access_token TEXT,
            token_expires_at TEXT,
            enabled INTEGER DEFAULT 1,
            mode TEXT DEFAULT 'manual',
            group_id INTEGER,
            group_name TEXT,
            template_id INTEGER,
            template_name TEXT,
            updated_at TEXT NOT NULL
        )
    """)

    conn.commit()

    # سازگاری اتصال PasarGuard با نسخه‌های قبلی
    for col, default in [
        ("template_id", "INTEGER"),
        ("template_name", "TEXT"),
    ]:
        try:
            conn.execute(f"ALTER TABLE pasarguard_config ADD COLUMN {col} {default}")
        except sqlite3.OperationalError:
            pass

    # سازگاری
    for col, default in [
        ("expires_at", "TEXT"),
        ("is_charge", "INTEGER DEFAULT 0"),
        ("subscription_id", "INTEGER"),
        ("approved_at", "TEXT"),
        ("pg_username", "TEXT"),
        ("pg_subscription_url", "TEXT"),
        ("unlimited_hwid", "INTEGER"),
    ]:
        try:
            conn.execute(f"ALTER TABLE orders ADD COLUMN {col} {default}")
        except sqlite3.OperationalError:
            pass

    for col, default in [
        ("referred_by", "INTEGER"),
        ("referral_rewarded", "INTEGER DEFAULT 0"),
        ("language", "TEXT"),
        ("balance", "INTEGER DEFAULT 0"),
    ]:
        try:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col} {default}")
        except sqlite3.OperationalError:
            pass

    conn.commit()
    conn.close()


# =========================================================
# اتصال اختیاری PasarGuard
# =========================================================

_PG_TOKEN_CACHE = {"token": None, "expires_at": 0.0}
_PG_TOKEN_LOCK = threading.Lock()
_PG_ORDER_LOCK = None


def _pg_now_epoch():
    return datetime.now().timestamp()


def _pg_crypto_key():
    seed = (BOT_TOKEN or "") + "|HanzuVPN|PasarGuard|v1"
    return hashlib.sha256(seed.encode("utf-8")).digest()


def _pg_xor_stream(data, key, nonce):
    out = bytearray(len(data))
    pos = 0
    counter = 0
    while pos < len(data):
        block = hmac.new(key, nonce + counter.to_bytes(8, "big"), hashlib.sha256).digest()
        take = min(len(block), len(data) - pos)
        for i in range(take):
            out[pos + i] = data[pos + i] ^ block[i]
        pos += take
        counter += 1
    return bytes(out)


def _pg_encrypt_secret(value):
    raw = (value or "").encode("utf-8")
    nonce = os.urandom(16)
    cipher = _pg_xor_stream(raw, _pg_crypto_key(), nonce)
    tag = hmac.new(_pg_crypto_key(), nonce + cipher, hashlib.sha256).digest()[:16]
    return base64.urlsafe_b64encode(nonce + tag + cipher).decode("ascii")


def _pg_decrypt_secret(value):
    try:
        blob = base64.urlsafe_b64decode((value or "").encode("ascii"))
        if len(blob) < 32:
            return ""
        nonce, tag, cipher = blob[:16], blob[16:32], blob[32:]
        expected = hmac.new(_pg_crypto_key(), nonce + cipher, hashlib.sha256).digest()[:16]
        if not hmac.compare_digest(tag, expected):
            return ""
        return _pg_xor_stream(cipher, _pg_crypto_key(), nonce).decode("utf-8")
    except Exception:
        return ""


def get_pasarguard_config():
    conn = get_db()
    row = conn.execute("SELECT * FROM pasarguard_config WHERE id = 1").fetchone()
    conn.close()
    return row


def get_pasarguard_mode():
    row = get_pasarguard_config()
    if not row or not row["enabled"]:
        return "manual"
    return row["mode"] or "manual"


def _pg_url(base, path):
    base = (base or "").strip().rstrip("/") + "/"
    return urljoin(base, path.lstrip("/"))


def _pg_http(method, url, headers=None, json_body=None, form=None, timeout=12):
    data = None
    req_headers = dict(headers or {})
    if json_body is not None:
        data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    elif form is not None:
        from urllib.parse import urlencode
        data = urlencode(form).encode("utf-8")
        req_headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urlrequest.Request(url, data=data, headers=req_headers, method=method.upper())
    try:
        with urlrequest.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(body) if body else {}
            except Exception:
                payload = {"raw": body}
            return response.status, payload
    except Exception as exc:
        status = getattr(exc, "code", None)
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
            payload = json.loads(body) if body else {}
        except Exception:
            payload = {}
        return int(status or 0), payload or {"detail": str(exc)}


def _pg_login_sync(force=False):
    cfg = get_pasarguard_config()
    if not cfg:
        raise RuntimeError("پنل PasarGuard متصل نیست.")
    now = _pg_now_epoch()
    with _PG_TOKEN_LOCK:
        if not force and _PG_TOKEN_CACHE.get("token") and _PG_TOKEN_CACHE.get("expires_at", 0) > now + 60:
            return _PG_TOKEN_CACHE["token"]
        token = cfg["access_token"] or ""
        try:
            expires = datetime.strptime(cfg["token_expires_at"], "%Y-%m-%d %H:%M:%S").timestamp() if cfg["token_expires_at"] else 0
        except Exception:
            expires = 0
        if not force and token and expires > now + 60:
            _PG_TOKEN_CACHE.update(token=token, expires_at=expires)
            return token

        password = _pg_decrypt_secret(cfg["password_enc"])
        if not password:
            raise RuntimeError("رمز اتصال پنل قابل بازیابی نیست؛ اتصال را دوباره ثبت کنید.")
        status, payload = _pg_http(
            "POST", _pg_url(cfg["base_url"], "/api/admin/token"),
            form={"username": cfg["username"], "password": password, "grant_type": "password"},
            timeout=12,
        )
        if status != 200 or not payload.get("access_token"):
            detail = payload.get("detail") or payload.get("message") or "ورود به PasarGuard ناموفق بود."
            raise RuntimeError(str(detail)[:300])
        token = str(payload["access_token"])
        # توکن را کوتاه‌مدت cache می‌کنیم تا هر خرید login مجدد نزند.
        exp = now + 25 * 60
        try:
            parts = token.split(".")
            if len(parts) == 3:
                raw = parts[1] + "=" * (-len(parts[1]) % 4)
                claims = json.loads(base64.urlsafe_b64decode(raw.encode("ascii")).decode("utf-8"))
                if claims.get("exp"):
                    exp = float(claims["exp"])
        except Exception:
            pass
        conn = get_db()
        conn.execute("UPDATE pasarguard_config SET access_token=?, token_expires_at=?, updated_at=? WHERE id=1",
                     (token, datetime.fromtimestamp(exp).strftime("%Y-%m-%d %H:%M:%S"), now_text()))
        conn.commit(); conn.close()
        _PG_TOKEN_CACHE.update(token=token, expires_at=exp)
        return token


def _pg_request_sync(method, path, json_body=None, retry=True):
    cfg = get_pasarguard_config()
    if not cfg:
        raise RuntimeError("پنل PasarGuard متصل نیست.")
    token = _pg_login_sync(False)
    status, payload = _pg_http(method, _pg_url(cfg["base_url"], path),
                               headers={"Authorization": f"Bearer {token}"},
                               json_body=json_body, timeout=15)
    if status == 401 and retry:
        token = _pg_login_sync(True)
        status, payload = _pg_http(method, _pg_url(cfg["base_url"], path),
                                   headers={"Authorization": f"Bearer {token}"},
                                   json_body=json_body, timeout=15)
    if status < 200 or status >= 300:
        detail = payload.get("detail") or payload.get("message") or payload.get("error") or str(payload)
        raise RuntimeError(f"PasarGuard API {status}: {str(detail)[:350]}")
    return payload


def _pg_extract_list(payload, key):
    if isinstance(payload, dict):
        value = payload.get(key)
        if isinstance(value, list):
            return value
        for k in ("items", "results", "data"):
            value = payload.get(k)
            if isinstance(value, list):
                return value
            if isinstance(value, dict) and isinstance(value.get(key), list):
                return value[key]
    return payload if isinstance(payload, list) else []


def pg_get_groups_sync():
    try:
        payload = _pg_request_sync("GET", "/api/groups")
    except Exception as first:
        try:
            payload = _pg_request_sync("GET", "/api/groups/simple")
        except Exception:
            raise first
    groups = _pg_extract_list(payload, "groups")
    return [{"id": int(g.get("id")), "name": str(g.get("name") or g.get("label") or f"Group {g.get('id')}")}
            for g in groups if isinstance(g, dict) and g.get("id") is not None]


def pg_get_templates_sync():
    """Return templates allowed for the connected admin.
    PasarGuard RBAC exposes full templates to sudo and simple templates to operators.
    """
    first_error = None
    # RBAC operators are intentionally allowed to use the simple endpoint.
    try:
        payload = _pg_request_sync("GET", "/api/user_templates/simple")
        templates = _pg_extract_list(payload, "user_templates")
        if not templates:
            templates = _pg_extract_list(payload, "templates")
        if templates:
            return [
                {
                    "id": int(t.get("id")),
                    "name": str(t.get("name") or t.get("label") or f"Template {t.get('id')}"),
                    "group_ids": [],
                    "is_disabled": False,
                }
                for t in templates if isinstance(t, dict) and t.get("id") is not None
            ]
    except Exception as exc:
        first_error = exc

    try:
        payload = _pg_request_sync("GET", "/api/user_templates")
        templates = _pg_extract_list(payload, "user_templates")
        if not templates:
            templates = _pg_extract_list(payload, "templates")
        return [
            {
                "id": int(t.get("id")),
                "name": str(t.get("name") or t.get("label") or f"Template {t.get('id')}"),
                "group_ids": [],
                "is_disabled": False,
            }
            for t in templates if isinstance(t, dict) and t.get("id") is not None
        ]
    except Exception:
        if first_error:
            raise first_error
        raise


def pg_get_selected_template_sync():
    cfg = get_pasarguard_config()
    if not cfg:
        raise RuntimeError("پنل PasarGuard متصل نیست.")
    templates = pg_get_templates_sync()
    if not templates:
        raise RuntimeError("هیچ User Template مجازی برای این مدیر در PasarGuard پیدا نشد.")

    selected_id = cfg["template_id"]
    if selected_id:
        selected = next((t for t in templates if t["id"] == int(selected_id) and not t.get("is_disabled")), None)
        if selected:
            return selected

    group_id = cfg["group_id"]
    # اگر اطلاعات کامل template در دسترس باشد، template هم‌گروه را ترجیح بده.
    if group_id:
        matching = [t for t in templates if int(group_id) in t.get("group_ids", []) and not t.get("is_disabled")]
        if matching:
            return matching[0]

    usable = [t for t in templates if not t.get("is_disabled")]
    if not usable:
        raise RuntimeError("تمام User Templateهای قابل دسترسی غیرفعال هستند.")
    return usable[0]


def set_pasarguard_template(template_id, template_name):
    conn = get_db()
    conn.execute("UPDATE pasarguard_config SET template_id=?, template_name=?, updated_at=? WHERE id=1",
                 (int(template_id), str(template_name), now_text()))
    conn.commit()
    conn.close()


def pg_create_user_sync(volume, username, group_id, note=""):
    cfg = get_pasarguard_config()
    if not cfg:
        raise RuntimeError("پنل PasarGuard متصل نیست.")
    data_limit = 0 if is_unlimited_volume(volume) else int(float(_normalize_volume(volume) or 0)) * 1024 ** 3
    expire = (datetime.now() + timedelta(days=SERVICE_DAYS)).replace(microsecond=0).isoformat()
    payload = {
        "username": username,
        "proxy_settings": {},
        "expire": expire,
        "data_limit": data_limit,
        "data_limit_reset_strategy": "no_reset",
        "status": "active",
        "group_ids": [int(group_id)],
        "note": note or "HanzuVPN",
    }
    return _pg_request_sync("POST", "/api/user", payload)


def pg_create_user_from_template_sync(username, note=""):
    template = pg_get_selected_template_sync()
    # ثبت انتخاب خودکار در DB تا خریدهای بعدی نیاز به جستجوی template نداشته باشند.
    set_pasarguard_template(template["id"], template["name"])
    payload = _pg_request_sync("POST", "/api/user/from_template", {
        "user_template_id": int(template["id"]),
        "username": username,
        "note": note or "HanzuVPN",
    })
    return payload, template


def pg_update_user_limits_sync(username, payload, volume, group_id, note=""):
    """Apply the exact HanzuVPN plan after template creation.

    Important: do NOT rewrite group_ids here. RBAC roles may be allowed to
    create from a template while being forbidden from changing groups after
    creation. The selected template already supplies its groups.
    """
    data_limit = 0 if is_unlimited_volume(volume) else int(float(_normalize_volume(volume) or 0)) * 1024 ** 3
    expire = (datetime.now() + timedelta(days=SERVICE_DAYS)).replace(microsecond=0).isoformat()
    update_payload = {
        "data_limit": data_limit,
        "data_limit_reset_strategy": "no_reset",
        "expire": expire,
        "status": "active",
        "note": note or "HanzuVPN",
    }
    user_id = _pg_find_value(payload, ["id", "user_id", "userId"])
    errors = []
    if user_id is not None:
        try:
            return _pg_request_sync("PUT", f"/api/user/by-id/{int(user_id)}", update_payload)
        except Exception as first:
            errors.append(str(first))
    try:
        return _pg_request_sync("PUT", f"/api/user/{quote(str(username), safe='')}", update_payload)
    except Exception as second:
        errors.append(str(second))
    raise RuntimeError(" | ".join(errors)[:500])

def _pg_user_plan_matches(payload, volume):
    """Best-effort verification for templates that already contain the exact plan."""
    wanted_limit = 0 if is_unlimited_volume(volume) else int(float(_normalize_volume(volume) or 0)) * 1024 ** 3
    actual_limit = _pg_find_value(payload, ["data_limit", "dataLimit"])
    if actual_limit is not None:
        try:
            if int(actual_limit) != int(wanted_limit):
                return False
        except Exception:
            return False
    # If the API response doesn't expose data_limit, don't claim a match.
    else:
        return False
    return True

def _pg_find_value(obj, names):
    if isinstance(obj, dict):
        for n in names:
            if obj.get(n):
                return obj[n]
        for v in obj.values():
            found = _pg_find_value(v, names)
            if found:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _pg_find_value(v, names)
            if found:
                return found
    return None


def pg_create_order_service_sync(order):
    cfg = get_pasarguard_config()
    if not cfg or not cfg["enabled"]:
        raise RuntimeError("پنل PasarGuard فعال نیست.")
    group_id = cfg["group_id"]
    if not group_id:
        raise RuntimeError("گروه پیش‌فرض PasarGuard انتخاب نشده است.")
    username = f"hz_{order['user_id']}_{order['id']}_{hashlib.sha1(os.urandom(8)).hexdigest()[:6]}"
    note = f"HanzuVPN order #{order['id']}"

    try:
        payload = pg_create_user_sync(order["volume"], username, int(group_id), note)
    except Exception as direct_error:
        # در RBAC جدید، ممکن است این مدیر اجازه ساخت مستقیم نداشته باشد
        # و فقط اجازه ساخت از Template داشته باشد. در این حالت خودکار Template را امتحان می‌کنیم.
        error_text = str(direct_error).lower()
        # هر خطای 4xx ساخت مستقیم می‌تواند ناشی از RBAC/Template اجباری باشد؛
        # به‌جای توقف، یک‌بار مسیر Template را امتحان می‌کنیم. خطاهای شبکه/5xx
        # همچنان همان‌جا گزارش می‌شوند تا ربات بی‌دلیل درخواست اضافه نزند.
        template_related = any(x in error_text for x in (
            "template", "require_template", "not allowed", "forbidden", "permission", "403", "400", "405", "422"
        ))
        if not template_related:
            raise
        try:
            payload, template = pg_create_user_from_template_sync(username, note)
            # Template کاربر را می‌سازد. اگر خودش دقیقاً همان حجم سفارش را دارد،
            # دیگر PUT اضافی نمی‌زنیم؛ این برای RBAC محدود مهم است.
            final_username = _pg_find_value(payload, ["username"]) or username
            if not _pg_user_plan_matches(payload, order["volume"]):
                payload2 = pg_update_user_limits_sync(final_username, payload, order["volume"], int(group_id), note)
                if isinstance(payload2, dict):
                    merged = dict(payload)
                    merged.update(payload2)
                    payload = merged
        except Exception as template_error:
            raise RuntimeError(
                f"ساخت مستقیم ناموفق بود: {str(direct_error)[:220]} | "
                f"ساخت از Template هم ناموفق بود: {str(template_error)[:320]}"
            )

    sub = _pg_find_value(payload, ["subscription_url", "subscriptionUrl", "sub_url", "subscription"])
    final_username = _pg_find_value(payload, ["username"]) or username
    if not sub:
        raise RuntimeError("PasarGuard کاربر را ساخت اما Subscription URL برنگرداند.")

    sub = str(sub).strip()
    if sub.startswith("/"):
        base_url = str(cfg.get("base_url") or "").rstrip("/")
        if base_url:
            sub = base_url + sub
    elif not sub.startswith(("http://", "https://")):
        base_url = str(cfg.get("base_url") or "").rstrip("/")
        if base_url:
            sub = base_url + "/" + sub.lstrip("/")

    return {"username": str(final_username), "subscription_url": sub}

def save_pasarguard_connection(base_url, username, password):
    base_url = base_url.strip().rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        raise ValueError("آدرس پنل باید با http:// یا https:// شروع شود.")
    enc = _pg_encrypt_secret(password)
    conn = get_db()
    conn.execute("""
        INSERT INTO pasarguard_config
        (id, base_url, username, password_enc, access_token, token_expires_at, enabled, mode, group_id, group_name, template_id, template_name, updated_at)
        VALUES (1, ?, ?, ?, NULL, NULL, 1, 'manual', NULL, NULL, NULL, NULL, ?)
        ON CONFLICT(id) DO UPDATE SET base_url=excluded.base_url, username=excluded.username, password_enc=excluded.password_enc, access_token=NULL, token_expires_at=NULL, enabled=1, mode='manual', group_id=NULL, group_name=NULL, template_id=NULL, template_name=NULL, updated_at=excluded.updated_at
    """, (base_url, username.strip(), enc, now_text()))
    conn.commit(); conn.close()
    with _PG_TOKEN_LOCK:
        _PG_TOKEN_CACHE.update(token=None, expires_at=0)


def set_pasarguard_group(group_id, group_name):
    conn = get_db()
    conn.execute("UPDATE pasarguard_config SET group_id=?, group_name=?, updated_at=? WHERE id=1", (int(group_id), str(group_name), now_text()))
    conn.commit(); conn.close()


def set_pasarguard_mode(mode):
    if mode not in {"manual", "panel", "fallback"}:
        return
    conn = get_db(); conn.execute("UPDATE pasarguard_config SET mode=?, enabled=1, updated_at=? WHERE id=1", (mode, now_text())); conn.commit(); conn.close()


def disable_pasarguard():
    conn = get_db(); conn.execute("UPDATE pasarguard_config SET enabled=0, mode='manual', updated_at=? WHERE id=1", (now_text(),)); conn.commit(); conn.close()
    with _PG_TOKEN_LOCK:
        _PG_TOKEN_CACHE.update(token=None, expires_at=0)


def _pg_groups_text(groups):
    return groups


# =========================================================
# کیف پول
# =========================================================

def get_balance(user_id):
    conn = get_db()
    row = conn.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return row["balance"] if row and row["balance"] is not None else 0


def change_balance(user_id, amount, type_, description="", order_id=None):
    conn = get_db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("UPDATE users SET balance = COALESCE(balance, 0) + ? WHERE user_id = ?", (amount, user_id))
        conn.execute("""
            INSERT INTO wallet_transactions
            (user_id, amount, type, description, order_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, amount, type_, description, order_id, now_text()))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


def get_wallet_history(user_id, limit=15):
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM wallet_transactions
        WHERE user_id = ?
        ORDER BY id DESC LIMIT ?
    """, (user_id, limit)).fetchall()
    conn.close()
    return rows


# =========================================================
# منوی اصلی
# =========================================================

def home_keyboard(user_id):
    lang = get_user_language(user_id) or "fa"
    keyboard = [
        [styled_inline_button(t(lang, "panel_btn"), callback_data="dashboard")],
        [
            styled_inline_button(t(lang, "buy"), callback_data="buy"),
            styled_inline_button(t(lang, "trial"), callback_data="trial"),
        ],
        [
            styled_inline_button(t(lang, "services"), callback_data="my_services"),
            styled_inline_button(t(lang, "renew"), callback_data="renew"),
        ],
        [
            styled_inline_button(t(lang, "referral"), callback_data="referral"),
            styled_inline_button(t(lang, "wallet"), callback_data="wallet"),
        ],
        [
            styled_inline_button(t(lang, "support"), callback_data="support"),
            styled_inline_button(t(lang, "language"), callback_data="language"),
        ],
    ]
    if user_id == ADMIN_ID:
        keyboard.append([styled_inline_button(t(lang, "admin"), callback_data="admin")])
    if MENU_ONE_PER_ROW:
        keyboard = [[button] for row in keyboard for button in row]
    return InlineKeyboardMarkup(keyboard)


async def show_home(query, user_id):
    lang = get_user_language(user_id) or "fa"
    await rich_edit(query, t(lang, "welcome"), reply_markup=home_keyboard(user_id))


async def send_home(message, user_id):
    lang = get_user_language(user_id) or "fa"
    # نمایش منوی اصلی با همان دکمه‌های Rich/Inline برای همه کاربران
    await rich_reply_text(
        message,
        t(lang, "welcome"),
        reply_markup=home_keyboard(user_id),
    )


def dashboard_text(user, lang):
    name = user.first_name or user.username or str(user.id)
    return t(lang, "dash_title", name=name, balance=get_balance(user.id), count=len(get_user_services(user.id)))


def dashboard_keyboard(user_id):
    lang = get_user_language(user_id) or "fa"
    balance = get_balance(user_id)
    if get_user_services(user_id):
        first = styled_inline_button(t(lang, "services"), callback_data="my_services", force_style="default", icon_key="dash_services")
    else:
        first = styled_inline_button(t(lang, "dash_first_service"), callback_data="buy", force_style="default", icon_key="dash_first")
    return InlineKeyboardMarkup([
        [first],
        [styled_inline_button(t(lang, "dash_balance", balance=balance), callback_data="wallet", force_style="default", icon_key="dash_balance")],
        [styled_inline_button(t(lang, "dash_new_service"), callback_data="buy", icon_key="dash_new")],
        [styled_inline_button(t(lang, "dash_back"), callback_data="home", icon_key="dash_back")],
    ])


async def send_dashboard(message, user):
    lang = get_user_language(user.id) or "fa"
    await rich_reply_text(message, dashboard_text(user, lang), reply_markup=dashboard_keyboard(user.id))


async def show_dashboard(query, user):
    lang = get_user_language(user.id) or "fa"
    await rich_edit(query, dashboard_text(user, lang), reply_markup=dashboard_keyboard(user.id))


async def panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user(user)
    clear_user_states(context)
    if not get_user_language(user.id):
        await show_language_selector_message(update.message)
        return
    await send_dashboard(update.message, user)


# =========================================================
# دستورات
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user(user)
    clear_user_states(context)

    if context.args:
        try:
            referrer_id = int(context.args[0])
            if referrer_id != user.id:
                conn = get_db()
                existing = conn.execute("SELECT referred_by FROM users WHERE user_id = ?", (user.id,)).fetchone()
                if existing and existing["referred_by"] is None:
                    conn.execute("UPDATE users SET referred_by = ? WHERE user_id = ?", (referrer_id, user.id))
                    conn.commit()
                conn.close()
        except Exception:
            pass

    lang = get_user_language(user.id)
    if not lang and user.id != ADMIN_ID:
        await show_language_selector_message(update.message)
        return

    await send_home(update.message, user.id)


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
    await send_services_message(update.message, user.id)


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
        await rich_reply_text(update.message, t(lang, "trial_already"))
        return
    if result["status"] == "empty":
        await rich_reply_text(update.message, t(lang, "trial_empty"))
        return
    await rich_reply_text(update.message, t(lang, "trial_success", link=result["link"]))


async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user(user)
    clear_user_states(context)
    lang = get_user_language(user.id)
    if not lang:
        await show_language_selector_message(update.message)
        return
    await rich_reply_text(update.message, 
        t(lang, "support_title"),
        reply_markup=InlineKeyboardMarkup([
            [styled_inline_button(t(lang, "create_ticket"), callback_data="new_ticket")],
            [styled_inline_button(t(lang, "main_menu"), callback_data="home")],
        ])
    )



async def rich_test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin-only Rich Message smoke test."""
    if not update.effective_user or update.effective_user.id != ADMIN_ID:
        return
    html = (
        "<p><b>✨ Rich Message فعال است</b></p>"
        "<p><b>HanzuVPN</b> اکنون از پیام‌های غنی تلگرام استفاده می‌کند.</p>"
        "<ul><li>متن ساختاریافته</li><li>دکمه داخل خود پیام</li><li>Copy Text</li><li>پشتیبانی از Draft/Streaming</li></ul>"
        "<details><summary>جزئیات فنی</summary>"
        "Bot API 10.1+ · sendRichMessage · sendRichMessageDraft · editMessageText.rich_message"
        "</details>"
        '<tg-button-row>'
        '<tg-button type="callback_data" style="success" data="home">🏠 منوی اصلی</tg-button>'
        '<tg-button type="copy_text" text="HanzuVPN Rich Message">📋 کپی</tg-button>'
        "</tg-button-row>"
    )
    await rich_reply(update.message, html, parse_mode="HTML")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user(user)
    lang = get_user_language(user.id)
    if not lang:
        await show_language_selector_message(update.message)
        return
    await rich_reply_text(update.message, t(lang, "help"))


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user(user)
    await show_language_selector_message(update.message)


async def set_bot_commands(application):
    commands = [
        BotCommand("start", "Start / شروع"),
        BotCommand("panel", "Dashboard / پنل کاربری"),
        BotCommand("buy", "Buy Service / خرید سرویس"),
        BotCommand("services", "My Services / سرویس‌های من"),
        BotCommand("trial", "Free Trial / تست رایگان"),
        BotCommand("support", "Support / پشتیبانی"),
        BotCommand("language", "Change Language / تغییر زبان"),
        BotCommand("help", "Help / راهنما"),
    ]
    await application.bot.set_my_commands(commands)


# =========================================================
# سرویس‌های نامحدود — ورود دستی لینک
# =========================================================

def is_unlimited_volume(volume):
    return str(volume).upper() in UNLIMITED_PLANS

def unlimited_plan_info(volume, lang="fa"):
    plan = UNLIMITED_PLANS.get(str(volume).upper())
    if not plan:
        return None
    key = "label_en" if lang == "en" else ("label_ku" if lang == "ku" else "label_fa")
    return plan, plan[key]

def unlimited_display(volume, lang="fa"):
    info = unlimited_plan_info(volume, lang)
    return f"♾️ {info[1]}" if info else str(volume)


def plan_price(volume):
    key = str(volume).strip().upper()
    if key in UNLIMITED_PLANS:
        return int(UNLIMITED_PLANS[key]["price"])
    normalized = _normalize_volume(key) if "_normalize_volume" in globals() else None
    if normalized and normalized in TARIFF_PLANS:
        return int(TARIFF_PLANS[normalized])
    try:
        return int(TARIFF_PLANS.get(str(int(float(key))), int(float(key)) * PRICE_PER_GB))
    except Exception:
        return 0


def stock_subscription_query(conn, volume):
    key = str(volume).strip()
    if key.upper() in UNLIMITED_PLANS:
        return conn.execute("SELECT id, link FROM subscriptions WHERE UPPER(TRIM(volume)) = ? AND used = 0 ORDER BY id LIMIT 1", (key.upper(),)).fetchone()
    normalized = _normalize_volume(key)
    if not normalized:
        return None
    return conn.execute(
        "SELECT id, link FROM subscriptions WHERE CAST(TRIM(REPLACE(REPLACE(LOWER(volume), 'gb', ''), 'گیگ', '')) AS INTEGER) = ? AND used = 0 ORDER BY id LIMIT 1",
        (int(normalized),)
    ).fetchone()

# =========================================================
# خرید
# =========================================================

def buy_period_keyboard(user_id):
    lang = get_user_language(user_id) or "fa"
    if lang == "en":
        period_text = "1 Month"
    elif lang == "ku":
        period_text = "١ مانگ"
    else:
        period_text = "یکماهه"
    if lang == "en":
        unlimited_text = "♾️ Unlimited"
    elif lang == "ku":
        unlimited_text = "♾️ بێ سنوور"
    else:
        unlimited_text = "♾️ نامحدود"
    return InlineKeyboardMarkup([
        [styled_inline_button(period_text, callback_data="buy_monthly")],
        [styled_inline_button(unlimited_text, callback_data="unlimited")],
        [styled_inline_button(t(lang, "back"), callback_data="home")],
    ])


def buy_keyboard(user_id):
    lang = get_user_language(user_id) or "fa"
    if lang == "en":
        buttons = [
            ("1 GB | 3,500 Toman", "plan_1"),
            ("10 GB | 35,000 Toman", "plan_10"),
            ("20 GB | 70,000 Toman", "plan_20"),
            ("30 GB | 105,000 Toman", "plan_30"),
            ("40 GB | 140,000 Toman", "plan_40"),
            ("50 GB | 175,000 Toman", "plan_50"),
            ("100 GB | 350,000 Toman", "plan_100"),
        ]
    else:
        buttons = [
            ("1 گیگ | 3,500 تومان", "plan_1"),
            ("10 گیگ | 35,000 تومان", "plan_10"),
            ("20 گیگ | 70,000 تومان", "plan_20"),
            ("30 گیگ | 105,000 تومان", "plan_30"),
            ("40 گیگ | 140,000 تومان", "plan_40"),
            ("50 گیگ | 175,000 تومان", "plan_50"),
            ("100 گیگ | 350,000 تومان", "plan_100"),
        ]
    keyboard = [[styled_inline_button(text, callback_data=cb)] for text, cb in buttons]
    if lang == "en":
        unlimited_text = "♾️ Unlimited"
    elif lang == "ku":
        unlimited_text = "♾️ بێ سنوور"
    else:
        unlimited_text = "♾️ نامحدود"
    keyboard.append([styled_inline_button(unlimited_text, callback_data="unlimited")])
    keyboard.append([styled_inline_button(t(lang, "custom"), callback_data="custom")])
    keyboard.append([styled_inline_button(t(lang, "back"), callback_data="home")])
    return InlineKeyboardMarkup(keyboard)


async def send_buy_message(message):
    user_id = message.from_user.id
    lang = get_user_language(user_id) or "fa"
    await rich_reply_text(message, t(lang, "buy_title"), reply_markup=buy_period_keyboard(user_id))


async def show_buy_menu(query):
    lang = get_user_language(query.from_user.id) or "fa"
    await rich_edit(query, t(lang, "buy_title"), reply_markup=buy_period_keyboard(query.from_user.id))


async def show_buy_services(query):
    lang = get_user_language(query.from_user.id) or "fa"
    await rich_edit(query, t(lang, "buy_title"), reply_markup=buy_keyboard(query.from_user.id))


async def show_unlimited_services(query):
    lang = get_user_language(query.from_user.id) or "fa"
    if lang == "en":
        buttons = [("👤 Single User | 150,000 Toman", "unlimited_plan_1"), ("👥 Two Users | 250,000 Toman", "unlimited_plan_2"), ("👥 Three Users | 350,000 Toman", "unlimited_plan_3")]
        title = "♾️ Unlimited Service\n\nChoose your plan:"
    elif lang == "ku":
        buttons = [("👤 یەک بەکارهێنەر | 150,000 تومان", "unlimited_plan_1"), ("👥 دوو بەکارهێنەر | 250,000 تومان", "unlimited_plan_2"), ("👥 سێ بەکارهێنەر | 350,000 تومان", "unlimited_plan_3")]
        title = "♾️ خزمەتگوزاری بێ سنوور\n\nپلانەکەت هەڵبژێرە:"
    else:
        buttons = [("👤 تک کاربره | 150,000 تومان", "unlimited_plan_1"), ("👥 دو کاربره | 250,000 تومان", "unlimited_plan_2"), ("👥 سه کاربره | 350,000 تومان", "unlimited_plan_3")]
        title = "♾️ سرویس نامحدود\n\nپلن موردنظر را انتخاب کنید:"
    keyboard = [[styled_inline_button(text, callback_data=cb)] for text, cb in buttons]
    keyboard.append([styled_inline_button(t(lang, "back"), callback_data="buy_monthly")])
    await rich_edit(query, title, reply_markup=InlineKeyboardMarkup(keyboard))


# =========================================================
# پرداخت
# =========================================================

async def show_payment(query, volume, price, original_price=None, coupon_code=None):
    """مرحله اول پرداخت: فقط خلاصه سفارش و دکمه «پرداخت». شماره کارت در مرحله بعد نمایش داده می‌شود."""
    user_id = query.from_user.id
    lang = get_user_language(user_id) or "fa"
    if original_price is None:
        original_price = price

    if is_unlimited_volume(volume):
        if lang == "en":
            caption = f"♾️ Unlimited Service\n\n👤 Plan: {unlimited_display(volume, lang)}\n💰 Price: {price:,} Toman\n⏳ 30 days\n"
        elif lang == "ku":
            caption = f"♾️ خزمەتگوزاری بێ سنوور\n\n👤 پلان: {unlimited_display(volume, lang)}\n💰 نرخ: {price:,} تومان\n⏳ 30 ڕۆژ\n"
        else:
            caption = f"♾️ سرویس نامحدود\n\n👤 پلن: {unlimited_display(volume, lang)}\n💰 مبلغ: {price:,} تومان\n⏳ ۳۰ روز\n"
    else:
        caption = t(lang, "payment", volume=volume, price=price)
    if original_price != price and coupon_code:
        caption += t(lang, "original_price", original=original_price, coupon=coupon_code)
    keyboard = [
        [styled_inline_button(t(lang, "pay"), callback_data=f"pay_{volume}")],
    ]
    keyboard.append([styled_inline_button(t(lang, "back"), callback_data="buy")])
    await rich_edit(query, caption, reply_markup=InlineKeyboardMarkup(keyboard))


async def show_card_payment(query, volume, original_price, coupon_code=None, final_price=None):
    """مرحله دوم پرداخت: نمایش شماره کارت + کد تخفیف + دکمه «پرداخت کردم»."""
    user_id = query.from_user.id
    lang = get_user_language(user_id) or "fa"
    price = original_price if final_price is None else int(final_price)
    if coupon_code and final_price is None:
        result = apply_coupon(coupon_code, user_id, original_price)
        if result["status"] == "success":
            price = result["price"]
        else:
            coupon_code = None

    if is_unlimited_volume(volume):
        if lang == "en":
            caption = f"♾️ Unlimited Service\n\n👤 Plan: {unlimited_display(volume, lang)}\n💰 Price: {price:,} Toman\n⏳ 30 days\n"
        elif lang == "ku":
            caption = f"♾️ خزمەتگوزاری بێ سنوور\n\n👤 پلان: {unlimited_display(volume, lang)}\n💰 نرخ: {price:,} تومان\n⏳ 30 ڕۆژ\n"
        else:
            caption = f"♾️ سرویس نامحدود\n\n👤 پلن: {unlimited_display(volume, lang)}\n💰 مبلغ: {price:,} تومان\n⏳ ۳۰ روز\n"
    else:
        caption = t(lang, "payment", volume=volume, price=price)
    if original_price != price and coupon_code:
        caption += t(lang, "original_price", original=original_price, coupon=coupon_code)
    caption += t(lang, "card", card=CARD_NUMBER)

    keyboard = [
        [styled_copy_card_button()],
        [styled_inline_button(t(lang, "paid"), callback_data=f"paid_{volume}")],
        [styled_inline_button(t(lang, "coupon"), callback_data="coupon")],
    ]
    balance = get_balance(user_id)
    if balance >= price:
        keyboard.insert(0, [styled_inline_button(t(lang, "pay_wallet"), callback_data=f"walletpay_{volume}_{price}")])
    keyboard.append([styled_inline_button(t(lang, "back"), callback_data=f"paymentback_{volume}")])
    await rich_edit(query, caption, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


# =========================================================
# لینک‌ها و تست و سفارش (بخش‌های قبلی خلاصه شده برای جلوگیری از طولانی شدن بیش از حد)
# =========================================================

def add_subscription(volume, link):
    conn = get_db()
    conn.execute("INSERT INTO subscriptions (volume, link, used) VALUES (?, ?, 0)", (str(volume), link))
    conn.commit()
    conn.close()


def get_subscription_list():
    conn = get_db()
    rows = conn.execute("SELECT id, volume, link FROM subscriptions WHERE used = 0 ORDER BY CAST(volume AS INTEGER), id").fetchall()
    conn.close()
    return rows


def delete_subscription(subscription_id):
    conn = get_db()
    conn.execute("DELETE FROM subscriptions WHERE id = ? AND used = 0", (subscription_id,))
    conn.commit()
    conn.close()


def get_stock():
    conn = get_db()
    rows = conn.execute("SELECT volume, COUNT(*) AS count FROM subscriptions WHERE used = 0 GROUP BY volume ORDER BY CAST(volume AS INTEGER)").fetchall()
    conn.close()
    return {row["volume"]: row["count"] for row in rows}


def add_free_trial(link):
    conn = get_db()
    conn.execute("INSERT INTO free_trials (link, used) VALUES (?, 0)", (link,))
    conn.commit()
    conn.close()


def get_free_trial_stock():
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM free_trials WHERE used = 0").fetchone()[0]
    conn.close()
    return count


def get_free_trial_list():
    conn = get_db()
    rows = conn.execute("SELECT id, link FROM free_trials WHERE used = 0 ORDER BY id").fetchall()
    conn.close()
    return rows


def delete_free_trial(trial_id):
    conn = get_db()
    conn.execute("DELETE FROM free_trials WHERE id = ? AND used = 0", (trial_id,))
    conn.commit()
    conn.close()


def claim_trial(user):
    conn = get_db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        already = conn.execute("SELECT * FROM free_trial_users WHERE user_id = ?", (user.id,)).fetchone()
        if already:
            conn.rollback()
            return {"status": "already"}
        trial = conn.execute("SELECT id, link FROM free_trials WHERE used = 0 ORDER BY id LIMIT 1").fetchone()
        if not trial:
            conn.rollback()
            return {"status": "empty"}
        claimed_at = datetime.now()
        expires_at = claimed_at + timedelta(days=TRIAL_DAYS)
        conn.execute("UPDATE free_trials SET used = 1 WHERE id = ? AND used = 0", (trial["id"],))
        conn.execute("""
            INSERT INTO free_trial_users (user_id, trial_id, claimed_at, expires_at)
            VALUES (?, ?, ?, ?)
        """, (user.id, trial["id"], claimed_at.strftime("%Y-%m-%d %H:%M:%S"), expires_at.strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return {"status": "success", "link": trial["link"]}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def cancel_pending_orders(user_id):
    conn = get_db()
    conn.execute("UPDATE orders SET status = 'cancelled' WHERE user_id = ? AND status = 'pending'", (user_id,))
    conn.commit()
    conn.close()


def create_order(user, volume, price, coupon_code=None, is_charge=0):
    cancel_pending_orders(user.id)
    conn = get_db()
    cursor = conn.execute("""
        INSERT INTO orders (user_id, username, first_name, volume, price, status, created_at, is_charge)
        VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
    """, (user.id, user.username or "", user.first_name or "", str(volume), int(price), now_text(), is_charge))
    order_id = cursor.lastrowid

    if coupon_code and not is_charge:
        coupon = get_coupon(coupon_code)
        if coupon:
            try:
                conn.execute("INSERT OR IGNORE INTO coupon_uses (coupon_id, user_id, order_id, created_at) VALUES (?, ?, ?, ?)",
                             (coupon["id"], user.id, order_id, now_text()))
                conn.execute("UPDATE coupons SET used_count = used_count + 1 WHERE id = ?", (coupon["id"],))
            except Exception:
                pass

    conn.commit()
    conn.close()
    return order_id


def get_latest_pending_order(user_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM orders WHERE user_id = ? AND status = 'pending' ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
    conn.close()
    return row


def _normalize_volume(value):
    if value is None:
        return None
    text = str(value).strip().lower()
    text = text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
    for unit in ("گیگابایت", "گیگ", "gb", "g"):
        text = text.replace(unit, "")
    text = text.strip()
    try:
        n = int(float(text))
        return str(n) if n > 0 else None
    except Exception:
        return None


async def approve_order_with_source(order_id):
    """Approve a paid service without blocking the Telegram event loop.
    Manual mode is unchanged; panel modes provision through PasarGuard in a worker thread.
    """
    global _PG_ORDER_LOCK
    if _PG_ORDER_LOCK is None:
        _PG_ORDER_LOCK = asyncio.Lock()
    mode = get_pasarguard_mode()
    if mode == "manual":
        return await asyncio.to_thread(approve_order, order_id)

    async with _PG_ORDER_LOCK:
        conn = get_db()
        order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        conn.close()
        if not order:
            return {"status": "not_found"}
        if order["status"] != "pending":
            return {"status": "already_processed", "order": order}
        try:
            provision = await asyncio.to_thread(pg_create_order_service_sync, order)
        except Exception as exc:
            if mode == "fallback":
                return await asyncio.to_thread(approve_order, order_id)
            return {"status": "pg_error", "order": order, "error": str(exc)}

        approved_at = datetime.now()
        expires_at = approved_at + timedelta(days=SERVICE_DAYS)
        conn = get_db()
        try:
            conn.execute("BEGIN IMMEDIATE")
            fresh = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
            if not fresh or fresh["status"] != "pending":
                conn.rollback()
                return {"status": "already_processed", "order": fresh or order}
            conn.execute("""
                UPDATE orders SET status='approved', approved_at=?, expires_at=?, pg_username=?, pg_subscription_url=?
                WHERE id=? AND status='pending'
            """, (approved_at.strftime("%Y-%m-%d %H:%M:%S"), expires_at.strftime("%Y-%m-%d %H:%M:%S"),
                  provision["username"], provision["subscription_url"], order_id))
            conn.commit()
            return {"status":"approved", "order":fresh, "link":provision["subscription_url"],
                    "expires_at":expires_at.strftime("%Y-%m-%d %H:%M:%S"), "pg_username":provision["username"]}
        except Exception:
            conn.rollback(); raise
        finally:
            conn.close()


async def refund_wallet_after_pg_failure(user_id, amount, order_id):
    return await asyncio.to_thread(change_balance, user_id, amount, "refund", f"برگشت وجه به دلیل خطای PasarGuard - سفارش #{order_id}", order_id)


def approve_order(order_id):
    conn = get_db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not order:
            conn.rollback()
            return {"status": "not_found"}
        if order["status"] != "pending":
            conn.rollback()
            return {"status": "already_processed", "order": order}

        # اگر شارژ کیف پول باشد
        if order["is_charge"]:
            conn.execute("UPDATE users SET balance = COALESCE(balance, 0) + ? WHERE user_id = ?", (order["price"], order["user_id"]))
            conn.execute("INSERT INTO wallet_transactions (user_id, amount, type, description, order_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                         (order["user_id"], order["price"], "charge", f"شارژ کیف پول - سفارش #{order_id}", order_id, now_text()))
            conn.execute("UPDATE orders SET status = 'approved', approved_at = ? WHERE id = ? AND status = 'pending'",
                         (now_text(), order_id))
            conn.commit()
            return {"status": "charge_approved", "order": order}

        subscription = stock_subscription_query(conn, order["volume"])
        if not subscription:
            conn.rollback()
            return {"status": "no_stock", "order": order}

        approved_at = datetime.now()
        expires_at = approved_at + timedelta(days=SERVICE_DAYS)
        conn.execute("""
            UPDATE orders SET status = 'approved', subscription_id = ?, approved_at = ?, expires_at = ?
            WHERE id = ? AND status = 'pending'
        """, (subscription["id"], approved_at.strftime("%Y-%m-%d %H:%M:%S"), expires_at.strftime("%Y-%m-%d %H:%M:%S"), order_id))
        conn.execute("UPDATE subscriptions SET used = 1 WHERE id = ? AND used = 0", (subscription["id"],))
        conn.commit()
        return {
            "status": "approved",
            "order": order,
            "link": subscription["link"],
            "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def reject_order(order_id):
    conn = get_db()
    updated = conn.execute("UPDATE orders SET status = 'rejected' WHERE id = ? AND status = 'pending'", (order_id,))
    conn.commit()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    conn.close()
    return updated.rowcount == 1, order


def get_user_services(user_id):
    conn = get_db()
    rows = conn.execute("""
        SELECT o.id, o.volume, o.price, o.approved_at, o.expires_at, COALESCE(s.link, o.pg_subscription_url) AS link
        FROM orders o
        LEFT JOIN subscriptions s ON o.subscription_id = s.id
        WHERE o.user_id = ? AND o.status = 'approved' AND o.is_charge = 0
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
            if is_unlimited_volume(row["volume"]):
                plan_text = unlimited_display(row["volume"], lang).replace("♾️ ", "")
                if lang == "en":
                    text += f"🧾 Order #{row['id']}\n♾️ {plan_text}\n⏳ {row['expires_at'] or '-'}\n\n🔗 {row['link'] or '-'}\n\n"
                elif lang == "ku":
                    text += f"🧾 داواکاری #{row['id']}\n♾️ {plan_text}\n⏳ {row['expires_at'] or '-'}\n\n🔗 {row['link'] or '-'}\n\n"
                else:
                    text += f"🧾 سفارش #{row['id']}\n♾️ {plan_text}\n⏳ {row['expires_at'] or '-'}\n\n🔗 {row['link'] or '-'}\n\n"
            else:
                text += t(lang, "service_item", id=row["id"], volume=row["volume"], expires=row["expires_at"] or "-", link=row["link"] or "-")
    await rich_reply_text(message, text, reply_markup=InlineKeyboardMarkup([
        [styled_inline_button(t(lang, "renew"), callback_data="renew")],
        [styled_inline_button(t(lang, "main_menu"), callback_data="home")],
    ]))


# کوپن
def create_coupon(code, percent, max_uses):
    conn = get_db()
    try:
        conn.execute("INSERT INTO coupons (code, percent, max_uses, created_at) VALUES (?, ?, ?, ?)",
                     (code.upper(), percent, max_uses, now_text()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_coupon(code):
    conn = get_db()
    row = conn.execute("SELECT * FROM coupons WHERE code = ? AND active = 1", (code.upper(),)).fetchone()
    conn.close()
    return row


def user_used_coupon(coupon_id, user_id):
    conn = get_db()
    row = conn.execute("SELECT id FROM coupon_uses WHERE coupon_id = ? AND user_id = ?", (coupon_id, user_id)).fetchone()
    conn.close()
    return row is not None


def apply_coupon(code, user_id, price):
    coupon = get_coupon(code)
    if not coupon:
        return {"status": "invalid"}
    if user_used_coupon(coupon["id"], user_id):
        return {"status": "used"}
    if coupon["max_uses"] > 0 and coupon["used_count"] >= coupon["max_uses"]:
        return {"status": "full"}
    new_price = int(price * (100 - coupon["percent"]) / 100)
    return {"status": "success", "coupon": coupon, "price": max(new_price, 0)}


def referral_count(user_id):
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,)).fetchone()[0]
    conn.close()
    return count


def referral_link(bot_username, user_id):
    return f"https://t.me/{bot_username}?start={user_id}"


def create_ticket(user_id, subject="Support"):
    conn = get_db()
    cursor = conn.execute("INSERT INTO tickets (user_id, subject, status, created_at) VALUES (?, ?, 'open', ?)",
                          (user_id, subject, now_text()))
    ticket_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return ticket_id


def add_ticket_message(ticket_id, sender_id, message):
    conn = get_db()
    conn.execute("INSERT INTO ticket_messages (ticket_id, sender_id, message, created_at) VALUES (?, ?, ?, ?)",
                 (ticket_id, sender_id, message, now_text()))
    conn.commit()
    conn.close()


def get_stats():
    conn = get_db()
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_orders = conn.execute("SELECT COUNT(*) FROM orders WHERE is_charge = 0").fetchone()[0]
    approved = conn.execute("SELECT COUNT(*) FROM orders WHERE status='approved' AND is_charge = 0").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM orders WHERE status='pending'").fetchone()[0]
    rejected = conn.execute("SELECT COUNT(*) FROM orders WHERE status='rejected'").fetchone()[0]
    sales = conn.execute("SELECT COALESCE(SUM(price),0) FROM orders WHERE status='approved' AND is_charge = 0").fetchone()[0]
    trials = conn.execute("SELECT COUNT(*) FROM free_trial_users").fetchone()[0]
    referrals = conn.execute("SELECT COUNT(*) FROM users WHERE referred_by IS NOT NULL").fetchone()[0]
    open_tickets = conn.execute("SELECT COUNT(*) FROM tickets WHERE status='open'").fetchone()[0]
    conn.close()
    return {
        "users": total_users, "orders": total_orders, "approved": approved,
        "pending": pending, "rejected": rejected, "sales": sales,
        "trials": trials, "referrals": referrals, "tickets": open_tickets,
    }


# =========================================================
# =========================================================
# بکاپ دیتابیس
# =========================================================

def create_consistent_db_backup():
    source_path = os.path.abspath(DB_PATH)
    if not os.path.isfile(source_path):
        raise FileNotFoundError(f"Database not found: {source_path}")
    fd, backup_path = tempfile.mkstemp(prefix="hanzuvpn_backup_", suffix=".db")
    os.close(fd)
    src = dst = None
    try:
        src = sqlite3.connect(source_path, timeout=30)
        dst = sqlite3.connect(backup_path, timeout=30)
        src.backup(dst)
        dst.commit()
        return backup_path
    finally:
        if src is not None: src.close()
        if dst is not None: dst.close()

async def send_db_backup(query, context):
    if query.from_user.id != ADMIN_ID: return
    path = None
    try:
        path = create_consistent_db_backup()
        filename = f"hanzuvpn-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
        with open(path, "rb") as f:
            await context.bot.send_document(chat_id=ADMIN_ID, document=InputFile(f, filename=filename), caption="💾 بکاپ کامل دیتابیس HanzuVPN")
        await query.answer("✅ بکاپ با موفقیت ارسال شد.")
    except Exception as e:
        print(f"Backup error: {type(e).__name__}: {e}")
        await query.answer("❌ دریافت بکاپ ناموفق بود.", show_alert=True)
    finally:
        if path:
            try: os.remove(path)
            except OSError: pass

async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or user.id != ADMIN_ID: return
    path = None
    try:
        path = create_consistent_db_backup()
        filename = f"hanzuvpn-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
        with open(path, "rb") as f:
            await context.bot.send_document(chat_id=user.id, document=InputFile(f, filename=filename), caption="💾 بکاپ کامل دیتابیس HanzuVPN")
    except Exception as e:
        print(f"Backup error: {type(e).__name__}: {e}")
        if update.message: await rich_reply_text(update.message, "❌ دریافت بکاپ ناموفق بود.")
    finally:
        if path:
            try: os.remove(path)
            except OSError: pass

# پنل مدیریت + کیف پول ادمین
# =========================================================

async def show_button_style_panel(query):
    current = get_button_style()
    keyboard = [
        [styled_inline_button("⚪ پیش‌فرض", callback_data="button_style_default")],
        [styled_inline_button("🟢 سبز", callback_data="button_style_success")],
        [styled_inline_button("🔴 قرمز", callback_data="button_style_danger")],
        [styled_inline_button("🔵 آبی", callback_data="button_style_primary")],
        [styled_inline_button("🎯 تنظیم رنگ تک‌تک دکمه‌ها", callback_data="admin_button_colors")],
        [styled_inline_button("↩️ بازگشت به پنل مدیریت", callback_data="admin")],
    ]
    await rich_edit(query, 
        f"🎨 تنظیم استایل دکمه‌ها\n\n"
        f"استایل سراسری فعلی: {BUTTON_STYLE_OPTIONS[current]}\n\n"
        "اگر برای یک دکمه رنگ اختصاصی تعیین کنی، همان رنگ روی آن دکمه اعمال می‌شود و "
        "استایل سراسری روی آن نادیده گرفته می‌شود.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def show_button_color_list(query):
    colors = get_button_color_map()
    items = list(BUTTON_COLOR_TARGETS.items())
    keyboard = []

    for i in range(0, len(items), 2):
        row = []
        for key, label in items[i:i+2]:
            style = colors.get(key, "default")
            row.append(
                styled_inline_button(
                    f"{button_style_icon(style)} {label}",
                    callback_data=f"button_color_target_{key}"
                )
            )
        keyboard.append(row)

    keyboard.append([styled_inline_button("⚡ دکمه‌های پویا (pay_* و ...)", callback_data="button_color_dynamic")])
    keyboard.append([styled_inline_button("↩️ بازگشت", callback_data="admin_button_style")])

    await rich_edit(query, 
        "🎯 تنظیم رنگ تک‌تک دکمه‌ها\n\n"
        "روی هر دکمه بزن و رنگ دلخواهش را انتخاب کن.\n"
        "⚪ یعنی بدون رنگ اختصاصی و استفاده از تنظیم سراسری/خودکار.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def show_button_color_picker(query, key, label=None):
    colors = get_button_color_map()
    current = colors.get(key, "default")
    label = label or BUTTON_COLOR_TARGETS.get(key, key)

    keyboard = [
        [
            styled_inline_button(
                f"{'✅ ' if current == 'default' else ''}⚪ پیش‌فرض",
                callback_data=f"button_color_set_default_{key}"
            )
        ],
        [
            styled_inline_button(
                f"{'✅ ' if current == 'success' else ''}🟢 سبز",
                callback_data=f"button_color_set_success_{key}"
            )
        ],
        [
            styled_inline_button(
                f"{'✅ ' if current == 'danger' else ''}🔴 قرمز",
                callback_data=f"button_color_set_danger_{key}"
            )
        ],
        [
            styled_inline_button(
                f"{'✅ ' if current == 'primary' else ''}🔵 آبی",
                callback_data=f"button_color_set_primary_{key}"
            )
        ],
        [styled_inline_button("↩️ لیست دکمه‌ها", callback_data="admin_button_colors")],
    ]

    await rich_edit(query, 
        f"🎨 انتخاب رنگ\n\nدکمه: {label}\n"
        f"رنگ فعلی: {BUTTON_STYLE_OPTIONS.get(current, BUTTON_STYLE_OPTIONS['default'])}\n\n"
        "رنگ موردنظر را انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def show_dynamic_button_color_picker(query):
    colors = get_button_color_map()
    keyboard = []
    for pattern, label in BUTTON_COLOR_PATTERNS.items():
        current = colors.get(pattern, "default")
        keyboard.append([
            styled_inline_button(
                f"{button_style_icon(current)} {label}",
                callback_data=f"button_color_dynamic_target_{pattern.replace('*', 'X')}"
            )
        ])
    keyboard.append([styled_inline_button("↩️ لیست دکمه‌ها", callback_data="admin_button_colors")])
    await rich_edit(query, 
        "⚡ تنظیم رنگ دکمه‌های پویا\n\n"
        "این گزینه‌ها روی همه callbackهایی که با همان پیشوند شروع شوند اعمال می‌شوند.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def show_dynamic_color_picker(query, pattern):
    colors = get_button_color_map()
    current = colors.get(pattern, "default")
    label = BUTTON_COLOR_PATTERNS.get(pattern, pattern)
    encoded = pattern.replace("*", "X")
    keyboard = [
        [styled_inline_button(f"{'✅ ' if current == 'default' else ''}⚪ پیش‌فرض", callback_data=f"button_color_dynamic_set_default_{encoded}")],
        [styled_inline_button(f"{'✅ ' if current == 'success' else ''}🟢 سبز", callback_data=f"button_color_dynamic_set_success_{encoded}")],
        [styled_inline_button(f"{'✅ ' if current == 'danger' else ''}🔴 قرمز", callback_data=f"button_color_dynamic_set_danger_{encoded}")],
        [styled_inline_button(f"{'✅ ' if current == 'primary' else ''}🔵 آبی", callback_data=f"button_color_dynamic_set_primary_{encoded}")],
        [styled_inline_button("↩️ دکمه‌های پویا", callback_data="button_color_dynamic")],
    ]
    await rich_edit(query, 
        f"🎨 رنگ دکمه‌های پویا\n\n{label}  ({pattern})\n"
        f"رنگ فعلی: {BUTTON_STYLE_OPTIONS.get(current, BUTTON_STYLE_OPTIONS['default'])}",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def show_admin(query):
    lang = get_user_language(query.from_user.id) or "fa"
    keyboard = [
        [styled_inline_button("💾 دریافت بکاپ", callback_data="admin_backup")],
        [styled_inline_button(t(lang, "admin_add"), callback_data="admin_add")],
        [styled_inline_button(t(lang, "admin_trial"), callback_data="admin_trial")],
        [
            styled_inline_button(t(lang, "admin_stock"), callback_data="admin_stock"),
            styled_inline_button(t(lang, "admin_delete"), callback_data="admin_delete")
        ],
        [styled_inline_button(t(lang, "admin_coupon"), callback_data="admin_coupon")],
        [styled_inline_button(t(lang, "admin_balance"), callback_data="admin_balance")],
        [styled_inline_button(t(lang, "admin_broadcast"), callback_data="admin_broadcast")],
        [
            styled_inline_button(t(lang, "admin_stats"), callback_data="admin_stats"),
            styled_inline_button(t(lang, "admin_orders"), callback_data="admin_orders")
        ],
        [styled_inline_button(t(lang, "admin_tickets"), callback_data="admin_tickets")],
        [styled_inline_button("🔌 اتصال پنل PasarGuard", callback_data="pg_connect")],
        [styled_inline_button("📡 وضعیت / گروه پنل", callback_data="pg_status")],
        [styled_inline_button("🎨 استایل دکمه‌ها", callback_data="admin_button_style")],
        [styled_inline_button(t(lang, "back"), callback_data="home")],
    ]
    await rich_edit(query, 
        "⚙️ پنل مدیریت HanzuVPN\n\nمدیریت کامل ربات:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_admin_stock(query):
    lang = get_user_language(query.from_user.id) or "fa"
    stock = get_stock()
    trial_stock = get_free_trial_stock()
    text = "📦 موجودی HanzuVPN\n\n"
    if stock:
        for volume, count in stock.items():
            label = unlimited_display(volume, lang) if is_unlimited_volume(volume) else f"{volume} گیگ"
            text += f"🔹 {label}: {count} عدد\n"
    else:
        text += "❌ سرویس فروشی موجود نیست.\n"
    text += f"\n🎁 تست رایگان:\n🔹 {trial_stock} عدد\n"
    await rich_edit(query, text, reply_markup=InlineKeyboardMarkup([
        [styled_inline_button(t(lang, "admin_panel"), callback_data="admin")]
    ]))


async def show_admin_stats(query):
    lang = get_user_language(query.from_user.id) or "fa"
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
    await rich_edit(query, text, reply_markup=InlineKeyboardMarkup([
        [styled_inline_button(t(lang, "admin_panel"), callback_data="admin")]
    ]))


async def show_admin_orders(query):
    lang = get_user_language(query.from_user.id) or "fa"
    conn = get_db()
    rows = conn.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 15").fetchall()
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
            }.get(row["status"], row["status"])
            charge = " (شارژ کیف پول)" if row["is_charge"] else ""
            text += (
                f"#{row['id']} | {row['first_name'] or '-'}{charge}\n"
                f"📦 {row['volume']} | {row['price']:,} تومان\n"
                f"{status}\n🕐 {row['created_at']}\n\n"
            )
    await rich_edit(query, text, reply_markup=InlineKeyboardMarkup([
        [styled_inline_button(t(lang, "admin_panel"), callback_data="admin")]
    ]))


async def show_admin_trial(query):
    lang = get_user_language(query.from_user.id) or "fa"
    stock = get_free_trial_stock()
    keyboard = [
        [styled_inline_button(t(lang, "admin_trial_add"), callback_data="admin_trial_add")],
        [styled_inline_button(t(lang, "admin_trial_delete"), callback_data="admin_trial_delete")],
        [styled_inline_button(t(lang, "admin_trial_stock"), callback_data="admin_trial_stock")],
        [styled_inline_button(t(lang, "admin_panel"), callback_data="admin")],
    ]
    await rich_edit(query, 
        f"🎁 مدیریت تست رایگان\n\n📦 حجم: 100 مگابایت\n⏳ مدت: 1 روز\n📊 موجودی: {stock}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_admin_trial_delete(query):
    lang = get_user_language(query.from_user.id) or "fa"
    rows = get_free_trial_list()
    if not rows:
        await rich_edit(query, 
            "🗑 حذف تست\n\n❌ لینک تستی وجود ندارد.",
            reply_markup=InlineKeyboardMarkup([[styled_inline_button(t(lang, "admin_trial"), callback_data="admin_trial")]])
        )
        return
    keyboard = [[styled_inline_button(t(lang, "trial_item", id=row['id']), callback_data=f"trial_delete_{row['id']}")] for row in rows]
    keyboard.append([styled_inline_button(t(lang, "admin_trial"), callback_data="admin_trial")])
    await rich_edit(query, "🗑 لینک تست موردنظر را انتخاب کن:", reply_markup=InlineKeyboardMarkup(keyboard))


async def show_delete_menu(query):
    lang = get_user_language(query.from_user.id) or "fa"
    rows = get_subscription_list()
    if not rows:
        await rich_edit(query, 
            "🗑 حذف لینک\n\n❌ لینک استفاده‌نشده‌ای وجود ندارد.",
            reply_markup=InlineKeyboardMarkup([[styled_inline_button(t(lang, "admin_panel"), callback_data="admin")]])
        )
        return
    keyboard = [[styled_inline_button(t(lang, "delete_item", id=row['id'], volume=row['volume']), callback_data=f"delete_{row['id']}")] for row in rows]
    keyboard.append([styled_inline_button(t(lang, "admin_panel"), callback_data="admin")])
    await rich_edit(query, "🗑 کدام لینک حذف شود؟", reply_markup=InlineKeyboardMarkup(keyboard))


# =========================================================
# Callback Handler (کامل)
# =========================================================

async def _button_handler_impl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass
    user = query.from_user
    user_id = user.id
    ensure_user(user)
    data = query.data or ""

    if data == "admin_button_colors":
        if user_id != ADMIN_ID:
            return
        await show_button_color_list(query)
        return

    if data == "button_color_dynamic":
        if user_id != ADMIN_ID:
            return
        await show_dynamic_button_color_picker(query)
        return

    if data.startswith("button_color_target_"):
        if user_id != ADMIN_ID:
            return
        key = data.split("button_color_target_", 1)[1]
        if key not in BUTTON_COLOR_TARGETS:
            await query.answer("دکمه نامعتبر است.", show_alert=True)
            return
        await show_button_color_picker(query, key, BUTTON_COLOR_TARGETS[key])
        return

    if data.startswith("button_color_dynamic_target_"):
        if user_id != ADMIN_ID:
            return
        encoded = data.split("button_color_dynamic_target_", 1)[1]
        pattern = encoded[:-1] + "*" if encoded.endswith("X") else encoded
        if pattern not in BUTTON_COLOR_PATTERNS:
            await query.answer("دکمه پویا نامعتبر است.", show_alert=True)
            return
        await show_dynamic_color_picker(query, pattern)
        return

    if data.startswith("button_color_set_"):
        if user_id != ADMIN_ID:
            return
        rest = data.split("button_color_set_", 1)[1]
        style, key = rest.split("_", 1)
        if style not in BUTTON_STYLE_OPTIONS or key not in BUTTON_COLOR_TARGETS:
            await query.answer("تنظیم نامعتبر است.", show_alert=True)
            return
        set_button_color(key, style)
        await show_button_color_picker(query, key, BUTTON_COLOR_TARGETS[key])
        return

    if data.startswith("button_color_dynamic_set_"):
        if user_id != ADMIN_ID:
            return
        rest = data.split("button_color_dynamic_set_", 1)[1]
        style, encoded = rest.split("_", 1)
        pattern = encoded[:-1] + "*" if encoded.endswith("X") else encoded
        if style not in BUTTON_STYLE_OPTIONS or pattern not in BUTTON_COLOR_PATTERNS:
            await query.answer("تنظیم نامعتبر است.", show_alert=True)
            return
        set_button_color(pattern, style)
        await show_dynamic_color_picker(query, pattern)
        return

    if data == "admin_button_style":
        if user_id != ADMIN_ID:
            return
        await show_button_style_panel(query)
        return

    if data.startswith("button_style_"):
        if user_id != ADMIN_ID:
            return
        selected = data.split("button_style_", 1)[1]
        set_button_style(selected)
        await show_button_style_panel(query)
        return

    # زبان
    if data == "language":
        await rich_edit(query, TEXTS["fa"]["language_title"], reply_markup=language_keyboard())
        return

    if data.startswith("language_"):
        language = data.split("_", 1)[1]
        if language not in LANGUAGES:
            await query.answer("زبان نامعتبر است.", show_alert=True)
            return
        set_user_language(user_id, language)
        clear_user_states(context)
        await rich_edit(query, 
            t(language, "language_changed") + "\n\n" + t(language, "welcome"),
            reply_markup=home_keyboard(user_id)
        )
        try:
            await rich_reply_text(query.message, t(language, "language_changed"))
        except Exception as e:
            print("Language reply keyboard update error:", e)
        return

    lang = get_user_language(user_id)
    if not lang and user_id != ADMIN_ID:
        await rich_edit(query, TEXTS["fa"]["language_title"], reply_markup=language_keyboard())
        return
    # خانه
    if data == "home":
        clear_user_states(context)
        await show_home(query, user_id)
        return

    # داشبورد کاربری
    if data == "dashboard":
        clear_user_states(context)
        await show_dashboard(query, query.from_user)
        return

    # کیف پول کاربر
    if data == "wallet":
        balance = get_balance(user_id)
        await rich_edit(query, 
            t(lang, "wallet_title", balance=balance),
            reply_markup=InlineKeyboardMarkup([
                [styled_inline_button(t(lang, "charge_wallet"), callback_data="charge_wallet")],
                [styled_inline_button(t(lang, "wallet_history"), callback_data="wallet_history")],
                [styled_inline_button(t(lang, "back"), callback_data="home")],
            ])
        )
        return

    if data == "charge_wallet":
        context.user_data["waiting_charge_amount"] = True
        await rich_edit(query, t(lang, "charge_prompt", min=MIN_CHARGE))
        return

    if data == "wallet_history":
        rows = get_wallet_history(user_id)
        if not rows:
            text = t(lang, "no_history")
        else:
            text = t(lang, "history_title")
            for row in rows:
                emoji = "🟢" if row["amount"] > 0 else "🔴"
                text += t(lang, "history_item",
                          emoji=emoji,
                          amount=abs(row["amount"]),
                          desc=row["description"] or row["type"],
                          date=row["created_at"])
        await rich_edit(query, text, reply_markup=InlineKeyboardMarkup([
            [styled_inline_button(t(lang, "back"), callback_data="wallet")]
        ]))
        return

    # خرید
    if data == "buy":
        clear_user_states(context)
        await show_buy_menu(query)
        return

    if data == "buy_monthly":
        clear_user_states(context)
        await show_buy_services(query)
        return

    if data == "unlimited":
        clear_user_states(context)
        await show_unlimited_services(query)
        return

    if data.startswith("unlimited_plan_"):
        plan_number = data.split("_")[-1]
        volume = f"UNLIMITED_{plan_number}"
        plan = UNLIMITED_PLANS.get(volume)
        if not plan:
            await query.answer("پلن نامعتبر است.", show_alert=True)
            return
        coupon_code = context.user_data.get("coupon_code")
        price = plan["price"]
        original_price = plan["price"]
        if coupon_code:
            result = apply_coupon(coupon_code, user_id, price)
            if result["status"] == "success":
                price = result["price"]
            else:
                context.user_data.pop("coupon_code", None)
                coupon_code = None
        await show_payment(query, volume, price, original_price, coupon_code)
        return

    if data.startswith("plan_"):
        volume = data.split("_")[1]
        base_price = PLANS.get(volume)
        if not base_price:
            return
        coupon_code = context.user_data.get("coupon_code")
        price = base_price
        original_price = base_price
        if coupon_code:
            result = apply_coupon(coupon_code, user_id, base_price)
            if result["status"] == "success":
                price = result["price"]
            else:
                context.user_data.pop("coupon_code", None)
                coupon_code = None
        await show_payment(query, volume, price, original_price, coupon_code)
        return

    # مرحله دوم پرداخت: با زدن «پرداخت» شماره کارت نمایش داده می‌شود.
    if data.startswith("pay_"):
        volume = data.split("_", 1)[1]
        if volume == "custom":
            volume = context.user_data.get("custom_volume")
        original_price = None
        if is_unlimited_volume(volume):
            original_price = UNLIMITED_PLANS[volume]["price"]
        elif volume in PLANS:
            original_price = PLANS[volume]
        else:
            original_price = context.user_data.get("custom_price")
        if not volume or not original_price:
            await query.answer("سفارش نامعتبر است.", show_alert=True)
            return
        coupon_code = context.user_data.get("coupon_code") or context.user_data.get("pending_payment_coupon")
        final_price = int(original_price)
        if coupon_code:
            result = apply_coupon(coupon_code, user_id, int(original_price))
            if result["status"] == "success":
                final_price = int(result["price"])
            else:
                coupon_code = None
                context.user_data.pop("coupon_code", None)
                context.user_data.pop("pending_payment_coupon", None)
        context.user_data["pending_payment_volume"] = str(volume)
        context.user_data["pending_payment_original_price"] = int(original_price)
        context.user_data["pending_payment_price"] = int(final_price)
        await show_card_payment(query, str(volume), int(original_price), coupon_code, int(final_price))
        return

    if data.startswith("paymentback_"):
        volume = data.split("_", 1)[1]
        original_price = (UNLIMITED_PLANS[volume]["price"] if is_unlimited_volume(volume) else (PLANS.get(volume) or context.user_data.get("custom_price")))
        if not original_price:
            await show_buy_menu(query)
            return
        coupon_code = context.user_data.get("coupon_code") or context.user_data.get("pending_payment_coupon")
        price = int(original_price)
        if coupon_code:
            result = apply_coupon(coupon_code, user_id, price)
            if result["status"] == "success": price = result["price"]
        await show_payment(query, volume, price, int(original_price), coupon_code)
        return

    # پرداخت عادی
   # =====================================================
    # پرداخت (خرید سرویس + شارژ کیف پول)
    # =====================================================
    if data.startswith("paid_"):
        parts = data.split("_")
        if len(parts) < 2:
            await query.answer("داده نامعتبر", show_alert=True)
            return

        volume = data[len("paid_"):]
        if not is_unlimited_volume(volume):
            volume = parts[1]

        # ---------- حالت شارژ کیف پول ----------
        if volume == "CHARGE":
            order_id = context.user_data.get("last_order_id")
            amount = context.user_data.get("charge_amount")

            if not order_id or not amount:
                await query.answer("سفارش شارژ پیدا نشد. دوباره تلاش کنید.", show_alert=True)
                return

            await rich_edit(query, 
                t(lang, "charge_created", order=order_id, amount=amount)
            )
            return

        # ---------- حالت خرید سرویس ----------
        if is_unlimited_volume(volume):
            base_price = UNLIMITED_PLANS[volume]["price"]
        elif volume in PLANS:
            base_price = PLANS[volume]
        else:
            # حجم دلخواه
            custom_volume = context.user_data.get("custom_volume")
            custom_price = context.user_data.get("custom_price")

            if not custom_volume or str(custom_volume) != str(volume):
                await query.answer("سفارش نامعتبر است. دوباره انتخاب کنید.", show_alert=True)
                return

            base_price = custom_price

        # اعمال کوپن (اگر وجود داشته باشد)
        coupon_code = context.user_data.get("coupon_code")
        stored_price = context.user_data.get("pending_payment_price")
        price = int(stored_price) if stored_price is not None else int(base_price)

        if stored_price is None and coupon_code:
            result = apply_coupon(coupon_code, user_id, base_price)
            if result["status"] == "success":
                price = int(result["price"])
            else:
                coupon_code = None
                context.user_data.pop("coupon_code", None)

        # ساخت سفارش
        order_id = create_order(user, volume, price, coupon_code)

        # پاک کردن stateها
        context.user_data.pop("coupon_code", None)
        context.user_data.pop("custom_volume", None)
        context.user_data.pop("custom_price", None)
        context.user_data.pop("pending_payment_price", None)
        context.user_data.pop("pending_payment_coupon", None)
        context.user_data.pop("pending_payment_volume", None)
        context.user_data.pop("pending_payment_original_price", None)
        context.user_data["last_order_id"] = order_id

        if is_unlimited_volume(volume):
            title = "♾️ Unlimited Service" if lang == "en" else ("♾️ خزمەتگوزاری بێ سنوور" if lang == "ku" else "♾️ سرویس نامحدود")
            receipt = (
                "📸 Send the receipt." if lang == "en"
                else ("📸 وێنەی پسوڵە بنێرە." if lang == "ku" else "📸 لطفاً تصویر رسید را ارسال کنید.")
            )
            amount_label = "Toman" if lang == "en" else "تومان"
            await rich_edit(query, f"{title}\n\n🧾 #{order_id}\n👤 {unlimited_display(volume, lang).replace('♾️ ', '')}\n💰 {price:,} {amount_label}\n\n{receipt}")
        else:
            await rich_edit(query, 
                t(lang, "order_created", order=order_id, volume=volume, price=price)
            )
        return
        if len(parts) < 2:
            return
        volume = parts[1]
        if volume in PLANS:
            base_price = PLANS[volume]
        else:
            custom_volume = context.user_data.get("custom_volume")
            custom_price = context.user_data.get("custom_price")
            if not custom_volume or str(custom_volume) != str(volume):
                await query.answer("سفارش نامعتبر است.", show_alert=True)
                return
            base_price = custom_price

        coupon_code = context.user_data.get("coupon_code")
        price = base_price
        if coupon_code:
            result = apply_coupon(coupon_code, user_id, base_price)
            if result["status"] == "success":
                price = result["price"]
            else:
                coupon_code = None
                context.user_data.pop("coupon_code", None)

        order_id = create_order(user, volume, price, coupon_code)
        context.user_data.pop("coupon_code", None)
        context.user_data.pop("custom_volume", None)
        context.user_data.pop("custom_price", None)
        context.user_data["last_order_id"] = order_id

        await rich_edit(query, t(lang, "order_created", order=order_id, volume=volume, price=price))
        return

    # پرداخت از کیف پول
    if data.startswith("walletpay_"):
        payload = data[len("walletpay_"):]
        try:
            volume, price_text = payload.rsplit("_", 1)
            price = int(price_text)
        except (ValueError, TypeError):
            return

        balance = get_balance(user_id)
        if balance < price:
            await query.answer(t(lang, "not_enough_balance"), show_alert=True)
            return

        # کسر از کیف پول
        success = change_balance(user_id, -price, "purchase", f"خرید سرویس {volume} گیگ", None)
        if not success:
            await query.answer("خطا در کسر موجودی.", show_alert=True)
            return

        # ساخت سفارش و تأیید خودکار
        order_id = create_order(user, volume, price, is_charge=0)
        result = await approve_order_with_source(order_id)

        if result["status"] == "approved":
            if is_unlimited_volume(volume):
                title = "♾️ Unlimited Service" if lang == "en" else ("♾️ خزمەتگوزاری بێ سنوور" if lang == "ku" else "♾️ سرویس نامحدود")
                plan_text = unlimited_display(volume, lang).replace("♾️ ", "")
                await rich_edit(query, 
                    t(lang, "paid_from_wallet", price=price, balance=get_balance(user_id)) +
                    f"\n\n{title}\n👤 {plan_text}\n📅 {result['expires_at']}\n🧾 #{order_id}\n\n🔗 {result['link']}"
                )
            else:
                await rich_edit(query, 
                    t(lang, "paid_from_wallet", price=price, balance=get_balance(user_id)) +
                    "\n\n" +
                    t(lang, "payment_confirmed",
                      volume=volume,
                      expires=result["expires_at"],
                      order=order_id,
                      link=result["link"])
                )
        elif result["status"] == "pg_error":
            await refund_wallet_after_pg_failure(user_id, price, order_id)
            await rich_edit(query, "❌ ساخت سرویس در PasarGuard ناموفق بود. مبلغ به کیف پول برگردانده شد.\n\n" + str(result.get("error") or "خطای نامشخص")[:300])
        elif result["status"] == "no_stock":
            # برگشت پول
            change_balance(user_id, price, "refund", f"برگشت وجه به دلیل نبود موجودی - سفارش #{order_id}")
            await rich_edit(query, "❌ موجودی سرویس کافی نیست. مبلغ به کیف پول برگردانده شد.")
        else:
            change_balance(user_id, price, "refund", f"برگشت وجه - سفارش #{order_id}")
            await rich_edit(query, "❌ خطا در تحویل سرویس. مبلغ به کیف پول برگردانده شد.")
        return

    # حجم دلخواه
    if data == "custom":
        context.user_data["waiting_custom_volume"] = True
        await rich_edit(query, t(lang, "custom_prompt"))
        return

    # تست
    if data == "trial":
        result = claim_trial(user)
        if result["status"] == "already":
            await rich_edit(query, t(lang, "trial_already"), reply_markup=InlineKeyboardMarkup([
                [styled_inline_button(t(lang, "buy"), callback_data="buy")],
                [styled_inline_button(t(lang, "back"), callback_data="home")],
            ]))
            return
        if result["status"] == "empty":
            await rich_edit(query, t(lang, "trial_empty"), reply_markup=InlineKeyboardMarkup([
                [styled_inline_button(t(lang, "back"), callback_data="home")]
            ]))
            return
        await rich_edit(query, t(lang, "trial_success", link=result["link"]), reply_markup=InlineKeyboardMarkup([
            [styled_inline_button(t(lang, "buy"), callback_data="buy")],
            [styled_inline_button(t(lang, "main_menu"), callback_data="home")],
        ]))
        return

    # سرویس‌های من
    if data == "my_services":
        rows = get_user_services(user_id)
        if not rows:
            text = t(lang, "no_services")
        else:
            text = t(lang, "services_title")
            for row in rows:
                if is_unlimited_volume(row["volume"]):
                    plan_text = unlimited_display(row["volume"], lang).replace("♾️ ", "")
                    if lang == "en":
                        text += f"🧾 Order #{row['id']}\n♾️ {plan_text}\n⏳ {row['expires_at'] or '-'}\n\n🔗 {row['link'] or '-'}\n\n"
                    elif lang == "ku":
                        text += f"🧾 داواکاری #{row['id']}\n♾️ {plan_text}\n⏳ {row['expires_at'] or '-'}\n\n🔗 {row['link'] or '-'}\n\n"
                    else:
                        text += f"🧾 سفارش #{row['id']}\n♾️ {plan_text}\n⏳ {row['expires_at'] or '-'}\n\n🔗 {row['link'] or '-'}\n\n"
                else:
                    text += t(lang, "service_item", id=row["id"], volume=row["volume"],
                              expires=row["expires_at"] or "-", link=row["link"] or "-")
        await rich_edit(query, text, reply_markup=InlineKeyboardMarkup([
            [styled_inline_button(t(lang, "renew"), callback_data="renew")],
            [styled_inline_button(t(lang, "back"), callback_data="home")],
        ]))
        return

    # تمدید
    if data == "renew":
        rows = get_user_services(user_id)
        if not rows:
            await rich_edit(query, t(lang, "renew_no_services"), reply_markup=InlineKeyboardMarkup([
                [styled_inline_button(t(lang, "buy"), callback_data="buy")],
                [styled_inline_button(t(lang, "back"), callback_data="home")],
            ]))
            return
        keyboard = []
        for row in rows[:10]:
            label = f"🔄 تمدید #{row['id']} | {row['volume']} گیگ"
            keyboard.append([styled_inline_button(label, callback_data=f"renew_{row['id']}")])
        keyboard.append([styled_inline_button(t(lang, "back"), callback_data="home")])
        await rich_edit(query, t(lang, "renew_choose"), reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("renew_") and not data.startswith("renewpay_") and not data.startswith("renewpaid_"):
        try:
            order_id = int(data.split("_")[1])
        except ValueError:
            return
        conn = get_db()
        order = conn.execute("SELECT * FROM orders WHERE id = ? AND user_id = ? AND status = 'approved'",
                             (order_id, user_id)).fetchone()
        conn.close()
        if not order:
            await query.answer("سرویس پیدا نشد.", show_alert=True)
            return
        # انتخاب حجم تمدید با گام‌های ۵ گیگ
        context.user_data["renew_order_id"] = order_id
        context.user_data["renew_volume"] = 5
        context.user_data["renew_price"] = 5 * PRICE_PER_GB
        volume = 5
        price = 5 * PRICE_PER_GB
        await rich_edit(query, 
            t(lang, "renew_payment", volume=volume, price=price),
            reply_markup=InlineKeyboardMarkup([
                [
                    styled_inline_button("➖", callback_data=f"renewminus_{order_id}"),
                    styled_inline_button(t(lang, "volume_label", volume=volume), callback_data="renew_noop"),
                    styled_inline_button("➕", callback_data=f"renewplus_{order_id}"),
                ],
                [styled_inline_button(t(lang, "pay"), callback_data=f"renewpay_{volume}")],
                [styled_inline_button(t(lang, "back"), callback_data="renew")],
            ])
        )
        return

    # افزایش حجم تمدید، هر بار ۵ گیگ
    if data.startswith("renewplus_") or data.startswith("renewminus_"):
        try:
            order_id = int(data.split("_")[1])
        except (ValueError, IndexError):
            return
        if context.user_data.get("renew_order_id") != order_id:
            await query.answer("سفارش تمدید معتبر نیست.", show_alert=True)
            return
        try:
            volume = int(context.user_data.get("renew_volume", 5))
        except (TypeError, ValueError):
            volume = 5
        if data.startswith("renewplus_"):
            volume += 5
        else:
            volume = max(5, volume - 5)
        price = volume * PRICE_PER_GB
        context.user_data["renew_volume"] = volume
        context.user_data["renew_price"] = price
        await rich_edit(query, 
            t(lang, "renew_payment", volume=volume, price=price),
            reply_markup=InlineKeyboardMarkup([
                [
                    styled_inline_button("➖", callback_data=f"renewminus_{order_id}"),
                    styled_inline_button(t(lang, "volume_label", volume=volume), callback_data="renew_noop"),
                    styled_inline_button("➕", callback_data=f"renewplus_{order_id}"),
                ],
                [styled_inline_button(t(lang, "pay"), callback_data=f"renewpay_{volume}")],
                [styled_inline_button(t(lang, "back"), callback_data="renew")],
            ])
        )
        await query.answer()
        return

    if data == "renew_noop":
        await query.answer()
        return

    if data.startswith("renewpay_"):
        volume = data.split("_")[1]
        stored_volume = context.user_data.get("renew_volume")
        stored_price = context.user_data.get("renew_price")
        if not stored_volume or str(stored_volume) != str(volume) or not stored_price:
            await query.answer("سفارش نامعتبر است.", show_alert=True)
            return
        context.user_data["pending_payment_volume"] = str(volume)
        context.user_data["pending_payment_original_price"] = int(stored_price)
        context.user_data["coupon_return_payment"] = False
        await rich_edit(query, 
            t(lang, "renew_paid", volume=volume, price=stored_price, card=CARD_NUMBER),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [styled_inline_button(t(lang, "paid"), callback_data=f"renewpaid_{volume}")],
                [styled_inline_button(t(lang, "coupon"), callback_data="coupon")],
                [styled_inline_button(t(lang, "back"), callback_data="renew")],
            ])
        )
        return

    if data.startswith("renewpaid_"):
        volume = data.split("_")[1]
        stored_volume = context.user_data.get("renew_volume")
        stored_price = context.user_data.get("renew_price")
        if not stored_volume or str(stored_volume) != str(volume) or not stored_price:
            await query.answer("سفارش نامعتبر است.", show_alert=True)
            return
        price = int(stored_price)
        coupon_code = context.user_data.get("coupon_code")
        if coupon_code:
            result = apply_coupon(coupon_code, user_id, price)
            if result["status"] == "success":
                price = result["price"]
            else:
                coupon_code = None
                context.user_data.pop("coupon_code", None)
        order_id = create_order(user, volume, price, coupon_code)
        context.user_data.pop("renew_volume", None)
        context.user_data.pop("renew_price", None)
        context.user_data.pop("pending_payment_volume", None)
        context.user_data.pop("pending_payment_original_price", None)
        context.user_data.pop("coupon_code", None)
        await rich_edit(query, t(lang, "renew_created", order=order_id, volume=volume, price=price))
        return

    # پشتیبانی
    if data == "support":
        await rich_edit(query, t(lang, "support_title"), reply_markup=InlineKeyboardMarkup([
            [styled_inline_button(t(lang, "create_ticket"), callback_data="new_ticket")],
            [styled_inline_button(t(lang, "back"), callback_data="home")],
        ]))
        return

    if data == "new_ticket":
        ticket_id = create_ticket(user_id)
        context.user_data["ticket_id"] = ticket_id
        context.user_data["waiting_ticket_message"] = True
        await rich_edit(query, t(lang, "ticket_prompt", id=ticket_id))
        return

    # دعوت
    if data == "referral":
        try:
            bot = await context.bot.get_me()
            link = referral_link(bot.username, user_id)
            count = referral_count(user_id)
            await rich_edit(query, 
                t(lang, "referral_title", count=count, link=link),
                reply_markup=InlineKeyboardMarkup([[styled_inline_button(t(lang, "back"), callback_data="home")]])
            )
        except Exception:
            await rich_edit(query, t(lang, "referral_error"))
        return

    # کد تخفیف — فقط در مرحله‌ای که شماره کارت نمایش داده شده
    if data == "coupon":
        context.user_data["waiting_coupon"] = True
        context.user_data["coupon_return_payment"] = True
        await rich_edit(query, t(lang, "coupon_prompt"))
        return

    # ==================== ادمین ====================
    # تایید / رد رسید پرداخت توسط ادمین
    if data.startswith("approve_") or data.startswith("reject_"):
        if user_id != ADMIN_ID:
            return
        try:
            order_id = int(data.split("_", 1)[1])
        except (ValueError, IndexError):
            await query.answer("❌ سفارش نامعتبر است.", show_alert=True)
            return

        if data.startswith("approve_"):
            try:
                result = await approve_order_with_source(order_id)
            except Exception as e:
                print(f"Approve order error: {type(e).__name__}: {e}")
                await query.answer("❌ خطا در تأیید سفارش.", show_alert=True)
                return

            if result.get("status") == "pg_error":
                err = str(result.get("error") or "خطای نامشخص")[:180]
                await query.answer(f"❌ ساخت سرویس در PasarGuard ناموفق بود.\n{err}", show_alert=True)
                pg_order = result.get("order")
                if pg_order:
                    try:
                        await context.bot.send_message(chat_id=pg_order["user_id"], text="❌ ساخت سرویس در پنل PasarGuard ناموفق بود. سفارش شما هنوز در انتظار بررسی است.")
                    except Exception:
                        pass
                return

            if result.get("status") == "approved":
                order = result.get("order")
                link = result.get("link") or "-"
                expires = result.get("expires_at") or "-"
                recipient_lang = get_user_language(order["user_id"]) or "fa"
                await query.edit_message_reply_markup(reply_markup=None)
                await context.bot.send_message(
                    chat_id=order["user_id"],
                    text=t(recipient_lang, "payment_confirmed",
                          volume=order["volume"], expires=expires, order=order_id, link=link)
                )
                await query.answer("✅ پرداخت تأیید شد.")
                return

            if result.get("status") == "charge_approved":
                order = result.get("order")
                recipient_lang = get_user_language(order["user_id"]) or "fa"
                await query.edit_message_reply_markup(reply_markup=None)
                await context.bot.send_message(
                    chat_id=order["user_id"],
                    text=t(recipient_lang, "charge_success", amount=order["price"], balance=get_balance(order["user_id"]))
                )
                await query.answer("✅ شارژ کیف پول تأیید شد.")
                return

            if result.get("status") == "no_stock":
                await query.answer("❌ برای این سفارش لینک دستی موجود نیست.", show_alert=True)
                return

            await query.answer("⚠️ این سفارش قبلاً پردازش شده است.", show_alert=True)
            return

        # رد سفارش
        try:
            ok, order = reject_order(order_id)
        except Exception as e:
            print(f"Reject order error: {type(e).__name__}: {e}")
            await query.answer("❌ خطا در رد سفارش.", show_alert=True)
            return
        if not ok:
            await query.answer("⚠️ این سفارش قبلاً پردازش شده است.", show_alert=True)
            return
        await query.edit_message_reply_markup(reply_markup=None)
        recipient_lang = get_user_language(order["user_id"]) or "fa"
        await context.bot.send_message(
            chat_id=order["user_id"],
            text=t(recipient_lang, "payment_rejected", order=order_id)
        )
        await query.answer("❌ پرداخت رد شد.")
        return

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

    if data == "admin_backup":
        if user_id != ADMIN_ID:
            return
        await send_db_backup(query, context)
        return

    if data == "pg_connect":
        if user_id != ADMIN_ID:
            return
        context.user_data["pg_waiting_url"] = True
        context.user_data.pop("pg_waiting_username", None)
        context.user_data.pop("pg_waiting_password", None)
        await rich_edit(query, "🔌 اتصال PasarGuard\n\nآدرس کامل پنل را ارسال کن.\n\nمثال:\nhttps://panel.example.com")
        return

    if data == "pg_status":
        if user_id != ADMIN_ID:
            return
        cfg = get_pasarguard_config()
        if not cfg or not cfg["enabled"]:
            await rich_edit(query, "📡 اتصال PasarGuard\n\n❌ پنل متصل نیست.", reply_markup=InlineKeyboardMarkup([[styled_inline_button("🔌 اتصال پنل", callback_data="pg_connect")], [styled_inline_button(t(lang, "admin_panel"), callback_data="admin")]]))
            return
        mode_labels = {"manual": "📝 دستی", "panel": "⚡ پنل PasarGuard", "fallback": "🔄 پنل → دستی در خطا"}
        try:
            groups = await asyncio.to_thread(pg_get_groups_sync)
            group_count = len(groups)
            status_text = "🟢 اتصال موفق"
        except Exception as exc:
            group_count = 0
            status_text = f"🔴 خطا: {str(exc)[:180]}"
        text = (f"📡 وضعیت PasarGuard\n\n{status_text}\n"
                f"🌐 {cfg['base_url']}\n"
                f"👤 {cfg['username']}\n"
                f"📦 گروه انتخابی: {cfg['group_name'] or 'انتخاب نشده'}\n"
                f"🧩 Template: {cfg['template_name'] or 'خودکار هنگام ساخت'}\n"
                f"🔢 تعداد گروه‌ها: {group_count}\n"
                f"🛒 حالت فروش: {mode_labels.get(cfg['mode'] or 'manual')}" )
        kb = [[styled_inline_button("📦 انتخاب گروه", callback_data="pg_groups")],
              [styled_inline_button("🛒 حالت فروش", callback_data="pg_mode")],
              [styled_inline_button("🔄 بروزرسانی اتصال", callback_data="pg_refresh")],
              [styled_inline_button("🗑 قطع اتصال", callback_data="pg_disconnect")],
              [styled_inline_button(t(lang, "admin_panel"), callback_data="admin")]]
        await rich_edit(query, text, reply_markup=InlineKeyboardMarkup(kb))
        return

    if data == "pg_refresh":
        if user_id != ADMIN_ID: return
        try:
            groups = await asyncio.to_thread(pg_get_groups_sync)
            await rich_edit(query, f"✅ اتصال پنل برقرار است.\n\n📦 گروه‌های قابل دریافت: {len(groups)}", reply_markup=InlineKeyboardMarkup([[styled_inline_button("📦 انتخاب گروه", callback_data="pg_groups")], [styled_inline_button("🔙 وضعیت پنل", callback_data="pg_status")]]))
        except Exception as exc:
            await rich_edit(query, f"❌ بروزرسانی ناموفق بود.\n\n{str(exc)[:300]}", reply_markup=InlineKeyboardMarkup([[styled_inline_button("🔙 وضعیت پنل", callback_data="pg_status")]]))
        return

    if data == "pg_groups":
        if user_id != ADMIN_ID: return
        try:
            groups = await asyncio.to_thread(pg_get_groups_sync)
        except Exception as exc:
            await query.answer(str(exc)[:190], show_alert=True); return
        keyboard = []
        cfg = get_pasarguard_config()
        selected_group_id = cfg["group_id"] if cfg else None
        for g in groups[:50]:
            mark = "✅ " if selected_group_id == g["id"] else ""
            keyboard.append([styled_inline_button(f"{mark}{g['name']} | ID {g['id']}", callback_data=f"pg_group_{g['id']}")])
        keyboard.append([styled_inline_button("🔙 وضعیت پنل", callback_data="pg_status")])
        await rich_edit(query, "📦 گروه‌های PasarGuard\n\nگروه موردنظر برای ساخت خودکار سرویس را انتخاب کن:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("pg_group_"):
        if user_id != ADMIN_ID: return
        try: group_id = int(data.split("_", 2)[2])
        except Exception: return
        try:
            groups = await asyncio.to_thread(pg_get_groups_sync)
            group = next((g for g in groups if g["id"] == group_id), None)
            if not group: raise RuntimeError("گروه پیدا نشد.")
            set_pasarguard_group(group_id, group["name"])
            conn = get_db()
            conn.execute("UPDATE pasarguard_config SET template_id=NULL, template_name=NULL, updated_at=? WHERE id=1", (now_text(),))
            conn.commit(); conn.close()
            await rich_edit(query, f"✅ گروه انتخاب شد.\n\n📦 {group['name']}\n🆔 {group_id}\n\nحالا در حالت «پنل» خریدها به‌صورت خودکار در PasarGuard ساخته می‌شوند.", reply_markup=InlineKeyboardMarkup([[styled_inline_button("🛒 حالت فروش", callback_data="pg_mode")], [styled_inline_button("🔙 وضعیت پنل", callback_data="pg_status")]]))
        except Exception as exc:
            await query.answer(str(exc)[:190], show_alert=True)
        return

    if data == "pg_mode":
        if user_id != ADMIN_ID: return
        cfg = get_pasarguard_config()
        current = (cfg["mode"] if cfg else "manual") or "manual"
        keyboard = [
            [styled_inline_button(("✅ " if current == "manual" else "") + "📝 دستی", callback_data="pg_mode_manual")],
            [styled_inline_button(("✅ " if current == "panel" else "") + "⚡ PasarGuard", callback_data="pg_mode_panel")],
            [styled_inline_button(("✅ " if current == "fallback" else "") + "🔄 پنل → دستی در خطا", callback_data="pg_mode_fallback")],
            [styled_inline_button("🔙 وضعیت پنل", callback_data="pg_status")],
        ]
        await rich_edit(query, "🛒 منبع ساخت سرویس\n\nدستی: فقط لینک‌هایی که خودت وارد کرده‌ای.\n\nPasarGuard: خرید مستقیم از پنل.\n\nFallback: اول پنل؛ اگر پنل خطا داد، لینک دستی استفاده می‌شود.", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("pg_mode_"):
        if user_id != ADMIN_ID: return
        mode = data[len("pg_mode_"):]
        if mode not in {"manual", "panel", "fallback"}: return
        cfg = get_pasarguard_config()
        if mode != "manual" and (not cfg or not cfg["group_id"]):
            await query.answer("اول پنل و گروه را انتخاب کن.", show_alert=True); return
        set_pasarguard_mode(mode)
        labels = {"manual":"📝 دستی", "panel":"⚡ PasarGuard", "fallback":"🔄 پنل → دستی در خطا"}
        await rich_edit(query, f"✅ حالت فروش روی «{labels[mode]}» قرار گرفت.", reply_markup=InlineKeyboardMarkup([[styled_inline_button("🔙 وضعیت پنل", callback_data="pg_status")]]))
        return

    if data == "pg_disconnect":
        if user_id != ADMIN_ID: return
        disable_pasarguard()
        await rich_edit(query, "🗑 اتصال PasarGuard قطع شد.\n\nسیستم دستی قبلی همچنان فعال است.", reply_markup=InlineKeyboardMarkup([[styled_inline_button("🔌 اتصال دوباره", callback_data="pg_connect")], [styled_inline_button(t(lang, "admin_panel"), callback_data="admin")]]))
        return

    if data == "admin_add":
        if user_id != ADMIN_ID:
            return
        context.user_data["admin_waiting_volume"] = True
        await rich_edit(query, "➕ افزودن لینک سرویس\n\nحجم را وارد کن:\n\nمثال: 10\nبرای نامحدود: UNLIMITED_1 یا UNLIMITED_2 یا UNLIMITED_3")
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
        delete_subscription(subscription_id)
        await rich_edit(query, "✅ لینک حذف شد.", reply_markup=InlineKeyboardMarkup([
            [styled_inline_button(t(lang, "admin_panel"), callback_data="admin")]
        ]))
        return

    if data == "admin_trial":
        if user_id != ADMIN_ID:
            return
        await show_admin_trial(query)
        return

    if data == "admin_trial_add":
        if user_id != ADMIN_ID:
            return
        context.user_data["admin_waiting_trial_link"] = True
        await rich_edit(query, "➕ افزودن لینک تست\n\nلینک Subscription تست را ارسال کن.")
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
        delete_free_trial(trial_id)
        await rich_edit(query, "✅ لینک تست حذف شد.", reply_markup=InlineKeyboardMarkup([
            [styled_inline_button(t(lang, "admin_trial"), callback_data="admin_trial")]
        ]))
        return

    if data == "admin_trial_stock":
        if user_id != ADMIN_ID:
            return
        stock = get_free_trial_stock()
        await rich_edit(query, 
            f"🎁 موجودی تست\n\n📦 100 مگابایت\n⏳ 1 روز\n🔢 موجودی: {stock}",
            reply_markup=InlineKeyboardMarkup([[styled_inline_button(t(lang, "admin_trial"), callback_data="admin_trial")]])
        )
        return

    if data == "admin_coupon":
        if user_id != ADMIN_ID:
            return
        context.user_data["admin_waiting_coupon"] = True
        await rich_edit(query, "🎟 ساخت کد تخفیف\n\nفرمت:\nCODE درصد تعداد\n\nمثال:\nHANZU20 20 100")
        return

    if data == "admin_broadcast":
        if user_id != ADMIN_ID:
            return
        context.user_data["admin_broadcast"] = True
        await rich_edit(query, "📢 پیام همگانی\n\nمتن پیام را بفرست.")
        return

    # مدیریت موجودی کاربر توسط ادمین
    if data == "admin_balance":
        if user_id != ADMIN_ID:
            return
        context.user_data["admin_waiting_balance_user"] = True
        await rich_edit(query, "💰 مدیریت موجودی\n\nآی‌دی عددی کاربر را ارسال کن:")
        return

    if data == "admin_tickets":
        if user_id != ADMIN_ID:
            return
        conn = get_db()
        rows = conn.execute("SELECT * FROM tickets WHERE status = 'open' ORDER BY id DESC LIMIT 20").fetchall()
        conn.close()
        if not rows:
            text = "🎫 تیکت باز نداریم."
            keyboard = [[styled_inline_button(t(lang, "admin_panel"), callback_data="admin")]]
        else:
            text = "🎫 تیکت‌های باز\n\n"
            keyboard = []
            for row in rows:
                text += f"#{row['id']} | User: {row['user_id']}\n"
                keyboard.append([styled_inline_button(t(lang, "ticket_item", id=row['id']), callback_data=f"ticket_{row['id']}")])
            keyboard.append([styled_inline_button(t(lang, "admin_panel"), callback_data="admin")])
        await rich_edit(query, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("ticket_"):
        if user_id != ADMIN_ID:
            return
        try:
            ticket_id = int(data.split("_")[1])
        except ValueError:
            return
        conn = get_db()
        ticket = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        messages = conn.execute("SELECT * FROM ticket_messages WHERE ticket_id = ? ORDER BY id ASC LIMIT 10", (ticket_id,)).fetchall()
        conn.close()
        if not ticket:
            return
        text = f"🎫 تیکت #{ticket_id}\n👤 User ID: {ticket['user_id']}\n\n"
        for msg in messages:
            sender = "کاربر" if msg["sender_id"] != ADMIN_ID else "ادمین"
            text += f"{sender}:\n{msg['message']}\n\n"
        context.user_data["admin_ticket_id"] = ticket_id
        context.user_data["admin_waiting_ticket_reply"] = True
        await rich_edit(query, 
            text + "\n✏️ پاسخ خود را ارسال کنید.",
            reply_markup=InlineKeyboardMarkup([
                [styled_inline_button(t(lang, "admin_close_ticket"), callback_data=f"close_ticket_{ticket_id}")],
                [styled_inline_button(t(lang, "admin_tickets"), callback_data="admin_tickets")],
            ])
        )
        return

    if data.startswith("close_ticket_"):
        if user_id != ADMIN_ID:
            return
        try:
            ticket_id = int(data.split("_")[2])
        except ValueError:
            return
        conn = get_db()
        ticket = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        conn.execute("UPDATE tickets SET status = 'closed', closed_at = ? WHERE id = ?", (now_text(), ticket_id))
        conn.commit()
        conn.close()
        if ticket:
            try:
                recipient_lang = get_user_language(ticket["user_id"]) or "fa"
                await context.bot.send_message(chat_id=ticket["user_id"], text=t(recipient_lang, "ticket_closed", id=ticket_id))
            except Exception:
                pass
        await rich_edit(query, "✅ تیکت بسته شد.", reply_markup=InlineKeyboardMarkup([
            [styled_inline_button(t(lang, "admin_panel"), callback_data="admin")]
        ]))
        return

    # تأیید / رد سفارش
    if data.startswith("approve_"):
        if user_id != ADMIN_ID:
            return
        try:
            order_id = int(data.split("_")[1])
        except ValueError:
            return
        result = await approve_order_with_source(order_id)
        if result["status"] == "not_found":
            await query.answer("سفارش پیدا نشد.", show_alert=True)
            return
        if result["status"] == "already_processed":
            await query.answer("این سفارش قبلاً پردازش شده.", show_alert=True)
            return
        if result["status"] == "no_stock":
            await query.answer("برای این حجم لینک موجود نیست.", show_alert=True)
            return
        if result["status"] == "pg_error":
            err = str(result.get("error") or "خطای نامشخص")[:180]
            await query.answer(f"❌ ساخت سرویس در پنل ناموفق بود.\n{err}", show_alert=True)
            return

        order = result["order"]
        recipient_lang = get_user_language(order["user_id"]) or "fa"

        if result["status"] == "charge_approved":
            balance = get_balance(order["user_id"])
            await context.bot.send_message(
                chat_id=order["user_id"],
                text=t(recipient_lang, "charge_success", amount=order["price"], balance=balance)
            )
            try:
                await query.edit_message_caption(caption=f"✅ شارژ کیف پول #{order_id} تأیید شد.\n💰 {order['price']:,} تومان")
            except Exception:
                await rich_edit(query, f"✅ شارژ کیف پول #{order_id} تأیید شد.\n💰 {order['price']:,} تومان")
            return

        if is_unlimited_volume(order["volume"]):
            plan_text = unlimited_display(order["volume"], recipient_lang).replace("♾️ ", "")
            if recipient_lang == "en":
                confirmation_text = f"✅ Payment approved.\n\n♾️ Unlimited Service\n👤 {plan_text}\n📅 {result['expires_at']}\n🧾 #{order_id}\n\n🔗 {result['link']}"
            elif recipient_lang == "ku":
                confirmation_text = f"✅ پارەدان پشتڕاستکرایەوە.\n\n♾️ خزمەتگوزاری بێ سنوور\n👤 {plan_text}\n📅 {result['expires_at']}\n🧾 #{order_id}\n\n🔗 {result['link']}"
            else:
                confirmation_text = f"✅ پرداخت تأیید شد.\n\n♾️ سرویس نامحدود\n👤 {plan_text}\n📅 {result['expires_at']}\n🧾 #{order_id}\n\n🔗 {result['link']}"
        else:
            confirmation_text = t(recipient_lang, "payment_confirmed",
                   volume=order["volume"],
                   expires=result["expires_at"],
                   order=order_id,
                   link=result["link"])
        await context.bot.send_message(chat_id=order["user_id"], text=confirmation_text)
        try:
            await query.edit_message_caption(
                caption=(f"✅ سفارش #{order_id} تأیید شد.\n♾️ {unlimited_display(order['volume'], recipient_lang).replace('♾️ ', '')}\n💰 {order['price']:,} تومان\n📅 {result['expires_at']}" if is_unlimited_volume(order['volume']) else f"✅ سفارش #{order_id} تأیید شد.\n📦 {order['volume']} گیگ\n💰 {order['price']:,} تومان\n📅 {result['expires_at']}")
            )
        except Exception:
            await rich_edit(query, 
                f"✅ سفارش #{order_id} تأیید شد.\n📦 {order['volume']} گیگ\n💰 {order['price']:,} تومان\n📅 {result['expires_at']}"
            )
        return

    if data.startswith("reject_"):
        if user_id != ADMIN_ID:
            return
        try:
            order_id = int(data.split("_")[1])
        except ValueError:
            return
        changed, order = reject_order(order_id)
        if not order:
            await query.answer("سفارش پیدا نشد.", show_alert=True)
            return
        if not changed:
            await query.answer("این سفارش قبلاً پردازش شده.", show_alert=True)
            return
        recipient_lang = get_user_language(order["user_id"]) or "fa"
        await context.bot.send_message(
            chat_id=order["user_id"],
            text=t(recipient_lang, "payment_rejected", order=order_id)
        )
        try:
            await query.edit_message_caption(caption=f"❌ سفارش #{order_id} رد شد.\n📦 {order['volume']}\n💰 {order['price']:,} تومان")
        except Exception:
            await rich_edit(query, f"❌ سفارش #{order_id} رد شد.\n📦 {order['volume']}\n💰 {order['price']:,} تومان")
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
        await show_language_selector_message(update.message)
        return

    # ==================== کیبورد پایینی اصلی ====================
    # فقط وقتی کاربر در حال وارد کردن اطلاعات یک فرم نیست، دکمه‌های منو را پردازش می‌کنیم.
    menu_map = {
        t(lang, "panel"): "panel",
        t(lang, "buy"): "buy",
        t(lang, "trial"): "trial",
        t(lang, "services"): "services",
        t(lang, "renew"): "renew",
        t(lang, "referral"): "referral",
        t(lang, "wallet"): "wallet",
        t(lang, "support"): "support",
        t(lang, "language"): "language",
    }
    if user.id == ADMIN_ID:
        menu_map[t("fa", "admin")] = "admin"

    # دکمه‌های منو باید قبل از فرم‌های معمولی بررسی شوند، ولی نه وقتی کاربر عمداً
    # در حال وارد کردن متن/مبلغ/کد تخفیف/پاسخ تیکت است.
    waiting_state = any([
        context.user_data.get("waiting_coupon"),
        context.user_data.get("waiting_charge_amount"),
        context.user_data.get("waiting_ticket_message"),
        context.user_data.get("admin_waiting_coupon"),
        context.user_data.get("admin_broadcast"),
        context.user_data.get("admin_waiting_ticket_reply"),
        context.user_data.get("admin_waiting_volume"),
        context.user_data.get("admin_waiting_link"),
        context.user_data.get("admin_waiting_trial_link"),
        context.user_data.get("admin_waiting_balance_user"),
        context.user_data.get("admin_waiting_balance_amount"),
        context.user_data.get("pg_waiting_url"),
        context.user_data.get("pg_waiting_username"),
        context.user_data.get("pg_waiting_password"),
    ])
    if not waiting_state and text in menu_map:
        action = menu_map[text]
        if action == "panel":
            await panel_command(update, context)
            return
        if action == "buy":
            await buy_command(update, context)
            return
        if action == "trial":
            await trial_command(update, context)
            return
        if action == "services":
            await services_command(update, context)
            return
        if action == "support":
            await support_command(update, context)
            return
        if action == "language":
            await language_command(update, context)
            return
        if action == "wallet":
            await rich_reply_text(update.message, 
                t(lang, "wallet_title", balance=get_balance(user.id)),
                reply_markup=InlineKeyboardMarkup([
                    [styled_inline_button(t(lang, "charge_wallet"), callback_data="charge_wallet")],
                    [styled_inline_button(t(lang, "wallet_history"), callback_data="wallet_history")],
                    [styled_inline_button(t(lang, "back"), callback_data="home")],
                ])
            )
            return
        if action == "referral":
            try:
                bot = await context.bot.get_me()
                link = referral_link(bot.username, user.id)
                count = referral_count(user.id)
                await rich_reply_text(update.message, 
                    t(lang, "referral_title", count=count, link=link),
                    reply_markup=InlineKeyboardMarkup([[styled_inline_button(t(lang, "back"), callback_data="home")]])
                )
            except Exception:
                await rich_reply_text(update.message, t(lang, "referral_error"))
            return
        if action == "renew":
            rows = get_user_services(user.id)
            if not rows:
                await rich_reply_text(update.message, 
                    t(lang, "renew_no_services"),
                    reply_markup=InlineKeyboardMarkup([[styled_inline_button(t(lang, "buy"), callback_data="buy")], [styled_inline_button(t(lang, "back"), callback_data="home")]])
                )
                return
            keyboard = [[styled_inline_button(f"{t(lang, 'renew')} #{row['id']} | {row['volume']} {t(lang, 'volume_label', volume='').strip()}", callback_data=f"renew_{row['id']}")] for row in rows[:10]]
            keyboard.append([styled_inline_button(t(lang, "back"), callback_data="home")])
            await rich_reply_text(update.message, t(lang, "renew_choose"), reply_markup=InlineKeyboardMarkup(keyboard))
            return
        if action == "admin" and user.id == ADMIN_ID:
            # پنل مدیریت را با همان منوی اصلی ادمین نمایش می‌دهیم.
            keyboard = [
                [styled_inline_button(t(lang, "admin_add"), callback_data="admin_add")],
                [styled_inline_button(t(lang, "admin_trial"), callback_data="admin_trial")],
                [styled_inline_button(t(lang, "admin_stock"), callback_data="admin_stock"), styled_inline_button(t(lang, "admin_delete"), callback_data="admin_delete")],
                [styled_inline_button(t(lang, "admin_coupon"), callback_data="admin_coupon"), styled_inline_button(t(lang, "admin_balance"), callback_data="admin_balance")],
                [styled_inline_button(t(lang, "admin_broadcast"), callback_data="admin_broadcast")],
                [styled_inline_button(t(lang, "admin_stats"), callback_data="admin_stats"), styled_inline_button(t(lang, "admin_orders"), callback_data="admin_orders")],
                [styled_inline_button(t(lang, "admin_tickets"), callback_data="admin_tickets")],
                [styled_inline_button("🔌 اتصال پنل PasarGuard", callback_data="pg_connect")],
                [styled_inline_button("📡 وضعیت / گروه پنل", callback_data="pg_status")],
                [styled_inline_button(t(lang, "back"), callback_data="home")],
            ]
            await rich_reply_text(update.message, "⚙️ پنل مدیریت", reply_markup=InlineKeyboardMarkup(keyboard))
            return

    # اتصال PasarGuard - مرحله ۱: آدرس پنل
    if user.id == ADMIN_ID and context.user_data.get("pg_waiting_url"):
        base_url = text.strip()
        if not base_url.startswith(("http://", "https://")):
            await rich_reply_text(update.message, "❌ آدرس پنل باید با http:// یا https:// شروع شود.")
            return
        context.user_data["pg_waiting_url"] = False
        context.user_data["pg_waiting_username"] = True
        context.user_data["pg_base_url"] = base_url
        await rich_reply_text(update.message, "👤 نام کاربری مدیر PasarGuard را ارسال کن.")
        return

    if user.id == ADMIN_ID and context.user_data.get("pg_waiting_username"):
        context.user_data["pg_waiting_username"] = False
        context.user_data["pg_waiting_password"] = True
        context.user_data["pg_username"] = text.strip()
        await rich_reply_text(update.message, "🔐 رمز عبور PasarGuard را ارسال کن.\n\nبعد از دریافت، پیام رمز از چت حذف می‌شود.")
        return

    if user.id == ADMIN_ID and context.user_data.get("pg_waiting_password"):
        context.user_data["pg_waiting_password"] = False
        password = text
        base_url = context.user_data.pop("pg_base_url", "")
        username = context.user_data.pop("pg_username", "")
        try:
            try:
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
            except Exception:
                pass
            save_pasarguard_connection(base_url, username, password)
            await asyncio.to_thread(_pg_login_sync, True)
            groups = await asyncio.to_thread(pg_get_groups_sync)
            keyboard = [[styled_inline_button(f"{g['name']} | ID {g['id']}", callback_data=f"pg_group_{g['id']}")] for g in groups[:50]]
            keyboard.append([styled_inline_button("🔙 پنل مدیریت", callback_data="admin")])
            await context.bot.send_message(chat_id=user.id, text=f"✅ اتصال PasarGuard با موفقیت برقرار شد.\n\n📦 {len(groups)} گروه پیدا شد.\nگروه پیش‌فرض را انتخاب کن:", reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as exc:
            await rich_reply_text(update.message, f"❌ اتصال ناموفق بود.\n\n{str(exc)[:350]}", reply_markup=InlineKeyboardMarkup([[styled_inline_button("🔌 تلاش دوباره", callback_data="pg_connect")], [styled_inline_button("🔙 پنل مدیریت", callback_data="admin")]]))
        return

    # شارژ کیف پول - دریافت مبلغ
    if context.user_data.get("waiting_charge_amount"):
        context.user_data["waiting_charge_amount"] = False
        try:
            amount = int(text.replace(",", "").replace("،", ""))
            if amount < MIN_CHARGE:
                raise ValueError
        except ValueError:
            await rich_reply_text(update.message, t(lang, "invalid_charge", min=MIN_CHARGE))
            return

        context.user_data["charge_amount"] = amount
        order_id = create_order(user, "CHARGE", amount, is_charge=1)
        context.user_data["last_order_id"] = order_id

        await rich_reply_text(update.message, 
            t(lang, "charge_payment", amount=amount, card=CARD_NUMBER),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [styled_inline_button(t(lang, "paid"), callback_data=f"paid_CHARGE")],
                [styled_inline_button(t(lang, "back"), callback_data="wallet")],
            ])
        )
        return

    # تیکت کاربر
    if context.user_data.get("waiting_ticket_message"):
        ticket_id = context.user_data.get("ticket_id")
        if not ticket_id:
            return
        add_ticket_message(ticket_id, user.id, text)
        context.user_data["waiting_ticket_message"] = False
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🎫 تیکت جدید #{ticket_id}\n\n👤 {user.first_name or '-'}\n🆔 {user.id}\n\n💬 {text}",
            reply_markup=InlineKeyboardMarkup([
                [styled_inline_button(t(lang, "admin_ticket_view"), callback_data=f"ticket_{ticket_id}")]
            ])
        )
        await rich_reply_text(update.message, t(lang, "ticket_created", id=ticket_id))
        return

    # پاسخ ادمین به تیکت
    if user.id == ADMIN_ID and context.user_data.get("admin_waiting_ticket_reply"):
        ticket_id = context.user_data.get("admin_ticket_id")
        conn = get_db()
        ticket = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        conn.close()
        if not ticket:
            return
        add_ticket_message(ticket_id, ADMIN_ID, text)
        recipient_lang = get_user_language(ticket["user_id"]) or "fa"
        await context.bot.send_message(
            chat_id=ticket["user_id"],
            text=f"💬 پاسخ پشتیبانی\n\n🎫 تیکت #{ticket_id}\n\n{text}"
        )
        await rich_reply_text(update.message, "✅ پاسخ برای کاربر ارسال شد.")
        context.user_data["admin_waiting_ticket_reply"] = False
        return

    # پیام همگانی
    if user.id == ADMIN_ID and context.user_data.get("admin_broadcast"):
        context.user_data["admin_broadcast"] = False
        conn = get_db()
        users = conn.execute("SELECT user_id FROM users").fetchall()
        conn.close()
        sent = failed = 0
        for row in users:
            try:
                await context.bot.send_message(chat_id=row["user_id"], text=text)
                sent += 1
                await asyncio.sleep(0.05)
            except Exception:
                failed += 1
        await rich_reply_text(update.message, f"📢 ارسال همگانی تمام شد.\n\n✅ موفق: {sent}\n❌ ناموفق: {failed}")
        return

    # ساخت کوپن
    if user.id == ADMIN_ID and context.user_data.get("admin_waiting_coupon"):
        parts = text.split()
        if len(parts) != 3:
            await rich_reply_text(update.message, "❌ فرمت اشتباه است.\n\nمثال:\nHANZU20 20 100")
            return
        code = parts[0].upper()
        try:
            percent = int(parts[1])
            max_uses = int(parts[2])
            if percent <= 0 or percent > 100 or max_uses < 0:
                raise ValueError
        except ValueError:
            await rich_reply_text(update.message, "❌ درصد یا تعداد نامعتبر است.")
            return
        success = create_coupon(code, percent, max_uses)
        if success:
            await rich_reply_text(update.message, f"✅ کد تخفیف ساخته شد.\n\n🎟 {code}\n💰 {percent}%\n🔢 {'نامحدود' if max_uses == 0 else max_uses}")
        else:
            await rich_reply_text(update.message, "❌ این کد قبلاً وجود دارد.")
        context.user_data["admin_waiting_coupon"] = False
        return

    # افزودن تست
    if user.id == ADMIN_ID and context.user_data.get("admin_waiting_trial_link"):
        if not (text.startswith("http://") or text.startswith("https://")):
            await rich_reply_text(update.message, "❌ لینک معتبر نیست.")
            return
        add_free_trial(text)
        context.user_data["admin_waiting_trial_link"] = False
        await rich_reply_text(update.message, "✅ لینک تست اضافه شد.")
        return

    # مدیریت موجودی توسط ادمین - دریافت آی‌دی کاربر
    if user.id == ADMIN_ID and context.user_data.get("admin_waiting_balance_user"):
        try:
            target_id = int(text)
        except ValueError:
            await rich_reply_text(update.message, "❌ آی‌دی باید عدد باشد.")
            return
        context.user_data["admin_waiting_balance_user"] = False
        context.user_data["admin_balance_user_id"] = target_id
        context.user_data["admin_waiting_balance_amount"] = True
        balance = get_balance(target_id)
        await rich_reply_text(update.message, 
            f"کاربر: {target_id}\nموجودی فعلی: {balance:,} تومان\n\n"
            "مبلغ را وارد کن (مثبت برای افزایش، منفی برای کاهش):\n\nمثال:\n50000\nیا\n-20000"
        )
        return

    # مدیریت موجودی - دریافت مبلغ
    if user.id == ADMIN_ID and context.user_data.get("admin_waiting_balance_amount"):
        try:
            amount = int(text.replace(",", "").replace("،", ""))
        except ValueError:
            await rich_reply_text(update.message, "❌ مبلغ نامعتبر است.")
            return
        target_id = context.user_data.get("admin_balance_user_id")
        context.user_data["admin_waiting_balance_amount"] = False
        context.user_data.pop("admin_balance_user_id", None)

        if amount == 0:
            await rich_reply_text(update.message, "❌ مبلغ صفر مجاز نیست.")
            return

        type_ = "admin_add" if amount > 0 else "admin_remove"
        desc = "افزایش توسط ادمین" if amount > 0 else "کاهش توسط ادمین"
        success = change_balance(target_id, amount, type_, desc)
        if success:
            new_balance = get_balance(target_id)
            await rich_reply_text(update.message, f"✅ انجام شد.\n\nکاربر: {target_id}\nتغییر: {amount:,}\nموجودی جدید: {new_balance:,}")
            try:
                await context.bot.send_message(
                    chat_id=target_id,
                    text=f"💰 موجودی کیف پول شما توسط مدیریت تغییر کرد.\n\n💵 موجودی جدید: {new_balance:,} تومان"
                )
            except Exception:
                pass
        else:
            await rich_reply_text(update.message, "❌ خطا در تغییر موجودی.")
        return

    # حجم دلخواه
    if context.user_data.get("waiting_custom_volume"):
        context.user_data["waiting_custom_volume"] = False
        try:
            volume = int(text)
            if volume <= 0 or volume > 1000:
                raise ValueError
        except ValueError:
            await rich_reply_text(update.message, t(lang, "invalid_volume"))
            return

        price = volume * PRICE_PER_GB
        context.user_data["custom_volume"] = volume
        context.user_data["custom_price"] = price

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

        # مرحله اول: هنوز شماره کارت نمایش داده نمی‌شود.
        context.user_data["pending_payment_volume"] = volume
        context.user_data["pending_payment_original_price"] = price
        context.user_data["pending_payment_coupon"] = coupon_code
        payment_text = t(lang, "payment", volume=volume, price=final_price)
        if original_price != final_price and coupon_code:
            payment_text += t(lang, "original_price", original=original_price, coupon=coupon_code)
        keyboard = [
            [styled_inline_button(t(lang, "pay"), callback_data=f"pay_{volume}")],
            [styled_inline_button(t(lang, "back"), callback_data="buy")],
        ]
        await rich_reply_text(update.message, payment_text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # کوپن کاربر
    if context.user_data.get("waiting_coupon"):
        context.user_data["waiting_coupon"] = False
        coupon = get_coupon(text.upper())
        if not coupon:
            await rich_reply_text(update.message, t(lang, "coupon_invalid"))
            return
        if user_used_coupon(coupon["id"], user.id):
            await rich_reply_text(update.message, t(lang, "coupon_used"))
            return
        if coupon["max_uses"] > 0 and coupon["used_count"] >= coupon["max_uses"]:
            await rich_reply_text(update.message, t(lang, "coupon_invalid"))
            return
        context.user_data["coupon_code"] = coupon["code"]
        # اگر کاربر کد تخفیف را از مرحله شماره کارت وارد کرده، همان پرداخت را با قیمت جدید باز کن.
        if context.user_data.pop("coupon_return_payment", False):
            volume = context.user_data.get("pending_payment_volume") or context.user_data.get("renew_volume")
            original_price = context.user_data.get("pending_payment_original_price") or context.user_data.get("renew_price")
            if volume and original_price:
                if context.user_data.get("renew_order_id"):
                    price = int(original_price)
                    result = apply_coupon(coupon["code"], user.id, price)
                    if result["status"] == "success": price = result["price"]
                    await rich_reply_text(update.message, 
                        t(lang, "renew_paid", volume=volume, price=price, card=CARD_NUMBER),
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup([
                            [styled_inline_button(t(lang, "paid"), callback_data=f"renewpaid_{volume}")],
                            [styled_inline_button(t(lang, "coupon"), callback_data="coupon")],
                            [styled_inline_button(t(lang, "back"), callback_data="renew")],
                        ])
                    )
                else:
                    result = apply_coupon(coupon["code"], user.id, int(original_price))
                    if result["status"] != "success":
                        await rich_reply_text(update.message, t(lang, "coupon_invalid"))
                        return
                    final_price = int(result["price"])
                    context.user_data["pending_payment_price"] = final_price
                    context.user_data["pending_payment_volume"] = str(volume)
                    context.user_data["pending_payment_original_price"] = int(original_price)
                    context.user_data["pending_payment_coupon"] = coupon["code"]
                    await rich_reply_text(update.message, 
                        t(lang, "payment", volume=volume, price=final_price)
                        + t(lang, "original_price", original=int(original_price), coupon=coupon["code"])
                        + t(lang, "card", card=CARD_NUMBER),
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup([
                            [styled_inline_button(t(lang, "paid"), callback_data=f"paid_{volume}")],
                            [styled_inline_button(t(lang, "coupon"), callback_data="coupon")],
                            [styled_inline_button(t(lang, "back"), callback_data=f"paymentback_{volume}")],
                        ])
                    )
                return
        await rich_reply_text(update.message, t(lang, "coupon_valid", code=coupon["code"], percent=coupon["percent"]))
        return

    # حجم لینک ادمین
    if user.id == ADMIN_ID and context.user_data.get("admin_waiting_volume"):
        raw_volume = text.strip().upper().replace(" ", "")
        if raw_volume in UNLIMITED_PLANS:
            volume = raw_volume
            label = unlimited_display(volume, "fa")
        else:
            try:
                volume_num = int(float(raw_volume))
                if volume_num <= 0 or volume_num > 1000:
                    raise ValueError
                volume = str(volume_num)
                label = f"{volume_num} گیگ"
            except ValueError:
                await rich_reply_text(update.message, "❌ حجم نامعتبر است.\n\nبرای نامحدود از UNLIMITED_1 یا UNLIMITED_2 یا UNLIMITED_3 استفاده کن.")
                return
        context.user_data["admin_waiting_volume"] = False
        context.user_data["admin_add_volume"] = volume
        context.user_data["admin_waiting_link"] = True
        await rich_reply_text(update.message, f"✅ {label} ثبت شد.\n\nحالا لینک Subscription را ارسال کن.")
        return

    # لینک سرویس ادمین
    if user.id == ADMIN_ID and context.user_data.get("admin_waiting_link"):
        if not (text.startswith("http://") or text.startswith("https://")):
            await rich_reply_text(update.message, "❌ لینک معتبر نیست.")
            return
        volume = context.user_data.get("admin_add_volume")
        add_subscription(volume, text)
        context.user_data.pop("admin_waiting_link", None)
        context.user_data.pop("admin_add_volume", None)
        label = unlimited_display(volume, "fa") if is_unlimited_volume(volume) else f"📦 {volume} گیگ"
        await rich_reply_text(update.message, f"✅ لینک اضافه شد.\n\n{label}")
        return


# =========================================================
# رسید پرداخت
# =========================================================

async def receipt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_language(update.effective_user.id) or "fa"
    user = update.effective_user
    ensure_user(user)
    lang = get_user_language(user.id) or "fa"

    order = get_latest_pending_order(user.id)
    if not order:
        await rich_reply_text(update.message, t(lang, "no_pending"))
        return

    charge_text = " (شارژ کیف پول)" if order["is_charge"] else ""
    caption = (
        f"💳 رسید پرداخت جدید{charge_text}\n\n"
        f"🧾 سفارش: #{order['id']}\n"
        f"👤 نام: {user.first_name or '-'}\n"
        f"👤 Username: @{user.username if user.username else '-'}\n"
        f"🆔 User ID: {user.id}\n\n"
        f"📦 {order['volume']}\n"
        f"💰 مبلغ: {order['price']:,} تومان\n"
        f"🕐 زمان: {order['created_at']}"
    )

    keyboard = [[
        styled_inline_button(t(lang, "approve_payment"), callback_data=f"approve_{order['id']}"),
        styled_inline_button(t(lang, "reject_payment"), callback_data=f"reject_{order['id']}")
    ]]

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=update.message.photo[-1].file_id,
        caption=caption,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    await rich_reply_text(update.message, t(lang, "receipt_received", order=order["id"]))


# =========================================================
# یادآوری انقضا
# =========================================================

async def expiration_checker(application):
    while True:
        try:
            conn = get_db()
            rows = conn.execute("SELECT * FROM orders WHERE status = 'approved' AND expires_at IS NOT NULL AND is_charge = 0").fetchall()
            conn.close()
            now = datetime.now()
            for row in rows:
                try:
                    expires = datetime.strptime(row["expires_at"], "%Y-%m-%d %H:%M:%S")
                except Exception:
                    continue
                remaining = expires - now
                days = remaining.total_seconds() / 86400
                reminder_type = None
                message = None
                lang = get_user_language(row["user_id"]) or "fa"
                if 2.5 <= days <= 3.5:
                    reminder_type = "3days"
                    message = t(lang, "reminder_3", order=row["id"])
                elif 0.5 <= days <= 1.5:
                    reminder_type = "1day"
                    message = t(lang, "reminder_1", order=row["id"])
                if not reminder_type:
                    continue
                conn = get_db()
                exists = conn.execute("SELECT id FROM reminders WHERE order_id = ? AND reminder_type = ?",
                                      (row["id"], reminder_type)).fetchone()
                if not exists:
                    conn.execute("INSERT INTO reminders (order_id, user_id, reminder_type, sent_at) VALUES (?, ?, ?, ?)",
                                 (row["id"], row["user_id"], reminder_type, now_text()))
                    conn.commit()
                    try:
                        await application.bot.send_message(chat_id=row["user_id"], text=message)
                    except Exception:
                        pass
                conn.close()
        except Exception as e:
            print("Expiration checker error:", e)
        await asyncio.sleep(6 * 60 * 60)


# =========================================================
# Mini App API
# =========================================================

def _telegram_user_from_init_data(init_data):
    if not BOT_TOKEN or not init_data:
        return None
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = pairs.pop("hash", "")
        if not received_hash:
            return None
        data_check = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
        secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        calc = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calc, received_hash):
            return None
        auth_date = int(pairs.get("auth_date", "0"))
        if abs(int(__import__("time").time()) - auth_date) > 86400:
            return None
        raw_user = pairs.get("user")
        if not raw_user:
            return None
        return json.loads(unquote(raw_user))
    except Exception:
        return None


def _api_user(init_data):
    data = _telegram_user_from_init_data(init_data)
    if not data or not data.get("id"):
        return None
    class U: pass
    u = U()
    u.id = int(data["id"])
    u.username = data.get("username", "")
    u.first_name = data.get("first_name", "")
    ensure_user(u)
    return u


def _json_bytes(obj):
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")


def _api_purchase_wallet(user, volume, price):
    # خرید کیف پول کاملاً اتمیک است: یا همه مراحل انجام می‌شوند یا هیچ‌کدام.
    # volume به شکل عددی نرمال می‌شود تا موجودی‌هایی مثل «10»، «10GB» یا «10 گیگ»
    # هم قابل تطبیق باشند.
    raw_volume = str(volume).strip()
    normalized_volume = raw_volume.upper() if raw_volume.upper() in UNLIMITED_PLANS else _normalize_volume(raw_volume)
    if not normalized_volume:
        return {"status":"invalid_volume"}

    for attempt in range(3):
        conn = get_db()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT balance FROM users WHERE user_id = ?", (user.id,)).fetchone()
            if not row:
                conn.rollback()
                return {"status":"error", "error":"user_not_found"}
            balance = int(row["balance"] or 0)
            if balance < price:
                conn.rollback()
                return {"status":"insufficient_balance", "balance":balance}

            # تطبیق عددی حجم، مستقل از فرمت ذخیره‌شده در subscriptions.volume
            sub = stock_subscription_query(conn, normalized_volume)
            if not sub:
                conn.rollback()
                return {"status":"no_stock", "balance":balance, "volume":normalized_volume}

            now = datetime.now()
            expires = now + timedelta(days=SERVICE_DAYS)

            # کم‌کردن موجودی فقط داخل همان تراکنش
            cur_balance = conn.execute(
                "UPDATE users SET balance = balance - ? WHERE user_id = ? AND COALESCE(balance, 0) >= ?",
                (price, user.id, price)
            )
            if cur_balance.rowcount != 1:
                conn.rollback()
                return {"status":"insufficient_balance", "balance":balance}

            tx = conn.execute(
                "INSERT INTO wallet_transactions (user_id, amount, type, description, order_id, created_at) VALUES (?, ?, ?, ?, NULL, ?)",
                (user.id, -price, "purchase", f"خرید سرویس {unlimited_display(normalized_volume, 'fa') if is_unlimited_volume(normalized_volume) else normalized_volume + ' گیگ'}", now_text())
            )
            order_id = conn.execute(
                "INSERT INTO orders (user_id, username, first_name, volume, price, status, created_at, is_charge, subscription_id, approved_at, expires_at) VALUES (?, ?, ?, ?, ?, 'approved', ?, 0, ?, ?, ?)",
                (user.id, user.username or "", user.first_name or "", normalized_volume, price, now_text(), sub["id"], now.strftime("%Y-%m-%d %H:%M:%S"), expires.strftime("%Y-%m-%d %H:%M:%S"))
            ).lastrowid
            conn.execute("UPDATE wallet_transactions SET order_id = ? WHERE id = ?", (order_id, tx.lastrowid))
            used = conn.execute("UPDATE subscriptions SET used = 1 WHERE id = ? AND used = 0", (sub["id"],))
            if used.rowcount != 1:
                raise RuntimeError("subscription_race")

            conn.commit()
            return {
                "status":"approved",
                "order_id":order_id,
                "volume":normalized_volume,
                "price":price,
                "balance":balance-price,
                "link":sub["link"],
                "expires_at":expires.strftime("%Y-%m-%d %H:%M:%S")
            }
        except sqlite3.OperationalError as e:
            try: conn.rollback()
            except Exception: pass
            if "locked" in str(e).lower() and attempt < 2:
                import time
                time.sleep(0.25 * (attempt + 1))
                continue
            return {"status":"error", "error":str(e)}
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            return {"status":"error", "error":str(e)}
        finally:
            conn.close()
    return {"status":"error", "error":"purchase_retry_exhausted"}


def _telegram_send_photo_base64(user_id, volume, price, image_b64, order_id):
    try:
        raw = base64.b64decode(image_b64.split(",",1)[-1])
        boundary = "----HanzuVPNBoundary"
        body = bytearray()
        def field(name, value):
            body.extend((f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n").encode())
        field("chat_id", str(ADMIN_ID))
        
        conn = get_db()
        try:
            row = conn.execute("SELECT username, first_name, created_at FROM orders WHERE id=?", (order_id,)).fetchone()
        finally:
            conn.close()
        username = (row["username"] if row else "") or "-"
        first_name = (row["first_name"] if row else "") or "-"
        caption = (f"💳 رسید Mini App\n\n🧾 سفارش: #{order_id}\n👤 نام: {first_name}\n🔗 Username: @{username.lstrip('@') if username != '-' else '-'}\n🆔 Telegram ID: {user_id}\n📦 نوع: {volume}\n💰 مبلغ: {price:,} تومان\n🕐 زمان ارسال: {now_text()}")
        field("caption", caption)
        field("reply_markup", InlineKeyboardMarkup([[
            styled_inline_button("✅ تأیید پرداخت", callback_data=f"approve_{order_id}"),
            styled_inline_button("❌ رد پرداخت", callback_data=f"reject_{order_id}"),
        ]]).to_json())
        body.extend((f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"receipt.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n").encode())
        body.extend(raw); body.extend(f"\r\n--{boundary}--\r\n".encode())
        req=urlrequest.Request(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data=bytes(body), headers={"Content-Type":f"multipart/form-data; boundary={boundary}"}, method="POST")
        with urlrequest.urlopen(req, timeout=20) as r: return json.loads(r.read().decode())
    except Exception as e:
        return {"ok":False,"error":str(e)}


class MiniAppHandler(BaseHTTPRequestHandler):
    def _send(self, status, obj):
        data=_json_bytes(obj); self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Access-Control-Allow-Origin","*"); self.send_header("Access-Control-Allow-Headers","Content-Type, X-Telegram-Init-Data"); self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS"); self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_OPTIONS(self): self._send(200,{"ok":True})
    def _user(self): return _api_user(self.headers.get("X-Telegram-Init-Data", ""))
    def do_GET(self):
        if self.path=="/health": return self._send(200,{"ok":True})
        u=self._user()
        if not u: return self._send(401,{"ok":False,"error":"unauthorized"})
        if self.path.startswith("/api/services"):
            rows=get_user_services(u.id); return self._send(200,{"ok":True,"services":[dict(r) for r in rows]})
        if self.path.startswith("/api/wallet"):
            return self._send(200,{"ok":True,"balance":get_balance(u.id)})
        if self.path.startswith("/api/bootstrap"):
            rows=get_user_services(u.id)
            plans=[{"volume":v,"price":p,"available":bool(get_stock().get(v,0))} for v,p in TARIFF_PLANS.items()] + [
                {"volume":k,"price":int(v["price"]),"available":bool(get_stock().get(k,0)),"kind":"unlimited","label_fa":v["label_fa"],"label_en":v["label_en"],"label_ku":v["label_ku"]}
                for k,v in UNLIMITED_PLANS.items()
            ]
            conn=get_db()
            try:
                tx=conn.execute("SELECT amount, type, description, created_at FROM wallet_transactions WHERE user_id=? ORDER BY id DESC LIMIT 20", (u.id,)).fetchall()
            finally:
                conn.close()
            return self._send(200,{"ok":True,"user":{"id":u.id,"username":u.username,"first_name":u.first_name},"language":get_user_language(u.id) or "fa","balance":get_balance(u.id),"plans":plans,"services":[dict(r) for r in rows],"history":[dict(r) for r in tx],"card":CARD_NUMBER,"min_charge":MIN_CHARGE,"service_days":SERVICE_DAYS})
        return self._send(404,{"ok":False,"error":"not_found"})
    def do_POST(self):
        u=self._user()
        if not u: return self._send(401,{"ok":False,"error":"unauthorized"})
        try: payload=json.loads(self.rfile.read(int(self.headers.get("Content-Length","0"))) or b"{}")
        except Exception: return self._send(400,{"ok":False,"error":"bad_json"})
        path=self.path.split("?",1)[0]
        if path in ("/api/buy","/api/renew"):
            if path=="/api/renew":
                oid=int(payload.get("order_id",0) or 0); conn=get_db()
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    order=conn.execute("SELECT id, volume, price, expires_at FROM orders WHERE id=? AND user_id=? AND status='approved' AND is_charge=0",(oid,u.id)).fetchone()
                    if not order: conn.rollback(); return self._send(404,{"ok":False,"error":"service_not_found"})
                    price=plan_price(order["volume"]); bal=conn.execute("SELECT balance FROM users WHERE user_id=?",(u.id,)).fetchone()[0] or 0
                    if bal<price: conn.rollback(); return self._send(200,{"ok":False,"error":"insufficient_balance","balance":bal,"price":price})
                    old=datetime.strptime(order["expires_at"],"%Y-%m-%d %H:%M:%S") if order["expires_at"] else datetime.now(); base=max(old,datetime.now()); newexp=base+timedelta(days=SERVICE_DAYS)
                    conn.execute("UPDATE users SET balance=balance-? WHERE user_id=?",(price,u.id)); conn.execute("INSERT INTO wallet_transactions (user_id,amount,type,description,order_id,created_at) VALUES (?,?,?,?,?,?)",(u.id,-price,"renew",f"تمدید سرویس #{oid}",oid,now_text())); conn.execute("UPDATE orders SET expires_at=? WHERE id=?",(newexp.strftime("%Y-%m-%d %H:%M:%S"),oid)); conn.commit(); return self._send(200,{"ok":True,"order_id":oid,"price":price,"balance":bal-price,"expires_at":newexp.strftime("%Y-%m-%d %H:%M:%S")})
                except Exception as e:
                    conn.rollback(); return self._send(500,{"ok":False,"error":str(e)})
                finally: conn.close()
            raw_volume = str(payload.get("volume", "")).strip()
            volume = raw_volume.upper() if raw_volume.upper() in UNLIMITED_PLANS else _normalize_volume(raw_volume)
            if not volume:
                return self._send(400,{"ok":False,"error":"invalid_volume"})
            price = plan_price(volume)
            # خرید واقعی فقط در تراکنش اتمیک انجام می‌شود؛ موجودی/موجودی سرویس
            # بین pre-check و خرید دیگر نمی‌تواند باعث race condition شود.
            r=_api_purchase_wallet(u,volume,price)
            status=r.get("status")
            if status=="approved":
                return self._send(200,{"ok":True,**r})
            if status=="insufficient_balance":
                return self._send(200,{"ok":False,"error":"insufficient_balance","balance":r.get("balance",0),"price":price,"required":max(price-int(r.get("balance",0)),0)})
            if status=="no_stock":
                return self._send(200,{"ok":False,"error":"no_stock","volume":volume,"balance":r.get("balance",0)})
            print("MiniApp purchase error:", r.get("error","unknown"))
            return self._send(500,{"ok":False,"error":"purchase_failed"})
        if path=="/api/language":
            language=str(payload.get("language", "fa"))
            if language not in LANGUAGES: return self._send(400,{"ok":False,"error":"invalid_language"})
            set_user_language(u.id, language)
            return self._send(200,{"ok":True,"language":language})
        if path=="/api/charge":
            amount=int(payload.get("amount",0))
            if amount<MIN_CHARGE: return self._send(400,{"ok":False,"error":"min_charge","min":MIN_CHARGE})
            oid=create_order(u,"CHARGE",amount,is_charge=1)
            return self._send(200,{"ok":True,"order_id":oid,"amount":amount,"card":CARD_NUMBER})
        if path=="/api/charge-receipt":
            oid=int(payload.get("order_id",0) or 0); amount=int(payload.get("amount",0) or 0); img=payload.get("image","")
            if not oid or not img: return self._send(400,{"ok":False,"error":"invalid_charge_receipt"})
            conn=get_db()
            try:
                order=conn.execute("SELECT id, user_id, price, status, is_charge FROM orders WHERE id=?",(oid,)).fetchone()
                if not order or int(order["user_id"])!=int(u.id) or int(order["is_charge"] or 0)!=1 or order["status"]!="pending":
                    return self._send(404,{"ok":False,"error":"charge_order_not_found"})
                real_amount=int(order["price"] or 0)
                if real_amount<MIN_CHARGE or (amount and amount!=real_amount):
                    return self._send(400,{"ok":False,"error":"invalid_charge_receipt"})
            finally:
                conn.close()
            tg=_telegram_send_photo_base64(u.id,"شارژ کیف پول",real_amount,img,oid)
            return self._send(200 if tg.get("ok") else 500,{"ok":bool(tg.get("ok")),"order_id":oid})
        if path=="/api/buy-receipt":
            raw_volume=str(payload.get("volume", "")).strip()
            volume=raw_volume.upper() if raw_volume.upper() in UNLIMITED_PLANS else _normalize_volume(raw_volume)
            price=plan_price(volume) if volume else 0
            img=payload.get("image","")
            if not volume or price <= 0 or not img: return self._send(400,{"ok":False,"error":"invalid_purchase_receipt"})
            oid=create_order(u,volume,price); tg=_telegram_send_photo_base64(u.id,volume,price,img,oid)
            return self._send(200 if tg.get("ok") else 500,{"ok":bool(tg.get("ok")),"order_id":oid})
        return self._send(404,{"ok":False,"error":"not_found"})


def start_miniapp_api():
    server=ThreadingHTTPServer((API_HOST,API_PORT),MiniAppHandler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    print(f"Mini App API listening on {API_HOST}:{API_PORT}")


# =========================================================
# آیکن پرمیوم دکمه‌ها (فقط ادمین)
# =========================================================

def _custom_emoji_entities(message):
    if not message:
        return []
    ents = list(message.entities or []) + list(message.caption_entities or [])
    return [e for e in ents if e.type == MessageEntity.CUSTOM_EMOJI]


class _AdminOnlyCustomEmoji(filters.MessageFilter):
    """پیام ادمین که فقط شامل ایموجی‌های پرمیوم است (برای گرفتن آیدی ایموجی)."""

    def filter(self, message):
        if not ADMIN_ID or not message.from_user or message.from_user.id != ADMIN_ID:
            return False
        text = message.text or ""
        ents = [e for e in (message.entities or []) if e.type == MessageEntity.CUSTOM_EMOJI]
        if not ents:
            return False
        units = text.encode("utf-16-le")
        covered = bytearray(len(units) // 2)
        for e in ents:
            for i in range(e.offset, min(e.offset + e.length, len(covered))):
                covered[i] = 1
        rest = "".join(units[2 * i:2 * i + 2].decode("utf-16-le", "ignore") for i in range(len(covered)) if not covered[i])
        return rest.strip() == ""


async def emoji_id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ids = [e.custom_emoji_id for e in _custom_emoji_entities(update.message)]
    pack_name = ""
    try:
        stickers = await context.bot.get_custom_emoji_stickers(ids[:1])
        pack_name = (stickers[0].set_name or "") if stickers else ""
    except Exception:
        pass
    lines = ["🆔 آیدی ایموجی‌ها:", ""]
    lines += [f"<code>{i}</code>" for i in ids]
    if pack_name:
        lines += ["", f"📦 پک: <code>{pack_name}</code>", f"برای فعال کردن روی همه دکمه‌ها: <code>/usepack {pack_name}</code>"]
    lines += ["", "برای گذاشتن روی دکمه، روی همین پیام ایموجی ریپلای کنید و بنویسید:", "<code>/seticon buy</code>"]
    await rich_reply_text(update.message, "\n".join(lines), parse_mode="HTML")


async def seticon_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != ADMIN_ID:
        return
    args = context.args or []
    usage = (
        "استفاده:\n"
        "/seticon <key> <emoji_id>\n"
        "یا ریپلای روی پیامی که ایموجی پرمیوم دارد: /seticon <key>\n\n"
        "کلیدهای داشبورد: dash_first ، dash_services ، dash_balance ، dash_new ، dash_back\n"
        "کلیدهای منو: buy ، trial ، wallet ، home ، pay_* ، approve_* ...\n"
        "چند آیکن یکجا: /seticons\n"
        "لیست: /icons    حذف: /delicon <key>"
    )
    if not args:
        await rich_reply_text(update.message, usage)
        return
    key = args[0]
    emoji_id = args[1] if len(args) > 1 else None
    if not emoji_id and update.message.reply_to_message:
        found = _custom_emoji_entities(update.message.reply_to_message)
        if found:
            emoji_id = found[0].custom_emoji_id
    if not emoji_id or not str(emoji_id).isdigit():
        await rich_reply_text(update.message, usage)
        return
    set_button_icon(key, emoji_id)
    await rich_reply_text(update.message, f"✅ آیکن دکمه «{key}» تنظیم شد.")


async def seticons_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ریپلای روی پیامی که چند ایموجی پرمیوم دارد: /seticons dash_first dash_balance dash_new"""
    if not update.effective_user or update.effective_user.id != ADMIN_ID:
        return
    keys = context.args or []
    found = _custom_emoji_entities(update.message.reply_to_message)
    if not keys or not found:
        await rich_reply_text(update.message, 
            "ریپلای روی پیامی که چند ایموجی پرمیوم دارد، بعد بنویسید:\n"
            "/seticons dash_first dash_balance dash_new\n\n"
            "ایموجی اول به کلید اول، دوم به کلید دوم و ... اختصاص داده می‌شود."
        )
        return
    count = 0
    for key, entity in zip(keys, found):
        set_button_icon(key, entity.custom_emoji_id)
        count += 1
    await rich_reply_text(update.message, f"✅ آیکن {count} دکمه تنظیم شد.")


async def _icon_allowed(update, emoji_id):
    """یک پیام تست با همین آیکن می‌فرستد؛ اگر تلگرام نپذیرد، یعنی اکانت صاحب ربات پرمیوم نیست."""
    try:
        await rich_reply_text(update.message, 
            "🧪 تست آیکن",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("تست آیکن", callback_data="home", icon_custom_emoji_id=str(emoji_id))
            ]]),
        )
        return True, ""
    except Exception as e:
        return False, str(e)


async def usepack_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    فعال‌سازی یک پک ایموجی پرمیوم برای همه دکمه‌ها: هر دکمه‌ای که ایموجی ابتدای متنش
    در پک باشد، خودکار آیکن پرمیوم می‌گیرد.
    /usepack <نام پک یا لینک addemoji>   یا ریپلای روی پیامی که ایموجی پرمیوم آن پک را دارد.
    """
    if not update.effective_user or update.effective_user.id != ADMIN_ID:
        return
    name = (context.args[0] if context.args else "").strip().rstrip("/").split("/")[-1]
    reply = update.message.reply_to_message
    if not name and reply:
        found = _custom_emoji_entities(reply)
        if found:
            try:
                stickers = await context.bot.get_custom_emoji_stickers([found[0].custom_emoji_id])
                name = (stickers[0].set_name or "") if stickers else ""
            except Exception:
                name = ""
    if not name:
        await rich_reply_text(update.message, 
            "استفاده:\n/usepack <نام پک>\n\n"
            "یا پیام رباتی که آیکن‌هایش را می‌خواهید را برای ربات خودتان فوروارد کنید، "
            "روی آن ریپلای کنید و بنویسید /usepack\n\n"
            "غیرفعال کردن: /nopack"
        )
        return
    try:
        sticker_set = await context.bot.get_sticker_set(name)
    except Exception:
        await rich_reply_text(update.message, "❌ پکی با این نام پیدا نشد.")
        return
    mapping = {}
    for st in sticker_set.stickers:
        if getattr(st, "custom_emoji_id", None) and st.emoji:
            mapping.setdefault(_norm_emoji(st.emoji), st.custom_emoji_id)
    if not mapping:
        await rich_reply_text(update.message, "❌ این پک، پک ایموجی پرمیوم (custom emoji) نیست.")
        return
    ok, err = await _icon_allowed(update, next(iter(mapping.values())))
    if not ok:
        await rich_reply_text(update.message, 
            "❌ تلگرام آیکن روی دکمه را قبول نکرد، پک فعال نشد.\n"
            "آیکن دکمه فقط وقتی کار می‌کند که صاحب ربات تلگرام پرمیوم داشته باشد.\n\n" + err[:200]
        )
        return
    set_icon_pack(name, mapping)
    keys = ["buy", "trial", "services", "renew", "coupon", "referral", "support", "wallet", "language",
            "admin", "back", "main_menu", "custom", "charge_wallet", "wallet_history",
            "dash_first_service", "dash_balance", "dash_new_service"]
    missing = []
    for key in keys:
        head = t("fa", key).partition(" ")[0]
        if head and not any(ch.isalnum() for ch in head) and _norm_emoji(head) not in mapping and head not in missing:
            missing.append(head)
    msg = f"✅ پک «{name}» فعال شد ({len(mapping)} ایموجی)."
    if missing:
        msg += "\n\nاین ایموجی‌ها در پک نبودند و همان ایموجی معمولی می‌مانند: " + " ".join(missing)
    await rich_reply_text(update.message, msg)


async def nopack_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != ADMIN_ID:
        return
    clear_icon_pack()
    await rich_reply_text(update.message, "🗑 پک ایموجی غیرفعال شد؛ دکمه‌ها به ایموجی معمولی برگشتند.")


async def delicon_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await rich_reply_text(update.message, "استفاده: /delicon <key>")
        return
    set_button_icon(context.args[0], None)
    await rich_reply_text(update.message, f"🗑 آیکن دکمه «{context.args[0]}» حذف شد.")


async def icons_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != ADMIN_ID:
        return
    icons = get_button_icon_map()
    pack = get_icon_pack()
    lines = []
    if pack["set"]:
        lines.append(f"📦 پک فعال: {pack['set']} ({len(pack['map'])} ایموجی)")
    lines += [f"{k} → {v}" for k, v in sorted(icons.items())]
    if not lines:
        await rich_reply_text(update.message, "هنوز آیکنی تنظیم نشده.\n\nبا /usepack یک پک ایموجی پرمیوم فعال کنید.")
        return
    await rich_reply_text(update.message, "🎨 آیکن دکمه‌ها:\n\n" + "\n".join(lines))


# =========================================================
# اجرای ربات
# =========================================================

async def post_init(application):
    await set_bot_commands(application)
    try:
        await application.bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="🛒 HanzuVPN",
                web_app=WebAppInfo(url=MINI_APP_URL + "?v=20261002-manual-unlimited"),
            )
        )
    except Exception as e:
        print("Mini App menu button setup error:", e)
    asyncio.create_task(expiration_checker(application))


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN تنظیم نشده است.")
    init_db()
    start_miniapp_api()
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("backup", backup_command))
    app.add_handler(CommandHandler("panel", panel_command))
    app.add_handler(CommandHandler("buy", buy_command))
    app.add_handler(CommandHandler("services", services_command))
    app.add_handler(CommandHandler("trial", trial_command))
    app.add_handler(CommandHandler("support", support_command))
    app.add_handler(CommandHandler("language", language_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("rich_test", rich_test_command))
    app.add_handler(CommandHandler("seticon", seticon_command))
    app.add_handler(CommandHandler("seticons", seticons_command))
    app.add_handler(CommandHandler("usepack", usepack_command))
    app.add_handler(CommandHandler("nopack", nopack_command))
    app.add_handler(CommandHandler("delicon", delicon_command))
    app.add_handler(CommandHandler("icons", icons_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, receipt_handler))
    app.add_handler(MessageHandler(_AdminOnlyCustomEmoji(), emoji_id_handler))
    app.add_handler(MessageHandler(filters.TEXT, text_handler))

    print("HanzuVPN Bot is running...")
    app.run_polling()


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stable callback entry point for every inline keyboard button."""
    try:
        await _button_handler_impl(update, context)
    except Exception as e:
        print(f"Callback handler error: {type(e).__name__}: {e}")
        q = getattr(update, "callback_query", None)
        if q:
            try:
                await q.answer("❌ خطایی رخ داد. دوباره تلاش کنید.", show_alert=True)
            except Exception:
                pass


if __name__ == "__main__":
    main()