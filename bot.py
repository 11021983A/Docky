#!/usr/bin/env python3
import os
import json
import logging
import threading
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import requests
from flask import Flask, jsonify
from dotenv import load_dotenv
import telebot
from telebot import types

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Переменные окружения (обязательно задать на Render)
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
WEBAPPURL = os.getenv("WEBAPPURL", "https://11021983a.github.io/Docky/").strip()
PORT = int(os.environ.get("PORT", "10000"))

# Gmail настройки (добавишь на Render)
EMAIL_USER = os.getenv("EMAIL_USER", "").strip()  # bot.docky@gmail.com
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "").strip()  # 16-значный пароль приложения

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN не задан. Установите переменную окружения BOT_TOKEN на Render.")

# Активы (документы)
ASSETS = {
    "business-center": {
        "icon": "🏢",
        "title": "Бизнес-центр",
        "description": "Документы для оформления залога бизнес-центра",
        "filename": "docs_business_center.docx",
        "url": "https://github.com/11021983A/Docky/raw/main/1.docx",
    },
    "shopping-center": {
        "icon": "🛍️",
        "title": "Торговый центр",
        "description": "Документы для оформления залога торгового центра",
        "filename": "docs_shopping_center.docx",
        "url": "https://github.com/11021983A/Docky/raw/main/1.docx",
    },
    "warehouse": {
        "icon": "📦",
        "title": "Склад",
        "description": "Документы для оформления залога склада",
        "filename": "docs_warehouse.docx",
        "url": "https://github.com/11021983A/Docky/raw/main/1.docx",
    },
    "hotel": {
        "icon": "🏨",
        "title": "Гостиница",
        "description": "Документы для оформления залога гостиницы",
        "filename": "docs_hotel.docx",
        "url": "https://github.com/11021983A/Docky/raw/main/1.docx",
    },
    "equipment": {
        "icon": "⚙️",
        "title": "Оборудование",
        "description": "Документы для оформления залога оборудования",
        "filename": "docs_equipment.docx",
        "url": "https://github.com/11021983A/Docky/raw/main/1.docx",
    },
}

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

def webapp_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("📄 Открыть документы", web_app=types.WebAppInfo(url=WEBAPPURL)))
    return kb

# Функция отправки email через Gmail
def send_email_with_document(recipient_email, asset_key, username):
    """Отправляет документ на email через Gmail"""
    if not EMAIL_USER or not EMAIL_PASSWORD:
        logger.error("❌ Email не настроен (нет EMAIL_USER или EMAIL_PASSWORD)")
        return False
    
    asset = ASSETS.get(asset_key)
    if not asset:
        logger.error(f"Актив {asset_key} не найден")
        return False
    
    try:
        # Создание письма
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = recipient_email
        msg['Subject'] = f"Документы для залога: {asset['title']}"
        
        # Текст письма
        body = f"""
Здравствуйте, {username}!

Спасибо за использование нашего Telegram бота!

Во вложении вы найдете документы для оформления залога:
📌 Тип актива: {asset['title']}
📄 Файл: {asset['filename']}

С уважением,
Команда Docky
        """
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # Скачивание и прикрепление файла
        logger.info(f"Скачиваю документ: {asset['url']}")
        response = requests.get(asset['url'], timeout=30)
        if response.status_code == 200:
            attachment = MIMEBase('application', 'octet-stream')
            attachment.set_payload(response.content)
            encoders.encode_base64(attachment)
            attachment.add_header('Content-Disposition', f'attachment; filename="{asset["filename"]}"')
            msg.attach(attachment)
            logger.info(f"✅ Файл прикреплён ({len(response.content)} байт)")
        else:
            logger.warning(f"⚠️ Не удалось скачать файл (HTTP {response.status_code})")
            return False
        
        # Отправка через Gmail SMTP
        logger.info(f"Отправляю email на {recipient_email}...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"✅ Email успешно отправлен на {recipient_email}")
        return True
        
    except smtplib.SMTPAuthenticationError:
        logger.error("❌ Ошибка авторизации Gmail. Проверьте EMAIL_USER и EMAIL_PASSWORD")
        return False
    except Exception as e:
        logger.exception(f"❌ Ошибка отправки email: {e}")
        return False

# Flask для healthcheck (нужен Render)
app = Flask(__name__)

@app.route("/")
def home():
    return jsonify(status="ok", bot="DockyZS", email_enabled=bool(EMAIL_USER and EMAIL_PASSWORD))

@app.route("/health")
def health():
    return jsonify(status="healthy"), 200

def run_flask():
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)

# Telegram команды
@bot.message_handler(commands=["start"])
def cmd_start(message):
    username = message.from_user.first_name or "Друг"
    email_status = "✅ Отправка на email работает" if EMAIL_USER and EMAIL_PASSWORD else "⚠️ Email не настроен"
    text = f"Привет, {username}!\n\nВыберите тип актива и получите документы для залога.\nНажмите кнопку *Открыть документы*.\n\n{email_status}"
    bot.send_message(message.chat.id, text, reply_markup=webapp_keyboard())

@bot.message_handler(commands=["help"])
def cmd_help(message):
    bot.send_message(message.chat.id, "/start — открыть Mini App\n/help — помощь", reply_markup=webapp_keyboard())

# Обработчик данных из Mini App
@bot.message_handler(content_types=["web_app_data"])
def on_webapp_data(message):
    try:
        raw = message.web_app_data.data
        payload = json.loads(raw)
        action = payload.get("action")
        username = message.from_user.first_name or "Пользователь"
        
        # Скачивание документа завершено (прямо в браузере)
        if action == "downloadcompleted":
            asset_key = payload.get("assettype")
            asset = ASSETS.get(asset_key)
            if asset:
                bot.reply_to(message, f"✅ Документ *{asset['title']}* скачан!\n\nЕсли нужно ещё — нажмите кнопку ниже.", reply_markup=webapp_keyboard())
            else:
                bot.reply_to(message, "Неизвестный актив.")
        
        # Отправка на email
        elif action == "sendemail":
            email = payload.get("email", "").strip()
            asset_key = payload.get("assettype")
            
            if not email:
                bot.reply_to(message, "❌ Email не указан.")
                return
            
            if not EMAIL_USER or not EMAIL_PASSWORD:
                bot.reply_to(message, "⚠️ Отправка на email временно недоступна. Обратитесь к администратору.")
                return
            
            asset = ASSETS.get(asset_key)
            if not asset:
                bot.reply_to(message, "❌ Неизвестный тип актива.")
                return
            
            bot.reply_to(message, f"📧 Отправляю документы на `{email}`...")
            
            success = send_email_with_document(email, asset_key, username)
            
            if success:
                bot.send_message(
                    message.chat.id,
                    f"✅ Документы *{asset['title']}* успешно отправлены на `{email}`!\n\nПроверьте почту (включая папку \"Спам\").",
                    reply_markup=webapp_keyboard()
                )
            else:
                bot.send_message(
                    message.chat.id,
                    f"❌ Не удалось отправить на `{email}`. Попробуйте позже или обратитесь к администратору.",
                    reply_markup=webapp_keyboard()
                )
        
        else:
            bot.reply_to(message, f"Получено действие: `{action}`")
            
    except Exception as e:
        logger.exception("Ошибка обработки web_app_data")
        bot.reply_to(message, "Произошла ошибка при обработке данных из Mini App.")

def main():
    logger.info(f"🤖 Бот запускается: {WEBAPPURL}")
    logger.info(f"📧 Email: {'настроен (' + EMAIL_USER + ')' if EMAIL_USER else 'не настроен'}")
    
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
