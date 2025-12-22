#!/usr/bin/env python3
import os
import json
import logging
import threading
from flask import Flask, jsonify
from dotenv import load_dotenv
import telebot
from telebot import types

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Переменные окружения (обязательно задать на Render)
BOTTOKEN = os.getenv("BOT_TOKEN", "").strip()
WEBAPPURL = os.getenv("WEBAPPURL", "https://11021983a.github.io/Docky/").strip()
PORT = int(os.environ.get("PORT", "10000"))

if not BOTTOKEN:
    raise RuntimeError("❌ BOTTOKEN не задан. Установите переменную окружения BOTTOKEN на Render.")

# Активы (документы)
ASSETS = {
    "business-center": {
        "icon": "🏢",
        "title": "Бизнес-центр",
        "filename": "docs_bc.docx",
        "url": "https://github.com/11021983A/Docky/raw/main/1.docx",
    },
    "shopping-center": {
        "icon": "🛍️",
        "title": "Торговый центр",
        "filename": "docs_tc.docx",
        "url": "https://github.com/11021983A/Docky/raw/main/1.docx",
    },
    "warehouse": {
        "icon": "📦",
        "title": "Склад",
        "filename": "docs_sklad.docx",
        "url": "https://github.com/11021983A/Docky/raw/main/1.docx",
    },
    "hotel": {
        "icon": "🏨",
        "title": "Гостиница",
        "filename": "docs_hotel.docx",
        "url": "https://github.com/11021983A/Docky/raw/main/1.docx",
    },
    "equipment": {
        "icon": "⚙️",
        "title": "Оборудование",
        "filename": "docs_equipment.docx",
        "url": "https://github.com/11021983A/Docky/raw/main/1.docx",
    },
}

bot = telebot.TeleBot(BOTTOKEN, parse_mode="Markdown")

def webapp_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("📄 Открыть документы", web_app=types.WebAppInfo(url=WEBAPPURL)))
    return kb

# Flask для healthcheck (нужен Render)
app = Flask(__name__)

@app.route("/")
def home():
    return jsonify(status="ok", bot="DockyZS")

@app.route("/health")
def health():
    return jsonify(status="healthy"), 200

def run_flask():
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)

# Telegram команды
@bot.message_handler(commands=["start"])
def cmd_start(message):
    text = f"Привет, {message.from_user.first_name}!\n\nВыберите тип актива и получите документы для залога.\nНажмите кнопку *Открыть документы*."
    bot.send_message(message.chat.id, text, reply_markup=webapp_keyboard())

@bot.message_handler(commands=["help"])
def cmd_help(message):
    bot.send_message(message.chat.id, "/start — открыть Mini App\n/help — помощь", reply_markup=webapp_keyboard())

# ВАЖНО: обработчик данных из Mini App (с подчёркиванием!)
@bot.message_handler(content_types=["web_app_data"])
def on_webapp_data(message):
    try:
        raw = message.web_app_data.data
        payload = json.loads(raw)
        action = payload.get("action")
        
        if action == "downloadcompleted":
            asset_key = payload.get("assettype")
            asset = ASSETS.get(asset_key)
            if asset:
                bot.reply_to(message, f"✅ Документ *{asset['title']}* скачан!\n\nЕсли нужно ещё — нажмите кнопку ниже.", reply_markup=webapp_keyboard())
            else:
                bot.reply_to(message, "Неизвестный актив.")
        else:
            bot.reply_to(message, f"Получено действие: `{action}`")
    except Exception as e:
        logger.exception("Ошибка обработки web_app_data")
        bot.reply_to(message, "Произошла ошибка при обработке данных из Mini App.")

def main():
    logger.info(f"🤖 Бот запускается: {WEBAPPURL}")
    
    # Запуск Flask в отдельном потоке
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info(f"🌐 Flask healthcheck на порту {PORT}")
    
    # Удаление webhook (если был)
    try:
        bot.remove_webhook()
    except Exception:
        pass
    
    logger.info("✅ Бот готов к работе!")
    bot.infinity_polling(timeout=30, long_polling_timeout=30, skip_pending=True)

if __name__ == "__main__":
    main()
