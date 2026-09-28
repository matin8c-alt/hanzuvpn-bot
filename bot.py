import os
import sqlite3
import asyncio
import json
import base64
import hashlib
import hmac
import threading
from urllib.parse import parse_qsl, unquote
from urllib import request as urlrequest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timedelta

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    BotCommand,
    MenuButtonWebApp,
    WebAppInfo,
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
        "welcome": "🌐 HanzuVPN\n\nبه ربات HanzuVPN خوش آمدید ❤️\n\nاز منوی زیر انتخاب کنید:",
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
        "wallet": "💰 کیف پول",
        "buy_title": "🛒 انتخاب سرویس\n\n⏳ مدت تمام سرویس‌ها: 30 روز\n\nحجم موردنظر خود را انتخاب کنید:",
        "custom": "✏️ حجم دلخواه",
        "trial_already": "⚠️ شما قبلاً تست رایگان خود را دریافت کرده‌اید.\n\nهر کاربر فقط یک‌بار می‌تواند از تست رایگان استفاده کند.",
        "trial_empty": "😔 در حال حاضر تست رایگان موجود نیست.\n\nلطفاً بعداً دوباره امتحان کنید.",
        "trial_success": "🎁 تست رایگان HanzuVPN\n\n📦 حجم: 100 مگابایت\n⏳ مدت: 1 روز\n\n🔗 لینک Subscription:\n\n{link}\n\n📌 لینک را در برنامه VPN خود وارد کنید.",
        "payment": "💳 اطلاعات پرداخت\n\n📦 حجم: {volume} گیگ\n💰 مبلغ: {price:,} تومان\n⏳ مدت: 30 روز\n",
        "original_price": "\n🏷 مبلغ اصلی: {original:,} تومان\n🎟 کد تخفیف: {coupon}\n",
        "card": "\n💳 شماره کارت:\n`{card}`\n\nبعد از انتقال مبلغ، روی «پرداخت کردم» بزنید و سپس تصویر رسید را ارسال کنید.",
        "paid": "💳 پرداخت کردم",
        "pay_wallet": "💰 پرداخت از کیف پول",
        "order_created": "✅ درخواست شما ثبت شد.\n\n🧾 سفارش: #{order}\n📦 حجم: {volume} گیگ\n💰 مبلغ: {price:,} تومان\n\n📸 حالا تصویر رسید را ارسال کنید.",
        "receipt_received": "✅ رسید شما دریافت شد.\n\n🧾 سفارش #{order}\n\nپس از بررسی توسط مدیریت، نتیجه برای شما ارسال می‌شود.",
        "no_pending": "❌ سفارش در انتظار پرداختی پیدا نشد.",
        "services_title": "📦 سرویس‌های شما\n\n",
        "no_services": "📦 سرویس‌های شما\n\nهنوز سرویس فعالی ندارید.",
        "service_item": "🧾 سفارش #{id}\n📦 حجم: {volume} گیگ\n⏳ انقضا: {expires}\n\n🔗 لینک:\n{link}\n\n━━━━━━━━━━━━\n\n",
        "renew_no_services": "🔄 تمدید سرویس\n\nشما سرویس فعالی ندارید.",
        "renew_choose": "🔄 تمدید سرویس\n\nسرویسی که می‌خواهید تمدید کنید را انتخاب کنید:",
        "renew_payment": "🔄 تمدید سرویس\n\n📦 حجم: {volume} گیگ\n💰 مبلغ تمدید: {price:,} تومان\n⏳ مدت: 30 روز\n\nبرای پرداخت روی دکمه زیر بزنید.",
        "renew_paid": "💳 پرداخت تمدید\n\n📦 حجم: {volume} گیگ\n💰 مبلغ: {price:,} تومان\n⏳ مدت: 30 روز\n\n💳 شماره کارت:\n`{card}`\n\nبعد از پرداخت روی دکمه زیر بزنید.",
        "renew_created": "✅ درخواست تمدید ثبت شد.\n\n🧾 سفارش: #{order}\n📦 حجم: {volume} گیگ\n💰 مبلغ: {price:,} تومان\n\n📸 حالا تصویر رسید را ارسال کنید.",
        "custom_prompt": "✏️ حجم دلخواه\n\nحجم موردنظر را به گیگ وارد کن.\n\nمثال:\n25",
        "invalid_volume": "❌ حجم نامعتبر است.\n\nمثلاً 25 وارد کن.",
        "custom_summary": "🛒 سرویس دلخواه\n\n📦 حجم: {volume} گیگ\n💰 قیمت: {price:,} تومان\n⏳ مدت: 30 روز",
        "support_title": "🎫 پشتیبانی HanzuVPN\n\nبرای ارسال پیام به پشتیبانی تیکت ایجاد کنید.",
        "create_ticket": "🎫 ایجاد تیکت",
        "ticket_prompt": "🎫 تیکت #{id}\n\nپیام خود را ارسال کنید.",
        "ticket_created": "✅ پیام شما در تیکت #{id} ثبت شد.\n\nپشتیبانی آن را بررسی می‌کند.",
        "ticket_closed": "🔒 تیکت #{id} بسته شد.\n\nدر صورت نیاز می‌توانید تیکت جدید ایجاد کنید.",
        "referral_title": "👥 دعوت دوستان\n\n👤 تعداد دعوت‌ها: {count}\n\nلینک اختصاصی شما:\n{link}\n\nلینک را برای دوستانت بفرست.",
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
        "wallet_title": "💰 کیف پول شما\n\n💵 موجودی فعلی: {balance:,} تومان",
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
    },
    "ku": {
        "language_title": "🌐 هەڵبژاردنی زمان\n\nتکایە زمانی خۆت هەڵبژێرە:",
        "language_changed": "✅ زمان بە سەرکەوتوویی گۆڕدرا.",
        "welcome": "🌐 HanzuVPN\n\nبەخێربێیت بۆ HanzuVPN ❤️\n\nلە خوارەوە هەڵبژاردەیەک هەڵبژێرە:",
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
        "pay_wallet": "💰 پارەدان لە جزدان",
        "order_created": "✅ داواکاری تۆمار کرا.\n\n🧾 #{order}\n📦 {volume} گیگ\n💰 {price:,} تومان\n\n📸 وێنەی پسوڵە بنێرە.",
        "receipt_received": "✅ پسوڵە وەرگیرا.\n\n🧾 #{order}",
        "no_pending": "❌ هیچ داواکارییەکی چاوەڕوان نەدۆزرایەوە.",
        "services_title": "📦 خزمەتگوزارییەکانت\n\n",
        "no_services": "📦 هیچ خزمەتگوزارییەکی چالاکت نییە.",
        "service_item": "🧾 #{id}\n📦 {volume} گیگ\n⏳ {expires}\n\n🔗 {link}\n\n━━━━━━━━━━━━\n\n",
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
    },
    "en": {
        "language_title": "🌐 Choose Language\n\nPlease select your language:",
        "language_changed": "✅ Language changed successfully.",
        "welcome": "🌐 HanzuVPN\n\nWelcome to HanzuVPN ❤️\n\nChoose an option below:",
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
        "pay_wallet": "💰 Pay from Wallet",
        "order_created": "✅ Request registered.\n\n🧾 Order: #{order}\n📦 {volume} GB\n💰 {price:,} Toman\n\n📸 Send the receipt.",
        "receipt_received": "✅ Receipt received.\n\n🧾 Order #{order}",
        "no_pending": "❌ No pending order found.",
        "services_title": "📦 Your Services\n\n",
        "no_services": "📦 You don't have any active services.",
        "service_item": "🧾 Order #{id}\n📦 {volume} GB\n⏳ {expires}\n\n🔗 {link}\n\n━━━━━━━━━━━━\n\n",
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
    }
}


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
        (user_id, username, first_name, created_at, language, balance)
        VALUES (?, ?, ?, ?, NULL, 0)
    """, (user.id, user.username or "", user.first_name or "", now_text()))
    conn.execute("""
        UPDATE users SET username = ?, first_name = ? WHERE user_id = ?
    """, (user.username or "", user.first_name or "", user.id))
    conn.commit()
    conn.close()


def get_user_language(user_id):
    if user_id == ADMIN_ID:
        return "fa"
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
        [InlineKeyboardButton("🇮🇷 فارسی", callback_data="language_fa")],
        [InlineKeyboardButton("🟢 کوردی", callback_data="language_ku")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="language_en")],
    ])


async def show_language_selector_message(message):
    await message.reply_text(TEXTS["fa"]["language_title"], reply_markup=language_keyboard())


def clear_user_states(context):
    keys = [
        "waiting_custom_volume", "waiting_coupon", "waiting_ticket_message",
        "ticket_id", "custom_volume", "custom_price", "coupon_code",
        "renew_order_id", "renew_volume", "renew_price",
        "admin_waiting_volume", "admin_waiting_link", "admin_add_volume",
        "admin_waiting_trial_link", "admin_waiting_coupon", "admin_broadcast",
        "admin_ticket_id", "admin_waiting_ticket_reply", "last_order_id",
        "waiting_charge_amount", "charge_amount", "admin_waiting_balance_user",
        "admin_balance_user_id", "admin_waiting_balance_amount"
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
            is_charge INTEGER DEFAULT 0
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

    conn.commit()

    # سازگاری
    for col, default in [
        ("expires_at", "TEXT"),
        ("is_charge", "INTEGER DEFAULT 0"),
        ("subscription_id", "INTEGER"),
        ("approved_at", "TEXT"),
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

def bottom_keyboard(user_id):
    lang = get_user_language(user_id) or "fa"
    if lang == "en":
        rows = [
            ["🏠 Home", "🛒 Buy Service"],
            ["📦 My Services", "💰 Wallet"],
            ["🎁 Free Trial", "🎫 Support"],
            ["🌐 Change Language"],
        ]
    elif lang == "ku":
        rows = [
            ["🏠 سەرەکی", "🛒 کڕینی خزمەتگوزاری"],
            ["📦 خزمەتگوزارییەکانم", "💰 جزدان"],
            ["🎁 تاقیکردنەوەی بەخۆڕایی", "🎫 پشتگیری"],
            ["🌐 گۆڕینی زمان"],
        ]
    else:
        rows = [
            ["🏠 خانه", "🛒 خرید سرویس"],
            ["📦 سرویس‌های من", "💰 کیف پول"],
            ["🎁 تست رایگان", "🎫 پشتیبانی"],
            ["🌐 تغییر زبان"],
        ]
    return ReplyKeyboardMarkup([[KeyboardButton(x) for x in row] for row in rows], resize_keyboard=True)


def home_keyboard(user_id):
    lang = get_user_language(user_id) or "fa"
    keyboard = [
        [InlineKeyboardButton(t(lang, "buy"), callback_data="buy")],
        [InlineKeyboardButton(t(lang, "trial"), callback_data="trial")],
        [
            InlineKeyboardButton(t(lang, "services"), callback_data="my_services"),
            InlineKeyboardButton(t(lang, "renew"), callback_data="renew"),
        ],
        [
            InlineKeyboardButton(t(lang, "coupon"), callback_data="coupon"),
            InlineKeyboardButton(t(lang, "referral"), callback_data="referral"),
        ],
        [InlineKeyboardButton(t(lang, "wallet"), callback_data="wallet")],
        [InlineKeyboardButton(t(lang, "support"), callback_data="support")],
        [InlineKeyboardButton(t(lang, "language"), callback_data="language")],
    ]
    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton(t("fa", "admin"), callback_data="admin")])
    return InlineKeyboardMarkup(keyboard)


async def show_home(query, user_id):
    lang = get_user_language(user_id) or "fa"
    await query.edit_message_text(t(lang, "welcome"), reply_markup=home_keyboard(user_id))


async def send_home(message, user_id):
    lang = get_user_language(user_id) or "fa"
    await message.reply_text(t(lang, "welcome"), reply_markup=home_keyboard(user_id))
    await message.reply_text("منوی پایین:", reply_markup=bottom_keyboard(user_id))


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

    if user.id == ADMIN_ID:
        set_user_language(user.id, "fa")

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
        await update.message.reply_text(t(lang, "trial_already"))
        return
    if result["status"] == "empty":
        await update.message.reply_text(t(lang, "trial_empty"))
        return
    await update.message.reply_text(t(lang, "trial_success", link=result["link"]))


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
            [InlineKeyboardButton(t(lang, "create_ticket"), callback_data="new_ticket")],
            [InlineKeyboardButton(t(lang, "main_menu"), callback_data="home")],
        ])
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user(user)
    lang = get_user_language(user.id)
    if not lang:
        await show_language_selector_message(update.message)
        return
    await update.message.reply_text(t(lang, "help"))


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user(user)
    await show_language_selector_message(update.message)


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
            ("1 GB | 3,500 Toman", "plan_1"),
            ("10 GB | 35,000 Toman", "plan_10"),
            ("15 GB | 52,500 Toman", "plan_15"),
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
            ("15 گیگ | 52,500 تومان", "plan_15"),
            ("20 گیگ | 70,000 تومان", "plan_20"),
            ("30 گیگ | 105,000 تومان", "plan_30"),
            ("40 گیگ | 140,000 تومان", "plan_40"),
            ("50 گیگ | 175,000 تومان", "plan_50"),
            ("100 گیگ | 350,000 تومان", "plan_100"),
        ]
    keyboard = [[InlineKeyboardButton(text, callback_data=cb)] for text, cb in buttons]
    keyboard.append([InlineKeyboardButton(t(lang, "custom"), callback_data="custom")])
    keyboard.append([InlineKeyboardButton(t(lang, "back"), callback_data="home")])
    return InlineKeyboardMarkup(keyboard)


async def send_buy_message(message):
    user_id = message.from_user.id
    lang = get_user_language(user_id) or "fa"
    await message.reply_text(t(lang, "buy_title"), reply_markup=buy_keyboard(user_id))


async def show_buy_menu(query):
    lang = get_user_language(query.from_user.id) or "fa"
    await query.edit_message_text(t(lang, "buy_title"), reply_markup=buy_keyboard(query.from_user.id))


# =========================================================
# پرداخت
# =========================================================

async def show_payment(query, volume, price, original_price=None, coupon_code=None):
    user_id = query.from_user.id
    lang = get_user_language(user_id) or "fa"
    if original_price is None:
        original_price = price

    caption = t(lang, "payment", volume=volume, price=price)
    if original_price != price and coupon_code:
        caption += t(lang, "original_price", original=original_price, coupon=coupon_code)
    caption += t(lang, "card", card=CARD_NUMBER)

    keyboard = [
        [InlineKeyboardButton(t(lang, "paid"), callback_data=f"paid_{volume}")]
    ]

    # دکمه پرداخت از کیف پول
    balance = get_balance(user_id)
    if balance >= price:
        keyboard.insert(0, [InlineKeyboardButton(t(lang, "pay_wallet"), callback_data=f"walletpay_{volume}_{price}")])

    keyboard.append([InlineKeyboardButton(t(lang, "back"), callback_data="buy")])

    await query.edit_message_text(
        caption,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


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

        normalized_order_volume = _normalize_volume(order["volume"])
        if not normalized_order_volume:
            conn.rollback()
            return {"status": "invalid_volume", "order": order}
        subscription = conn.execute(
            "SELECT id, link FROM subscriptions WHERE CAST(TRIM(REPLACE(REPLACE(LOWER(volume), 'gb', ''), 'گیگ', '')) AS INTEGER) = ? AND used = 0 ORDER BY id LIMIT 1",
            (int(normalized_order_volume),)
        ).fetchone()
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
        SELECT o.id, o.volume, o.price, o.approved_at, o.expires_at, s.link
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
            text += t(lang, "service_item", id=row["id"], volume=row["volume"], expires=row["expires_at"] or "-", link=row["link"] or "-")
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton(t(lang, "renew"), callback_data="renew")],
        [InlineKeyboardButton(t(lang, "main_menu"), callback_data="home")],
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
# پنل مدیریت + کیف پول ادمین
# =========================================================

async def show_admin(query):
    keyboard = [
        [InlineKeyboardButton("➕ افزودن لینک سرویس", callback_data="admin_add")],
        [InlineKeyboardButton("🎁 مدیریت تست", callback_data="admin_trial")],
        [
            InlineKeyboardButton("📦 موجودی", callback_data="admin_stock"),
            InlineKeyboardButton("🗑 حذف لینک", callback_data="admin_delete")
        ],
        [InlineKeyboardButton("🎟 کوپن‌ها", callback_data="admin_coupon")],
        [InlineKeyboardButton("💰 مدیریت موجودی کاربر", callback_data="admin_balance")],
        [InlineKeyboardButton("📢 پیام همگانی", callback_data="admin_broadcast")],
        [
            InlineKeyboardButton("📊 آمار", callback_data="admin_stats"),
            InlineKeyboardButton("🧾 سفارش‌ها", callback_data="admin_orders")
        ],
        [InlineKeyboardButton("🎫 تیکت‌ها", callback_data="admin_tickets")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="home")],
    ]
    await query.edit_message_text(
        "⚙️ پنل مدیریت HanzuVPN\n\nمدیریت کامل ربات:",
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
    text += f"\n🎁 تست رایگان:\n🔹 {trial_stock} عدد\n"
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 پنل مدیریت", callback_data="admin")]
    ]))


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
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 پنل مدیریت", callback_data="admin")]
    ]))


async def show_admin_orders(query):
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
            username = f"@{row['username']}" if row['username'] else "ندارد"
            text += (
                f"🧾 سفارش #{row['id']}" + (" • شارژ کیف پول" if row['is_charge'] else "") + "\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"👤 نام: {row['first_name'] or '-'}\n"
                f"🔹 Username: {username}\n"
                f"🆔 آیدی: {row['user_id']}\n"
                f"📦 حجم: {row['volume']}\n"
                f"💰 مبلغ: {row['price']:,} تومان\n"
                f"📌 وضعیت: {status}\n"
                f"🕐 زمان: {row['created_at']}\n\n"
            )
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 پنل مدیریت", callback_data="admin")]
    ]))


async def show_admin_trial(query):
    stock = get_free_trial_stock()
    keyboard = [
        [InlineKeyboardButton("➕ افزودن لینک تست", callback_data="admin_trial_add")],
        [InlineKeyboardButton("🗑 حذف لینک تست", callback_data="admin_trial_delete")],
        [InlineKeyboardButton("📦 موجودی تست", callback_data="admin_trial_stock")],
        [InlineKeyboardButton("🔙 پنل مدیریت", callback_data="admin")],
    ]
    await query.edit_message_text(
        f"🎁 مدیریت تست رایگان\n\n📦 حجم: 100 مگابایت\n⏳ مدت: 1 روز\n📊 موجودی: {stock}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_admin_trial_delete(query):
    rows = get_free_trial_list()
    if not rows:
        await query.edit_message_text(
            "🗑 حذف تست\n\n❌ لینک تستی وجود ندارد.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 مدیریت تست", callback_data="admin_trial")]])
        )
        return
    keyboard = [[InlineKeyboardButton(f"🗑 تست #{row['id']}", callback_data=f"trial_delete_{row['id']}")] for row in rows]
    keyboard.append([InlineKeyboardButton("🔙 مدیریت تست", callback_data="admin_trial")])
    await query.edit_message_text("🗑 لینک تست موردنظر را انتخاب کن:", reply_markup=InlineKeyboardMarkup(keyboard))


async def show_delete_menu(query):
    rows = get_subscription_list()
    if not rows:
        await query.edit_message_text(
            "🗑 حذف لینک\n\n❌ لینک استفاده‌نشده‌ای وجود ندارد.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 پنل مدیریت", callback_data="admin")]])
        )
        return
    keyboard = [[InlineKeyboardButton(f"🗑 #{row['id']} | {row['volume']} گیگ", callback_data=f"delete_{row['id']}")] for row in rows]
    keyboard.append([InlineKeyboardButton("🔙 پنل مدیریت", callback_data="admin")])
    await query.edit_message_text("🗑 کدام لینک حذف شود؟", reply_markup=InlineKeyboardMarkup(keyboard))


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

    # زبان
    if data == "language":
        await query.edit_message_text(TEXTS["fa"]["language_title"], reply_markup=language_keyboard())
        return

    if data.startswith("language_"):
        language = data.split("_", 1)[1]
        if language not in LANGUAGES:
            await query.answer("زبان نامعتبر است.", show_alert=True)
            return
        set_user_language(user_id, language)
        clear_user_states(context)
        await query.edit_message_text(
            t(language, "language_changed") + "\n\n" + t(language, "welcome"),
            reply_markup=home_keyboard(user_id)
        )
        return

    lang = get_user_language(user_id)
    if not lang and user_id != ADMIN_ID:
        await query.edit_message_text(TEXTS["fa"]["language_title"], reply_markup=language_keyboard())
        return
    if user_id == ADMIN_ID:
        lang = "fa"

    # خانه
    if data == "home":
        clear_user_states(context)
        await show_home(query, user_id)
        return

    # کیف پول کاربر
    if data == "wallet":
        balance = get_balance(user_id)
        await query.edit_message_text(
            t(lang, "wallet_title", balance=balance),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(t(lang, "charge_wallet"), callback_data="charge_wallet")],
                [InlineKeyboardButton(t(lang, "wallet_history"), callback_data="wallet_history")],
                [InlineKeyboardButton(t(lang, "back"), callback_data="home")],
            ])
        )
        return

    if data == "charge_wallet":
        context.user_data["waiting_charge_amount"] = True
        await query.edit_message_text(t(lang, "charge_prompt", min=MIN_CHARGE))
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
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(t(lang, "back"), callback_data="wallet")]
        ]))
        return

    # خرید
    if data == "buy":
        clear_user_states(context)
        await show_buy_menu(query)
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

    # پرداخت عادی
   # =====================================================
    # پرداخت (خرید سرویس + شارژ کیف پول)
    # =====================================================
    if data.startswith("paid_"):
        parts = data.split("_")
        if len(parts) < 2:
            await query.answer("داده نامعتبر", show_alert=True)
            return

        volume = parts[1]

        # ---------- حالت شارژ کیف پول ----------
        if volume == "CHARGE":
            order_id = context.user_data.get("last_order_id")
            amount = context.user_data.get("charge_amount")

            if not order_id or not amount:
                await query.answer("سفارش شارژ پیدا نشد. دوباره تلاش کنید.", show_alert=True)
                return

            await query.edit_message_text(
                t(lang, "charge_created", order=order_id, amount=amount)
            )
            return

        # ---------- حالت خرید سرویس ----------
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

        # اعمال کوپن (اگر وجود داشته باشد)
        coupon_code = context.user_data.get("coupon_code")
        price = base_price

        if coupon_code:
            result = apply_coupon(coupon_code, user_id, base_price)
            if result["status"] == "success":
                price = result["price"]
            else:
                coupon_code = None
                context.user_data.pop("coupon_code", None)

        # ساخت سفارش
        order_id = create_order(user, volume, price, coupon_code)

        # پاک کردن stateها
        context.user_data.pop("coupon_code", None)
        context.user_data.pop("custom_volume", None)
        context.user_data.pop("custom_price", None)
        context.user_data["last_order_id"] = order_id

        await query.edit_message_text(
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

        await query.edit_message_text(t(lang, "order_created", order=order_id, volume=volume, price=price))
        return

    # پرداخت از کیف پول
    if data.startswith("walletpay_"):
        parts = data.split("_")
        if len(parts) < 3:
            return
        volume = parts[1]
        try:
            price = int(parts[2])
        except ValueError:
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
        result = approve_order(order_id)

        if result["status"] == "approved":
            await query.edit_message_text(
                t(lang, "paid_from_wallet", price=price, balance=get_balance(user_id)) +
                "\n\n" +
                t(lang, "payment_confirmed",
                  volume=volume,
                  expires=result["expires_at"],
                  order=order_id,
                  link=result["link"])
            )
        elif result["status"] == "no_stock":
            # برگشت پول
            change_balance(user_id, price, "refund", f"برگشت وجه به دلیل نبود موجودی - سفارش #{order_id}")
            await query.edit_message_text("❌ موجودی سرویس کافی نیست. مبلغ به کیف پول برگردانده شد.")
        else:
            change_balance(user_id, price, "refund", f"برگشت وجه - سفارش #{order_id}")
            await query.edit_message_text("❌ خطا در تحویل سرویس. مبلغ به کیف پول برگردانده شد.")
        return

    # حجم دلخواه
    if data == "custom":
        context.user_data["waiting_custom_volume"] = True
        await query.edit_message_text(t(lang, "custom_prompt"))
        return

    # تست
    if data == "trial":
        result = claim_trial(user)
        if result["status"] == "already":
            await query.edit_message_text(t(lang, "trial_already"), reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(t(lang, "buy"), callback_data="buy")],
                [InlineKeyboardButton(t(lang, "back"), callback_data="home")],
            ]))
            return
        if result["status"] == "empty":
            await query.edit_message_text(t(lang, "trial_empty"), reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(t(lang, "back"), callback_data="home")]
            ]))
            return
        await query.edit_message_text(t(lang, "trial_success", link=result["link"]), reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(t(lang, "buy"), callback_data="buy")],
            [InlineKeyboardButton(t(lang, "main_menu"), callback_data="home")],
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
                text += t(lang, "service_item", id=row["id"], volume=row["volume"],
                          expires=row["expires_at"] or "-", link=row["link"] or "-")
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(t(lang, "renew"), callback_data="renew")],
            [InlineKeyboardButton(t(lang, "back"), callback_data="home")],
        ]))
        return

    # تمدید
    if data == "renew":
        rows = get_user_services(user_id)
        if not rows:
            await query.edit_message_text(t(lang, "renew_no_services"), reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(t(lang, "buy"), callback_data="buy")],
                [InlineKeyboardButton(t(lang, "back"), callback_data="home")],
            ]))
            return
        keyboard = []
        for row in rows[:10]:
            label = f"🔄 تمدید #{row['id']} | {row['volume']} گیگ"
            keyboard.append([InlineKeyboardButton(label, callback_data=f"renew_{row['id']}")])
        keyboard.append([InlineKeyboardButton(t(lang, "back"), callback_data="home")])
        await query.edit_message_text(t(lang, "renew_choose"), reply_markup=InlineKeyboardMarkup(keyboard))
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
        volume = order["volume"]
        try:
            price = int(float(volume)) * PRICE_PER_GB
        except:
            await query.answer("حجم نامعتبر است.", show_alert=True)
            return
        context.user_data["renew_volume"] = volume
        context.user_data["renew_price"] = price
        await query.edit_message_text(
            t(lang, "renew_payment", volume=volume, price=price),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(t(lang, "paid"), callback_data=f"renewpay_{volume}")],
                [InlineKeyboardButton(t(lang, "back"), callback_data="renew")],
            ])
        )
        return

    if data.startswith("renewpay_"):
        volume = data.split("_")[1]
        stored_volume = context.user_data.get("renew_volume")
        stored_price = context.user_data.get("renew_price")
        if not stored_volume or str(stored_volume) != str(volume) or not stored_price:
            await query.answer("سفارش نامعتبر است.", show_alert=True)
            return
        await query.edit_message_text(
            t(lang, "renew_paid", volume=volume, price=stored_price, card=CARD_NUMBER),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(t(lang, "paid"), callback_data=f"renewpaid_{volume}")],
                [InlineKeyboardButton(t(lang, "back"), callback_data="renew")],
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
        order_id = create_order(user, volume, stored_price)
        context.user_data.pop("renew_volume", None)
        context.user_data.pop("renew_price", None)
        await query.edit_message_text(t(lang, "renew_created", order=order_id, volume=volume, price=stored_price))
        return

    # پشتیبانی
    if data == "support":
        await query.edit_message_text(t(lang, "support_title"), reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(t(lang, "create_ticket"), callback_data="new_ticket")],
            [InlineKeyboardButton(t(lang, "back"), callback_data="home")],
        ]))
        return

    if data == "new_ticket":
        ticket_id = create_ticket(user_id)
        context.user_data["ticket_id"] = ticket_id
        context.user_data["waiting_ticket_message"] = True
        await query.edit_message_text(t(lang, "ticket_prompt", id=ticket_id))
        return

    # دعوت
    if data == "referral":
        try:
            bot = await context.bot.get_me()
            link = referral_link(bot.username, user_id)
            count = referral_count(user_id)
            await query.edit_message_text(
                t(lang, "referral_title", count=count, link=link),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t(lang, "back"), callback_data="home")]])
            )
        except Exception:
            await query.edit_message_text(t(lang, "referral_error"))
        return

    # کوپن
    if data == "coupon":
        context.user_data["waiting_coupon"] = True
        await query.edit_message_text(t(lang, "coupon_prompt"))
        return

    # ==================== ادمین ====================
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

    if data == "admin_add":
        if user_id != ADMIN_ID:
            return
        context.user_data["admin_waiting_volume"] = True
        await query.edit_message_text("➕ افزودن لینک سرویس\n\nحجم را به گیگ وارد کن:\n\nمثال: 10")
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
        await query.edit_message_text("✅ لینک حذف شد.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 پنل مدیریت", callback_data="admin")]
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
        await query.edit_message_text("➕ افزودن لینک تست\n\nلینک Subscription تست را ارسال کن.")
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
        await query.edit_message_text("✅ لینک تست حذف شد.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 مدیریت تست", callback_data="admin_trial")]
        ]))
        return

    if data == "admin_trial_stock":
        if user_id != ADMIN_ID:
            return
        stock = get_free_trial_stock()
        await query.edit_message_text(
            f"🎁 موجودی تست\n\n📦 100 مگابایت\n⏳ 1 روز\n🔢 موجودی: {stock}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 مدیریت تست", callback_data="admin_trial")]])
        )
        return

    if data == "admin_coupon":
        if user_id != ADMIN_ID:
            return
        context.user_data["admin_waiting_coupon"] = True
        await query.edit_message_text("🎟 ساخت کد تخفیف\n\nفرمت:\nCODE درصد تعداد\n\nمثال:\nHANZU20 20 100")
        return

    if data == "admin_broadcast":
        if user_id != ADMIN_ID:
            return
        context.user_data["admin_broadcast"] = True
        await query.edit_message_text("📢 پیام همگانی\n\nمتن پیام را بفرست.")
        return

    # مدیریت موجودی کاربر توسط ادمین
    if data == "admin_balance":
        if user_id != ADMIN_ID:
            return
        context.user_data["admin_waiting_balance_user"] = True
        await query.edit_message_text("💰 مدیریت موجودی\n\nآی‌دی عددی کاربر را ارسال کن:")
        return

    if data == "admin_tickets":
        if user_id != ADMIN_ID:
            return
        conn = get_db()
        rows = conn.execute("SELECT * FROM tickets WHERE status = 'open' ORDER BY id DESC LIMIT 20").fetchall()
        conn.close()
        if not rows:
            text = "🎫 تیکت باز نداریم."
            keyboard = [[InlineKeyboardButton("🔙 پنل مدیریت", callback_data="admin")]]
        else:
            text = "🎫 تیکت‌های باز\n\n"
            keyboard = []
            for row in rows:
                text += f"#{row['id']} | User: {row['user_id']}\n"
                keyboard.append([InlineKeyboardButton(f"🎫 تیکت #{row['id']}", callback_data=f"ticket_{row['id']}")])
            keyboard.append([InlineKeyboardButton("🔙 پنل مدیریت", callback_data="admin")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
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
        await query.edit_message_text(
            text + "\n✏️ پاسخ خود را ارسال کنید.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔒 بستن تیکت", callback_data=f"close_ticket_{ticket_id}")],
                [InlineKeyboardButton("🔙 تیکت‌ها", callback_data="admin_tickets")],
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
        await query.edit_message_text("✅ تیکت بسته شد.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 پنل مدیریت", callback_data="admin")]
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
        result = approve_order(order_id)
        if result["status"] == "not_found":
            await query.answer("سفارش پیدا نشد.", show_alert=True)
            return
        if result["status"] == "already_processed":
            await query.answer("این سفارش قبلاً پردازش شده.", show_alert=True)
            return
        if result["status"] == "no_stock":
            await query.answer("برای این حجم لینک موجود نیست.", show_alert=True)
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
                await query.edit_message_text(f"✅ شارژ کیف پول #{order_id} تأیید شد.\n💰 {order['price']:,} تومان")
            return

        await context.bot.send_message(
            chat_id=order["user_id"],
            text=t(recipient_lang, "payment_confirmed",
                   volume=order["volume"],
                   expires=result["expires_at"],
                   order=order_id,
                   link=result["link"])
        )
        try:
            await query.edit_message_caption(
                caption=f"✅ سفارش #{order_id} تأیید شد.\n📦 {order['volume']} گیگ\n💰 {order['price']:,} تومان\n📅 {result['expires_at']}"
            )
        except Exception:
            await query.edit_message_text(
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
            await query.edit_message_text(f"❌ سفارش #{order_id} رد شد.\n📦 {order['volume']}\n💰 {order['price']:,} تومان")
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

    # دکمه‌های کیبورد پایین ربات
    bottom_actions = {
        "🏠 خانه": "home", "🏠 Home": "home", "🏠 سەرەکی": "home",
        "🛒 خرید سرویس": "buy", "🛒 Buy Service": "buy", "🛒 کڕینی خزمەتگوزاری": "buy",
        "📦 سرویس‌های من": "my_services", "📦 My Services": "my_services", "📦 خزمەتگوزارییەکانم": "my_services",
        "💰 کیف پول": "wallet", "💰 Wallet": "wallet", "💰 جزدان": "wallet",
        "🎁 تست رایگان": "trial", "🎁 Free Trial": "trial", "🎁 تاقیکردنەوەی بەخۆڕایی": "trial",
        "🎫 پشتیبانی": "support", "🎫 Support": "support", "🎫 پشتگیری": "support",
        "🌐 تغییر زبان": "language", "🌐 Change Language": "language", "🌐 گۆڕینی زمان": "language",
    }
    action = bottom_actions.get(text)
    if action:
        if action == "home":
            clear_user_states(context)
            await send_home(update.message, user.id)
        elif action == "buy":
            await buy_command(update, context)
        elif action == "my_services":
            await services_command(update, context)
        elif action == "wallet":
            balance = get_balance(user.id)
            await update.message.reply_text(t(lang, "wallet_title", balance=balance), reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(t(lang, "charge_wallet"), callback_data="charge_wallet")],
                [InlineKeyboardButton(t(lang, "wallet_history"), callback_data="wallet_history")],
                [InlineKeyboardButton(t(lang, "main_menu"), callback_data="home")],
            ]))
        elif action == "trial":
            await trial_command(update, context)
        elif action == "support":
            await support_command(update, context)
        elif action == "language":
            await language_command(update, context)
        return

    # شارژ کیف پول - دریافت مبلغ
    if context.user_data.get("waiting_charge_amount"):
        context.user_data["waiting_charge_amount"] = False
        try:
            amount = int(text.replace(",", "").replace("،", ""))
            if amount < MIN_CHARGE:
                raise ValueError
        except ValueError:
            await update.message.reply_text(t(lang, "invalid_charge", min=MIN_CHARGE))
            return

        context.user_data["charge_amount"] = amount
        order_id = create_order(user, "CHARGE", amount, is_charge=1)
        context.user_data["last_order_id"] = order_id

        await update.message.reply_text(
            t(lang, "charge_payment", amount=amount, card=CARD_NUMBER),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(t(lang, "paid"), callback_data=f"paid_CHARGE")],
                [InlineKeyboardButton(t(lang, "back"), callback_data="wallet")],
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
                [InlineKeyboardButton("🎫 مشاهده تیکت", callback_data=f"ticket_{ticket_id}")]
            ])
        )
        await update.message.reply_text(t(lang, "ticket_created", id=ticket_id))
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
        await update.message.reply_text("✅ پاسخ برای کاربر ارسال شد.")
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
        await update.message.reply_text(f"📢 ارسال همگانی تمام شد.\n\n✅ موفق: {sent}\n❌ ناموفق: {failed}")
        return

    # ساخت کوپن
    if user.id == ADMIN_ID and context.user_data.get("admin_waiting_coupon"):
        parts = text.split()
        if len(parts) != 3:
            await update.message.reply_text("❌ فرمت اشتباه است.\n\nمثال:\nHANZU20 20 100")
            return
        code = parts[0].upper()
        try:
            percent = int(parts[1])
            max_uses = int(parts[2])
            if percent <= 0 or percent > 100 or max_uses < 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ درصد یا تعداد نامعتبر است.")
            return
        success = create_coupon(code, percent, max_uses)
        if success:
            await update.message.reply_text(f"✅ کد تخفیف ساخته شد.\n\n🎟 {code}\n💰 {percent}%\n🔢 {'نامحدود' if max_uses == 0 else max_uses}")
        else:
            await update.message.reply_text("❌ این کد قبلاً وجود دارد.")
        context.user_data["admin_waiting_coupon"] = False
        return

    # افزودن تست
    if user.id == ADMIN_ID and context.user_data.get("admin_waiting_trial_link"):
        if not (text.startswith("http://") or text.startswith("https://")):
            await update.message.reply_text("❌ لینک معتبر نیست.")
            return
        add_free_trial(text)
        context.user_data["admin_waiting_trial_link"] = False
        await update.message.reply_text("✅ لینک تست اضافه شد.")
        return

    # مدیریت موجودی توسط ادمین - دریافت آی‌دی کاربر
    if user.id == ADMIN_ID and context.user_data.get("admin_waiting_balance_user"):
        try:
            target_id = int(text)
        except ValueError:
            await update.message.reply_text("❌ آی‌دی باید عدد باشد.")
            return
        context.user_data["admin_waiting_balance_user"] = False
        context.user_data["admin_balance_user_id"] = target_id
        context.user_data["admin_waiting_balance_amount"] = True
        balance = get_balance(target_id)
        await update.message.reply_text(
            f"کاربر: {target_id}\nموجودی فعلی: {balance:,} تومان\n\n"
            "مبلغ را وارد کن (مثبت برای افزایش، منفی برای کاهش):\n\nمثال:\n50000\nیا\n-20000"
        )
        return

    # مدیریت موجودی - دریافت مبلغ
    if user.id == ADMIN_ID and context.user_data.get("admin_waiting_balance_amount"):
        try:
            amount = int(text.replace(",", "").replace("،", ""))
        except ValueError:
            await update.message.reply_text("❌ مبلغ نامعتبر است.")
            return
        target_id = context.user_data.get("admin_balance_user_id")
        context.user_data["admin_waiting_balance_amount"] = False
        context.user_data.pop("admin_balance_user_id", None)

        if amount == 0:
            await update.message.reply_text("❌ مبلغ صفر مجاز نیست.")
            return

        type_ = "admin_add" if amount > 0 else "admin_remove"
        desc = "افزایش توسط ادمین" if amount > 0 else "کاهش توسط ادمین"
        success = change_balance(target_id, amount, type_, desc)
        if success:
            new_balance = get_balance(target_id)
            await update.message.reply_text(f"✅ انجام شد.\n\nکاربر: {target_id}\nتغییر: {amount:,}\nموجودی جدید: {new_balance:,}")
            try:
                await context.bot.send_message(
                    chat_id=target_id,
                    text=f"💰 موجودی کیف پول شما توسط مدیریت تغییر کرد.\n\n💵 موجودی جدید: {new_balance:,} تومان"
                )
            except Exception:
                pass
        else:
            await update.message.reply_text("❌ خطا در تغییر موجودی.")
        return

    # حجم دلخواه
    if context.user_data.get("waiting_custom_volume"):
        context.user_data["waiting_custom_volume"] = False
        try:
            volume = int(text)
            if volume <= 0 or volume > 1000:
                raise ValueError
        except ValueError:
            await update.message.reply_text(t(lang, "invalid_volume"))
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

        payment_text = t(lang, "payment", volume=volume, price=final_price)
        if original_price != final_price and coupon_code:
            payment_text += t(lang, "original_price", original=original_price, coupon=coupon_code)
        payment_text += t(lang, "card", card=CARD_NUMBER)

        keyboard = [[InlineKeyboardButton(t(lang, "paid"), callback_data=f"paid_{volume}")]]
        if get_balance(user.id) >= final_price:
            keyboard.insert(0, [InlineKeyboardButton(t(lang, "pay_wallet"), callback_data=f"walletpay_{volume}_{final_price}")])
        keyboard.append([InlineKeyboardButton(t(lang, "back"), callback_data="buy")])

        await update.message.reply_text(
            payment_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # کوپن کاربر
    if context.user_data.get("waiting_coupon"):
        context.user_data["waiting_coupon"] = False
        coupon = get_coupon(text.upper())
        if not coupon:
            await update.message.reply_text(t(lang, "coupon_invalid"))
            return
        if user_used_coupon(coupon["id"], user.id):
            await update.message.reply_text(t(lang, "coupon_used"))
            return
        if coupon["max_uses"] > 0 and coupon["used_count"] >= coupon["max_uses"]:
            await update.message.reply_text(t(lang, "coupon_invalid"))
            return
        context.user_data["coupon_code"] = coupon["code"]
        await update.message.reply_text(
            t(lang, "coupon_valid", code=coupon["code"], percent=coupon["percent"]),
            reply_markup=buy_keyboard(user.id)
        )
        return

    # حجم لینک ادمین
    if user.id == ADMIN_ID and context.user_data.get("admin_waiting_volume"):
        try:
            volume = int(text)
            if volume <= 0 or volume > 1000:
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ حجم نامعتبر است.")
            return
        context.user_data["admin_waiting_volume"] = False
        context.user_data["admin_add_volume"] = str(volume)
        context.user_data["admin_waiting_link"] = True
        await update.message.reply_text(f"✅ حجم {volume} گیگ ثبت شد.\n\nحالا لینک Subscription را ارسال کن.")
        return

    # لینک سرویس ادمین
    if user.id == ADMIN_ID and context.user_data.get("admin_waiting_link"):
        if not (text.startswith("http://") or text.startswith("https://")):
            await update.message.reply_text("❌ لینک معتبر نیست.")
            return
        volume = context.user_data.get("admin_add_volume")
        add_subscription(volume, text)
        context.user_data.pop("admin_waiting_link", None)
        context.user_data.pop("admin_add_volume", None)
        await update.message.reply_text(f"✅ لینک اضافه شد.\n\n📦 حجم: {volume} گیگ")
        return


# =========================================================
# رسید پرداخت
# =========================================================

async def receipt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user(user)
    lang = get_user_language(user.id) or "fa"

    order = get_latest_pending_order(user.id)
    if not order:
        await update.message.reply_text(t(lang, "no_pending"))
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
        InlineKeyboardButton("✅ تأیید پرداخت", callback_data=f"approve_{order['id']}"),
        InlineKeyboardButton("❌ رد پرداخت", callback_data=f"reject_{order['id']}")
    ]]

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=update.message.photo[-1].file_id,
        caption=caption,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    await update.message.reply_text(t(lang, "receipt_received", order=order["id"]))


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
    normalized_volume = _normalize_volume(volume)
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
            sub = conn.execute(
                "SELECT id, link FROM subscriptions WHERE CAST(TRIM(REPLACE(REPLACE(LOWER(volume), 'gb', ''), 'گیگ', '')) AS INTEGER) = ? AND used = 0 ORDER BY id LIMIT 1",
                (int(normalized_volume),)
            ).fetchone()
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
                (user.id, -price, "purchase", f"خرید سرویس {normalized_volume} گیگ", now_text())
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
        field("reply_markup", json.dumps({"inline_keyboard":[[{"text":"✅ تأیید پرداخت","callback_data":f"approve_{order_id}"},{"text":"❌ رد پرداخت","callback_data":f"reject_{order_id}"}]]}, ensure_ascii=False))
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
            plans=[{"volume":v,"price":p,"available":bool(get_stock().get(v,0))} for v,p in TARIFF_PLANS.items()]
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
                    price=int(float(order["volume"]))*PRICE_PER_GB; bal=conn.execute("SELECT balance FROM users WHERE user_id=?",(u.id,)).fetchone()[0] or 0
                    if bal<price: conn.rollback(); return self._send(200,{"ok":False,"error":"insufficient_balance","balance":bal,"price":price})
                    old=datetime.strptime(order["expires_at"],"%Y-%m-%d %H:%M:%S") if order["expires_at"] else datetime.now(); base=max(old,datetime.now()); newexp=base+timedelta(days=SERVICE_DAYS)
                    conn.execute("UPDATE users SET balance=balance-? WHERE user_id=?",(price,u.id)); conn.execute("INSERT INTO wallet_transactions (user_id,amount,type,description,order_id,created_at) VALUES (?,?,?,?,?,?)",(u.id,-price,"renew",f"تمدید سرویس #{oid}",oid,now_text())); conn.execute("UPDATE orders SET expires_at=? WHERE id=?",(newexp.strftime("%Y-%m-%d %H:%M:%S"),oid)); conn.commit(); return self._send(200,{"ok":True,"order_id":oid,"price":price,"balance":bal-price,"expires_at":newexp.strftime("%Y-%m-%d %H:%M:%S")})
                except Exception as e:
                    conn.rollback(); return self._send(500,{"ok":False,"error":str(e)})
                finally: conn.close()
            volume = _normalize_volume(payload.get("volume"))
            if not volume:
                return self._send(400,{"ok":False,"error":"invalid_volume"})
            price = TARIFF_PLANS.get(volume) or (int(volume) * PRICE_PER_GB)
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
            volume=_normalize_volume(payload.get("volume")); price=(TARIFF_PLANS.get(volume) or (int(volume) * PRICE_PER_GB)) if volume else 0; img=payload.get("image","")
            if not volume or price <= 0 or not img: return self._send(400,{"ok":False,"error":"invalid_purchase_receipt"})
            oid=create_order(u,volume,price); tg=_telegram_send_photo_base64(u.id,volume,price,img,oid)
            return self._send(200 if tg.get("ok") else 500,{"ok":bool(tg.get("ok")),"order_id":oid})
        return self._send(404,{"ok":False,"error":"not_found"})


def start_miniapp_api():
    server=ThreadingHTTPServer((API_HOST,API_PORT),MiniAppHandler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    print(f"Mini App API listening on {API_HOST}:{API_PORT}")


# =========================================================
# اجرای ربات
# =========================================================

async def post_init(application):
    await set_bot_commands(application)
    try:
        await application.bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="🛒 HanzuVPN",
                web_app=WebAppInfo(url=MINI_APP_URL + "?v=20260928-v6"),
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
    app.add_handler(CommandHandler("buy", buy_command))
    app.add_handler(CommandHandler("services", services_command))
    app.add_handler(CommandHandler("trial", trial_command))
    app.add_handler(CommandHandler("support", support_command))
    app.add_handler(CommandHandler("language", language_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(_button_handler_impl))
    app.add_handler(MessageHandler(filters.PHOTO, receipt_handler))
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