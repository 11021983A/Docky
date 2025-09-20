import os
import telebot
from telebot import types
from dotenv import load_dotenv
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import email.utils
import requests
from io import BytesIO
import json
import re
from datetime import datetime
from threading import Thread
from flask import Flask, jsonify
import time
import uuid
import sys
import socket
import subprocess
import atexit

# Уникальный ID процесса
PROCESS_ID = str(uuid.uuid4())[:8]

# Загружаем переменные из .env файла
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Отключаем debug для urllib3
logging.getLogger('urllib3').setLevel(logging.WARNING)

# Получаем настройки
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://11021983a.github.io/Docky/')
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.mail.ru')
SMTP_PORT = int(os.getenv('SMTP_PORT', '465'))
EMAIL_USER = os.getenv('EMAIL_USER', 'docs_zs@mail.ru')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')
USE_SSL = os.getenv('USE_SSL', 'true').lower() == 'true'

# Проверяем обязательные параметры
if not BOT_TOKEN:
    print("Ошибка: Не найден BOT_TOKEN в файле .env")
    print("Добавьте в Environment Variables: BOT_TOKEN")
    exit()

if not EMAIL_PASSWORD:
    print("Предупреждение: Не найден EMAIL_PASSWORD")
    print("Добавьте пароль приложения Mail.ru в Environment Variables")

# Создаем бота
bot = telebot.TeleBot(BOT_TOKEN)

# Flask приложение для health check
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"status": "alive", "bot": "Доки", "version": "1.0"})

@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

def run_flask():
    """Запуск Flask сервера для health check"""
    port = int(os.environ.get('PORT', 10000))
    try:
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except OSError as e:
        if "Address already in use" in str(e):
            logger.error(f"Порт {port} уже занят, пропускаем запуск Flask")
        else:
            logger.error(f"Ошибка запуска Flask: {e}")

# Хранилище для пользователей
user_sessions = {}

# Данные об активах
ASSETS = {
    'бизнес-центр': {
        'icon': '🏢',
        'title': 'Бизнес-центр',
        'description': 'Офисные здания и бизнес-центры',
        'filename': 'БЦ.docx',
        'url': 'https://github.com/11021983A/Docky/raw/main/БЦ.docx'
    },
    'торговый-центр': {
        'icon': '🛍️',
        'title': 'Торговый центр',
        'description': 'Торговые центры и комплексы',
        'filename': 'ТЦ.docx',
        'url': 'https://github.com/11021983A/Docky/raw/main/ТЦ.docx'
    },
    'складской-комплекс': {
        'icon': '📦',
        'title': 'Складской комплекс',
        'description': 'Складские помещения и комплексы',
        'filename': 'Склад.docx',
        'url': 'https://github.com/11021983A/Docky/raw/main/Склад.docx'
    },
    'гостиница': {
        'icon': '🏨',
        'title': 'Гостиница',
        'description': 'Гостиничные комплексы',
        'filename': 'Гостиница.docx',
        'url': 'https://github.com/11021983A/Docky/raw/main/Гостиница.docx'
    },
    'бизнес': {
        'icon': '💼',
        'title': 'Бизнес',
        'description': 'Доли в бизнесе и акции',
        'filename': 'Бизнес_КИ.docx',
        'url': 'https://github.com/11021983A/Docky/raw/main/Бизнес_КИ.docx'
    },
    'комплекс-имущества': {
        'icon': '🗗️',
        'title': 'Комплекс имущества',
        'description': 'Имущественные комплексы',
        'filename': 'Бизнес_КИ.docx',
        'url': 'https://github.com/11021983A/Docky/raw/main/Бизнес_КИ.docx'
    },
    'машины-и-оборудование': {
        'icon': '⚙️',
        'title': 'Машины и оборудование',
        'description': 'Промышленное оборудование',
        'filename': 'МиО.docx',
        'url': 'https://github.com/11021983A/Docky/raw/main/МиО.docx'
    },
    'имущественные-права-на-жилье': {
        'icon': '🏠',
        'title': 'ИПС на жилье',
        'description': 'Права на жилую недвижимость',
        'filename': 'ИПС_жилье.docx',
        'url': 'https://github.com/11021983A/Docky/raw/main/ИПС_жилье.docx'
    }
}

def validate_email(email: str) -> bool:
    """Валидация email адреса"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def send_email_with_document(recipient_email: str, asset_type: str, user_name: str) -> bool:
    """Отправка email с документом через Mail.ru"""
    if not EMAIL_USER:
        logger.error("EMAIL_USER не задан")
        return False
    
    if not EMAIL_PASSWORD:
        logger.error("EMAIL_PASSWORD не задан")
        return False
    
    logger.info(f"=" * 50)
    logger.info(f"НАЧАЛО ОТПРАВКИ EMAIL")
    logger.info(f"Отправитель: {EMAIL_USER}")
    logger.info(f"Получатель: {recipient_email}")
    logger.info(f"Актив: {asset_type}")
    logger.info(f"Пользователь: {user_name}")
    logger.info(f"SMTP: {SMTP_SERVER}:{SMTP_PORT}")
    logger.info(f"=" * 50)
    
    try:
        asset = ASSETS.get(asset_type)
        if not asset:
            logger.error(f"Актив {asset_type} не найден в ASSETS")
            return False
            
        # Создаем сообщение
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = recipient_email
        msg['Subject'] = f'Документы для залога - {asset["title"]}'
        msg['Reply-To'] = EMAIL_USER
        msg['Date'] = email.utils.formatdate(localtime=True)
        msg['Message-ID'] = email.utils.make_msgid()
        
        # HTML тело письма
        html_body = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .info-box {{ background: #f8f9fa; border-left: 4px solid #007bff; padding: 15px; margin: 15px 0; }}
                .footer {{ background: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>{asset['icon']} Документы для залоговой службы</h2>
                <p>Тип актива: {asset['title']}</p>
            </div>
            
            <div class="content">
                <p>Здравствуйте, {user_name}!</p>
                
                <p>Спасибо за использование нашего Telegram бота! Во вложении вы найдете полный перечень документов для оформления залога типа <strong>"{asset['title']}"</strong>.</p>
                
                <div class="info-box">
                    <h4>Информация об активе:</h4>
                    <ul>
                        <li><strong>Тип:</strong> {asset['description']}</li>
                        <li><strong>Файл:</strong> {asset['filename']}</li>
                    </ul>
                </div>
            </div>
            
            <div class="footer">
                <p>Это письмо было отправлено автоматически через Telegram бота "Доки"</p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
        
        # Пытаемся загрузить и прикрепить документ
        try:
            document_url = asset['url']
            logger.info(f"Загружаем документ с URL: {document_url}")
            response = requests.get(document_url, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            if response.status_code == 200:
                attachment = MIMEBase('application', 'octet-stream')
                attachment.set_payload(response.content)
                encoders.encode_base64(attachment)
                attachment.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{asset["filename"]}"'
                )
                msg.attach(attachment)
                logger.info(f"Документ {asset['filename']} прикреплен к письму, размер: {len(response.content)} байт")
            else:
                logger.warning(f"Не удалось загрузить документ: HTTP {response.status_code}")
                
        except Exception as e:
            logger.error(f"Ошибка загрузки документа: {e}")
        
        # Отправляем email
        logger.info(f"Подключаемся к SMTP серверу {SMTP_SERVER}:{SMTP_PORT} (SSL: {USE_SSL})")
        
        try:
            if USE_SSL or SMTP_PORT == 465:
                logger.info("Используем SSL подключение...")
                server = smtplib.SMTP_SSL(SMTP_SERVER, 465, timeout=30)
                server.set_debuglevel(1)
            else:
                logger.info("Используем TLS подключение...")
                server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
                server.set_debuglevel(1)
                server.starttls()
            
            logger.info(f"Логинимся как {EMAIL_USER}")
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            
            logger.info(f"Отправляем письмо на {recipient_email}")
            logger.info(f"From: {EMAIL_USER}")
            logger.info(f"To: {recipient_email}")
            
            try:
                server.sendmail(EMAIL_USER, [recipient_email], msg.as_string())
                logger.info("Метод sendmail успешен")
            except Exception as e:
                logger.error(f"Ошибка sendmail: {e}")
                try:
                    server.send_message(msg)
                    logger.info("Метод send_message успешен")
                except Exception as e2:
                    logger.error(f"Ошибка send_message: {e2}")
                    raise
            
            server.quit()
            logger.info(f"Email успешно отправлен на {recipient_email}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"Ошибка аутентификации SMTP: {e}")
            logger.error("ПРОВЕРЬТЕ: EMAIL_PASSWORD должен быть паролем приложения Mail.ru, НЕ обычным паролем!")
        except smtplib.SMTPServerDisconnected as e:
            logger.error(f"Сервер разорвал соединение: {e}")
        except smtplib.SMTPException as e:
            logger.error(f"SMTP ошибка: {e}")
        
        return False
        
    except Exception as e:
        logger.error(f"Общая ошибка отправки email: {e}")
        logger.exception("Полный traceback:")
        return False

@bot.message_handler(commands=['start'])
def start_command(message):
    """Стартовое сообщение с Web App"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "Пользователь"
    username = message.from_user.username
    
    user_sessions[user_id] = {
        'name': user_name,
        'username': username,
        'started_at': datetime.now()
    }
    
    keyboard = types.InlineKeyboardMarkup()
    webapp_btn = types.InlineKeyboardButton(
        text="Выберите актив",
        web_app=types.WebAppInfo(url=WEBAPP_URL)
    )
    keyboard.add(webapp_btn)
    
    welcome_text = f"""
🤖 Привет, {user_name}! Меня зовут **Доки**!

📋 Я помогаю с документами для залоговой службы Сбера.

🚀 **Что я умею:**
• Показать перечень требуемых для залоговой службы Банка документов
• Отправить документы на email  

📱 **Нажмите кнопку ниже**, чтобы открыть удобный каталог с документами прямо в Telegram!
"""
    
    bot.send_message(
        message.chat.id,
        welcome_text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['help', 'info'])
def help_command(message):
    """Справочная информация"""
    help_text = f"""
🤖 **Справка по боту Доки**

**Основные возможности:**
📋 Web-каталог документов (встроен в Telegram)
📧 Отправка документов на email
📞 Прямая связь со специалистами

**Доступные активы ({len(ASSETS)} типов):**
"""
    
    for asset_type, asset in ASSETS.items():
        help_text += f"{asset['icon']} **{asset['title']}**\n"
    
    help_text += f"""

**Команды:**
• `/start` - Открыть каталог
• `/help` - Эта справка
• `/contacts` - Контактная информация
• `/test_email` - Тестовая отправка email

**Веб-приложение:** {WEBAPP_URL}

💡 **Совет:** Используйте веб-каталог для быстрого выбора и скачивания документов!
"""
    
    keyboard = types.InlineKeyboardMarkup()
    webapp_btn = types.InlineKeyboardButton(
        "Выберите актив", 
        web_app=types.WebAppInfo(url=WEBAPP_URL)
    )
    keyboard.add(webapp_btn)
    
    bot.send_message(
        message.chat.id,
        help_text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['contacts'])
def contacts_command(message):
    """Контактная информация"""
    contacts_text = """
📞 **Контакты службы поддержки**

📧 **Email:** docs_zs@mail.ru
🤖 **Telegram:** @your_docs_bot  
📱 **WhatsApp:** +7 (XXX) XXX-XX-XX

⏰ **Время работы:**
Пн-Пт: 9:00 - 18:00
Сб-Вс: 10:00 - 16:00

📋 **Веб-каталог доступен 24/7**
"""
    
    keyboard = types.InlineKeyboardMarkup()
    webapp_btn = types.InlineKeyboardButton(
        "Выберите актив", 
        web_app=types.WebAppInfo(url=WEBAPP_URL)
    )
    email_btn = types.InlineKeyboardButton(
        "📧 Написать на почту", 
        url=f"mailto:{EMAIL_USER}"
    )
    keyboard.add(webapp_btn)
    keyboard.add(email_btn)
    
    bot.send_message(
        message.chat.id,
        contacts_text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    """Обработка нажатий на кнопки"""
    try:
        if call.data == "help":
            help_command(call.message)
        elif call.data == "contacts":
            contacts_command(call.message)
        
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        logger.error(f"Ошибка в callback: {e}")
        bot.answer_callback_query(call.id, "Произошла ошибка")

@bot.message_handler(content_types=['web_app_data'])
def handle_web_app_data(message):
    """Обработка данных от Web App"""
    logger.info("🔔 ВЫЗВАН ОБРАБОТЧИК WEB_APP_DATA")
    logger.info(f"   📱 Тип сообщения: {message.content_type}")
    logger.info(f"   👤 От пользователя: {message.from_user.first_name} (ID: {message.from_user.id})")
    
    try:
        if not hasattr(message, 'web_app_data') or not message.web_app_data:
            logger.error("❌ НЕТ ДАННЫХ WEB_APP_DATA В СООБЩЕНИИ")
            bot.reply_to(message, "⌛ Не получены данные от веб-приложения")
            return
        
        if not hasattr(message.web_app_data, 'data') or not message.web_app_data.data:
            logger.error("❌ ПУСТЫЕ ДАННЫЕ В WEB_APP_DATA")
            bot.reply_to(message, "⌛ Пустые данные от веб-приложения")
            return
        
        logger.info(f"   📋 Сырые данные: {message.web_app_data.data}")
        
        web_app_data = json.loads(message.web_app_data.data)
        action = web_app_data.get('action')
        
        user_id = message.from_user.id
        user_name = message.from_user.first_name or "Пользователь"
        
        logger.info(f"📱 ПОЛУЧЕНЫ ДАННЫЕ ОТ WEB APP:")
        logger.info(f"   👤 Пользователь: {user_name} (ID: {user_id})")
        logger.info(f"   🎯 Действие: {action}")
        logger.info(f"   📋 Полные данные: {web_app_data}")
        
        if action == 'send_email':
            email = web_app_data.get('email')
            asset_type = web_app_data.get('asset_type')
            
            logger.info(f"📧 ЗАПРОС НА ОТПРАВКУ EMAIL:")
            logger.info(f"   📬 Email: {email}")
            logger.info(f"   📄 Актив: {asset_type}")
            
            if not email:
                logger.error("❌ Email адрес не указан в данных")
                bot.reply_to(message, "⌛ Email адрес не указан")
                return
            
            if not validate_email(email):
                logger.error(f"❌ Неверный формат email: {email}")
                bot.reply_to(message, f"⌛ Неверный формат email адреса: {email}")
                return
            
            if asset_type not in ASSETS:
                logger.error(f"❌ Неизвестный актив: {asset_type}")
                logger.error(f"   Доступные активы: {list(ASSETS.keys())}")
                bot.reply_to(message, f"⌛ Неизвестный тип актива: {asset_type}")
                return
            
            logger.info(f"📤 Отправляем уведомление пользователю о начале отправки")
            bot.reply_to(message, f"📧 Письмо направлено на {email}")
            
            logger.info(f"📮 НАЧИНАЕМ ОТПРАВКУ EMAIL:")
            logger.info(f"   📬 Получатель: {email}")
            logger.info(f"   📄 Тип актива: {asset_type}")
            logger.info(f"   👤 Имя отправителя: {user_name}")
            
            success = send_email_with_document(email, asset_type, user_name)
            
            asset = ASSETS[asset_type]
            
            if success:
                logger.info(f"✅ EMAIL УСПЕШНО ОТПРАВЛЕН на {email}")
                response_text = f"""
✅ **Документы отправлены!**

📧 **Email:** {email}
📄 **Актив:** {asset['icon']} {asset['title']}

📬 Проверьте входящие письма и папку "Спам".

📄 Нужны документы для другого актива? Откройте каталог снова!
"""
                keyboard = types.InlineKeyboardMarkup()
                webapp_btn = types.InlineKeyboardButton(
                    "Выберите другой актив", 
                    web_app=types.WebAppInfo(url=WEBAPP_URL)
                )
                keyboard.add(webapp_btn)
                
                bot.send_message(
                    message.chat.id, 
                    response_text, 
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
                
                if ADMIN_CHAT_ID:
                    admin_msg = f"📧 Email отправлен\n👤 {user_name} (@{message.from_user.username})\n📄 {asset['title']}\n📧 {email}"
                    try:
                        bot.send_message(ADMIN_CHAT_ID, admin_msg)
                        logger.info(f"📨 Уведомление админу отправлено")
                    except Exception as e:
                        logger.error(f"❌ Ошибка отправки уведомления админу: {e}")
            else:
                logger.error(f"❌ ОШИБКА ОТПРАВКИ EMAIL на {email}")
                bot.send_message(
                    message.chat.id,
                    f"⌛ **Ошибка отправки email**\n\n"
                    f"Не удалось отправить документы для {asset['icon']} {asset['title']} на адрес {email}.\n\n"
                    f"📄 Попробуйте:\n"
                    f"• Проверить правильность email\n"
                    f"• Скачать документ и отправить вручную\n"
                    f"• Написать нам напрямую: {EMAIL_USER}\n\n"
                    f"💡 Используйте команду /test_email для проверки системы",
                    parse_mode='Markdown'
                )
        
        elif action == 'download_completed':
            asset_type = web_app_data.get('asset_type')
            logger.info(f"📥 СКАЧИВАНИЕ ЗАВЕРШЕНО:")
            logger.info(f"   📄 Актив: {asset_type}")
            logger.info(f"   👤 Пользователь: {user_name}")
            
            if asset_type in ASSETS:
                asset = ASSETS[asset_type]
                
                response_text = f"""
✅ **Документ скачан!**

📄 **Актив:** {asset['icon']} {asset['title']}
📂 **Файл:** {asset['filename']}
"""
                
                keyboard = types.InlineKeyboardMarkup()
                webapp_btn = types.InlineKeyboardButton(
                    "Выбрать другой актив", 
                    web_app=types.WebAppInfo(url=WEBAPP_URL)
                )
                keyboard.add(webapp_btn)
                
                bot.reply_to(
                    message, 
                    response_text, 
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            else:
                logger.error(f"❌ Неизвестный актив при скачивании: {asset_type}")
        
        else:
            logger.warning(f"⚠️ Неизвестное действие от веб-приложения: {action}")
            logger.warning(f"   Полученные данные: {web_app_data}")
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Ошибка парсинга JSON от Web App: {e}")
        logger.error(f"   Сырые данные: {message.web_app_data.data if hasattr(message, 'web_app_data') and message.web_app_data else 'НЕТ ДАННЫХ'}")
        bot.reply_to(message, "⌛ Ошибка обработки данных от веб-приложения")
    except Exception as e:
        logger.error(f"❌ Общая ошибка обработки Web App данных: {e}")
        logger.exception("📋 Полный traceback:")
        bot.reply_to(message, "⌛ Произошла ошибка при обработке запроса")

@bot.message_handler(commands=['test_send'])
def test_send_command(message):
    """Команда для тестовой отправки email на указанный адрес"""
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Используйте: /test_send email@example.com")
        return
    
    test_email = parts[1]
    if not validate_email(test_email):
        bot.reply_to(message, f"⌛ Неверный формат email: {test_email}")
        return
    
    test_data = {
        'action': 'send_email',
        'asset_type': 'бизнес-центр',
        'email': test_email
    }
    
    user_name = message.from_user.first_name or "Пользователь"
    
    logger.info(f"Тест отправки через /test_send")
    logger.info(f"Данные: {test_data}")
    
    bot.reply_to(message, f"📧 Тестирую отправку на {test_email}...")
    
    success = send_email_with_document(test_email, 'бизнес-центр', user_name)
    
    if success:
        bot.reply_to(message, f"✅ Письмо отправлено на {test_email}!")
    else:
        bot.reply_to(message, f"⌛ Ошибка отправки на {test_email}")

@bot.message_handler(commands=['test_email'])
def test_email_command(message):
    """Команда для тестирования отправки email"""
    user_name = message.from_user.first_name or "Тестовый пользователь"
    
    if not EMAIL_USER or not EMAIL_PASSWORD:
        bot.reply_to(message, "⌛ Email настройки не заданы в переменных окружения")
        return
    
    parts = message.text.split()
    if len(parts) > 1:
        test_email = parts[1]
        if not validate_email(test_email):
            bot.reply_to(message, f"⌛ Неверный формат email: {test_email}")
            return
    else:
        test_email = EMAIL_USER
    bot.reply_to(message, f"📄 Отправляю тестовое письмо на {test_email}...")
    
    success = send_email_with_document(test_email, 'бизнес-центр', user_name)
    
    if success:
        bot.reply_to(message, f"✅ Тестовое письмо успешно отправлено на {test_email}!\n📬 Проверьте почту и папку Спам.")
    else:
        bot.reply_to(message, f"⌛ Ошибка отправки на {test_email}.\n📋 Проверьте логи для деталей.")

@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
    """Обработка текстовых сообщений"""
    logger.info(f"📨 ПОЛУЧЕНО СООБЩЕНИЕ:")
    logger.info(f"   👤 От: {message.from_user.first_name} (ID: {message.from_user.id})")
    logger.info(f"   📝 Тип: {message.content_type}")
    logger.info(f"   📄 Текст: {message.text if hasattr(message, 'text') else 'НЕТ ТЕКСТА'}")
    
    if message.content_type == 'web_app_data':
        logger.info("🔄 Это сообщение web_app_data, перенаправляем в специальный обработчик")
        return
    
    user_message = message.text.lower() if hasattr(message, 'text') and message.text else ""
    
    found_assets = []
    for asset_key, asset_data in ASSETS.items():
        if (any(word in user_message for word in asset_key.split('-')) or
            any(word in user_message for word in asset_data['title'].lower().split())):
            found_assets.append((asset_key, asset_data))
    
    if found_assets:
        if len(found_assets) == 1:
            asset_key, asset_data = found_assets[0]
            
            response_text = f"""
{asset_data['icon']} **{asset_data['title']}**

📝 {asset_data['description']}

🎯 **Что хотите сделать?**
"""
            
            keyboard = types.InlineKeyboardMarkup()
            
            webapp_url_with_asset = f"{WEBAPP_URL}?asset={asset_key}"
            webapp_btn = types.InlineKeyboardButton(
                f"📋 Открыть {asset_data['title']}", 
                web_app=types.WebAppInfo(url=webapp_url_with_asset)
            )
            keyboard.add(webapp_btn)
            
            catalog_btn = types.InlineKeyboardButton(
                "📚 Весь каталог", 
                web_app=types.WebAppInfo(url=WEBAPP_URL)
            )
            keyboard.add(catalog_btn)
            
        else:
            assets_text = '\n'.join([
                f"• {data['icon']} {data['title']}" 
                for _, data in found_assets
            ])
            
            response_text = f"""
🔍 **Найдено активов: {len(found_assets)}**

{assets_text}

📋 **Откройте каталог для выбора:**
"""
            
            keyboard = types.InlineKeyboardMarkup()
            webapp_btn = types.InlineKeyboardButton(
                "Выберите актив", 
                web_app=types.WebAppInfo(url=WEBAPP_URL)
            )
            keyboard.add(webapp_btn)
        
        bot.reply_to(
            message, 
            response_text, 
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
    else:
        response_text = f"""
🤖 Понял вас не совсем точно.

📋 **Доступно {len(ASSETS)} типов активов:**
"""
        
        for i, (_, asset_data) in enumerate(list(ASSETS.items())[:4]):
            response_text += f"{asset_data['icon']} {asset_data['title']}\n"
        
        if len(ASSETS) > 4:
            response_text += f"...и еще {len(ASSETS) - 4}\n"
        
        response_text += "\n💡 **Откройте каталог для удобного выбора:**"
        
        keyboard = types.InlineKeyboardMarkup()
        webapp_btn = types.InlineKeyboardButton(
            "Выберите актив", 
            web_app=types.WebAppInfo(url=WEBAPP_URL)
        )
        help_btn = types.InlineKeyboardButton("ℹ️ Справка", callback_data="help")
        keyboard.add(webapp_btn)
        keyboard.add(help_btn)
        
        bot.reply_to(
            message, 
            response_text, 
            parse_mode='Markdown',
            reply_markup=keyboard
        )

def main():
    """Основная функция запуска бота"""
    logger.info(f"🚀 Запуск Telegram Web App бота 'Доки' [Process: {PROCESS_ID}]")
    logger.info(f"📱 Web App URL: {WEBAPP_URL}")
    logger.info(f"📧 Email: {'✅ Настроен' if EMAIL_USER and EMAIL_PASSWORD else '⌛ Не настроен'}")
    logger.info(f"👮 Админ: {'✅ Настроен' if ADMIN_CHAT_ID else '⌛ Не настроен'}")
    
    print("=" * 50)
    print(f"🤖 TELEGRAM WEB APP БОТ 'ДОКИ' ЗАПУЩЕН [{PROCESS_ID}]")
    print("=" * 50)
    print(f"📱 Web App: {WEBAPP_URL}")
    print(f"📧 Email: {EMAIL_USER}")
    print(f"🌐 Health Check: http://localhost:{os.environ.get('PORT', 10000)}")
    print(f"📧 Функции:")
    print("   ✅ Telegram Web App интеграция")
    print("   ✅ Отправка email через Mail.ru")
    print("   ✅ HTTP Health Check для Render")
    print("   ✅ Автоматическое прикрепление документов")
    print("   ✅ Поиск активов по ключевым словам")
    print("   ✅ Обработка данных от веб-приложения")
    print("   ✅ Тестовая команда /test_email")
    print("=" * 50)
    
    try:
        bot.remove_webhook()
        bot.delete_webhook()
        try:
            updates = bot.get_updates(timeout=1)
            if updates:
                last_update_id = updates[-1].update_id
                bot.get_updates(offset=last_update_id + 1, timeout=1)
        except:
            pass
        logger.info("✅ Webhook очищен, старые обновления пропущены")
    except telebot.apihelper.ApiTelegramException as e:
        if "Conflict" in str(e):
            logger.error("⌛ Конфликт при очистке: другой экземпляр бота запущен")
            logger.error("Завершаем процесс для перезапуска Render")
            sys.exit(1)
    except Exception as e:
        logger.warning(f"Предупреждение при очистке webhook: {e}")
    
    time.sleep(2)
    
    try:
        bot_info = bot.get_me()
        print(f"✅ Подключение к Telegram: @{bot_info.username}")
        
        try:
            port = int(os.environ.get('PORT', 10000))
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            
            if result != 0:
                flask_thread = Thread(target=run_flask)
                flask_thread.daemon = True
                flask_thread.start()
                logger.info(f"🌐 HTTP сервер запущен на порту {port}")
            else:
                logger.warning(f"⚠️ Порт {port} уже занят, Flask не запущен")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось запустить Flask: {e}")
        
        time.sleep(2)
        
        logger.info("🤖 Telegram бот запущен и готов к работе")
        bot.polling(none_stop=True, timeout=60, skip_pending=True)
        
    except telebot.apihelper.ApiTelegramException as e:
        if "Conflict" in str(e):
            logger.error("⌛ Конфликт: другой экземпляр бота уже запущен")
            logger.error("Остановите другой процесс или подождите 30 секунд")
            time.sleep(30)
            main()
        else:
            logger.error(f"Telegram API ошибка: {e}")
            raise
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        
        if ADMIN_CHAT_ID:
            try:
                bot.send_message(
                    ADMIN_CHAT_ID, 
                    f"🚨 **Критическая ошибка бота:**\n```\n{str(e)}\n```",
                    parse_mode='Markdown'
                )
            except:
                pass
        
        print("⚠️ Попытка перезапуска через 5 секунд...")
        time.sleep(5)
        main()

if __name__ == '__main__':
    main()
