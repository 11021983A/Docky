#!/usr/bin/env python3
import os
import json
import re
import logging
import threading
from datetime import datetime

import requests
from flask import Flask, jsonify
from dotenv import load_dotenv

import telebot
from telebot import types

# -------------------- config --------------------
load_dotenv()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("docky")

BOTTOKEN = os.getenv("BOTTOKEN", "").strip()
WEBAPPURL = os.getenv("WEBAPPURL", "").strip()  # e.g. https://11021983a.github.io/Docky/
ADMINCHATID = os.getenv("ADMINCHATID", "").strip()

PORT = int(os.environ.get("PORT", "10000"))

if not BOTTOKEN:
    raise RuntimeError("BOTTOKEN is empty. Set BOTTOKEN env var.")

if not WEBAPPURL or not WEBAPPURL.startswith("https://"):
    raise RuntimeError("WEBAPPURL must be set and start with https:// (GitHub Pages / HTTPS hosting).")

# -------------------- assets --------------------
ASSETS = {
    "business-center": {
        "icon": "🏢",
        "title": "Бизнес-центр",
        "description": "Документы для БЦ (шаблон перечня).",
        "filename": "docs_business_center.docx",
        "url": "https://github.com/11021983A/Docky/raw/main/1.docx",
    },
    "shopping-center": {
        "icon": "🛍️",
        "title": "Торговый центр",
        "description": "Документы для ТЦ (шаблон перечня).",
        "filename": "docs_shopping_center.docx",
        "url": "https://github.com/11021983A/Docky/raw/main/1.docx",
    },
    "warehouse": {
        "icon": "📦",
        "title": "Склад",
        "description": "Документы для склада (шаблон перечня).",
        "filename": "docs_warehouse.docx",
        "url": "https://github.com/11021983A/Docky/raw/main/1.docx",
    },
    "hotel": {
        "icon": "🏨",
        "title": "Гостиница",
        "description": "Документы для гостиницы (шаблон перечня).",
        "filename": "docs_hotel.docx",
        "url": "https://github.com/11021983A/Docky/raw/main/1.docx",
    },
    "equipment": {
        "icon": "⚙️",
        "title": "Оборудование",
        "description": "Документы для оборудования (шаблон перечня).",
        "filename": "docs_equipment.docx",
        "url": "https://github.com/11021983A/Docky/raw/main/1.docx",
    },
}

# -------------------- telegram bot --------------------
bot = telebot.TeleBot(BOTTOKEN, parse_mode="Markdown")

def get_webapp_url() -> str:
    # cache busting so telegram reloads page if needed
    return f"{WEBAPPURL}?v={int(datetime.utcnow().timestamp())}"

def webapp_reply_keyboard() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("Открыть документы", web_app=types.WebAppInfo(url=get_webapp_url())))
    return kb

def validate_email(email: str) -> bool:
    if not email:
        return False
    return re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", email) is not None

def download_doc_bytes(url: str) -> bytes:
    r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return r.content

@bot.message_handler(commands=["start"])
def cmd_start(message):
    text = (
        "Бот помогает выбрать тип актива и скачать шаблоны документов для залога.\n\n"
        "Нажмите кнопку *Открыть документы* (это Telegram Mini App)."
    )
    bot.send_message(message.chat.id, text, reply_markup=webapp_reply_keyboard())

@bot.message_handler(commands=["help"])
def cmd_help(message):
    bot.send_message(
        message.chat.id,
        "/start — открыть Mini App\n"
        "/assets — список активов (выдача файла в чат)\n",
        reply_markup=webapp_reply_keyboard(),
    )

@bot.message_handler(commands=["assets"])
def cmd_assets(message):
    kb = types.InlineKeyboardMarkup()
    for key, asset in ASSETS.items():
        kb.add(types.InlineKeyboardButton(f"{asset['icon']} {asset['title']}", callback_data=f"get:{key}"))
    bot.send_message(message.chat.id, "Выберите актив, чтобы получить файл прямо в чат:", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("get:"))
def cb_get_asset(call):
    asset_key = call.data.split(":", 1)[1]
    asset = ASSETS.get(asset_key)
    if not asset:
        bot.answer_callback_query(call.id, "Неизвестный актив")
        return

    bot.answer_callback_query(call.id, "Готовлю файл...")
    try:
        content = download_doc_bytes(asset["url"])
        bot.send_document(
            call.message.chat.id,
            document=content,
            visible_file_name=asset["filename"],
            caption=f"{asset['icon']} *{asset['title']}*\n{asset['description']}",
        )
    except Exception as e:
        logger.exception("Failed to send document")
        bot.send_message(call.message.chat.id, f"Не удалось скачать/отправить файл: `{e}`")

# ВАЖНО: обработчик данных из Mini App
@bot.message_handler(content_types=["web_app_data"])
def on_webapp_data(message):
    # В pyTelegramBotAPI данные приходят в message.web_app_data.data
    raw = getattr(message.web_app_data, "data", None)
    if not raw:
        bot.reply_to(message, "Не получены данные из Mini App.")
        return

    try:
        payload = json.loads(raw)
    except Exception:
        bot.reply_to(message, "Ошибка: данные из Mini App не JSON.")
        return

    action = payload.get("action")
    asset_key = payload.get("assettype")

    if action == "download":
        asset = ASSETS.get(asset_key)
        if not asset:
            bot.reply_to(message, "Неизвестный актив.")
            return
        try:
            content = download_doc_bytes(asset["url"])
            bot.send_document(
                message.chat.id,
                document=content,
                visible_file_name=asset["filename"],
                caption=f"{asset['icon']} *{asset['title']}*\n{asset['description']}",
            )
        except Exception as e:
            logger.exception("download action failed")
            bot.reply_to(message, f"Не удалось скачать/отправить: `{e}`")
        return

    # (Опционально) отправка на email — здесь оставлено как заглушка, чтобы бот не падал без SMTP.
    if action == "sendemail":
        email = payload.get("email", "").strip()
        if not validate_email(email):
            bot.reply_to(message, "Некорректный email.")
            return
        bot.reply_to(message, "Отправка на email пока отключена в этой версии (нужна настройка SMTP).")
        return

    bot.reply_to(message, "Неизвестное действие из Mini App.")

def notify_admin(text: str):
    if not ADMINCHATID:
        return
    try:
        bot.send_message(ADMINCHATID, text)
    except Exception:
        logger.warning("Failed to notify admin")

# -------------------- healthcheck for hosting --------------------
app = Flask(__name__)

@app.get("/")
def root():
    return jsonify(status="ok", bot="docky", webapp=WEBAPPURL)

@app.get("/health")
def health():
    return jsonify(status="healthy")

def run_flask():
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)

def main():
    notify_admin("Docky bot started.")
    threading.Thread(target=run_flask, daemon=True).start()

    # На long polling важно удалить webhook, если он был включен ранее
    try:
        bot.remove_webhook()
    except Exception:
        pass

    bot.infinity_polling(timeout=30, long_polling_timeout=30, skip_pending=True)

if __name__ == "__main__":
    main()
