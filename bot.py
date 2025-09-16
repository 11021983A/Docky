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
import requests
from io import BytesIO
import json
import re
from datetime import datetime
from threading import Thread
from flask import Flask, jsonify

# Загружаем переменные из .env файла
load_dotenv()

# Настройка логирования с более детальным выводом
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,  # Изменено на DEBUG для более подробных логов
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Получаем настройки
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://11021983a.github.io/Docky/')
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.mail.ru')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
EMAIL_USER = os.getenv('EMAIL_USER', 'docs_zs@mail.ru')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')

# Проверяем обязательные параметры
if not BOT_TOKEN:
    print("❌ ОШИБКА: Не найден BOT_TOKEN в файле .env")
    print("💡 Добавьте в Environment Variables: BOT_TOKEN")
    exit()

if not EMAIL_PASSWORD:
    print("⚠️ ПРЕДУПРЕЖДЕНИЕ: Не найден EMAIL_PASSWORD")
    print("💡 Добавьте пароль приложения Mail.ru в Environment Variables")

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
    app.run(host='0.0.0.0', port=port, debug=False)

# Хранилище для пользователей (в памяти для простоты)
user_sessions = {}

# Данные об активах (только необходимая информация)
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
        'icon': '🏗️',
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
    if not EMAIL_USER or not EMAIL_PASSWORD:
        logger.error("Email настройки не заданы - EMAIL_USER или EMAIL_PASSWORD отсутствуют")
        return False
    
    logger.info(f"Начинаем отправку email на {recipient_email} для актива {asset_type}")
    
    try:
        asset = ASSETS.get(asset_type)
        if not asset:
            logger.error(f"Актив {asset_type} не найден в ASSETS")
            return False
            
        # Создаем сообщение
        msg = MIMEMultipart()
        msg['From'] = f'Доки - Банковские документы <{EMAIL_USER}>'
        msg['To'] = recipient_email
        msg['Subject'] = f'{asset["icon"]} Документы для {asset["title"]}'
        
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
                
                <p><strong>Важные рекомендации:</strong></p>
                <ul>
                    <li>Проверьте актуальность всех документов</li>
                    <li>Убедитесь в правильности заполнения</li>
                    <li>При возникновении вопросов обращайтесь к нашим специалистам</li>
                </ul>
                
                <p>Желаем успешного оформления!</p>
            </div>
            
            <div class="footer">
                <p>Это письмо было отправлено автоматически через Telegram бота "Доки"</p>
                <p>По вопросам: {EMAIL_USER} | Telegram: @your_docs_bot</p>
                <p>© 2024 Банковская залоговая служба</p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
        
        # Пытаемся загрузить и прикрепить документ
        try:
            document_url = asset['url']
            logger.info(f"Загружаем документ с URL: {document_url}")
            response = requests.get(document_url, timeout=30)
            
            if response.status_code == 200:
                attachment = MIMEBase('application', 'octet-stream')
                attachment.set_payload(response.content)
                encoders.encode_base64(attachment)
                attachment.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{asset["filename"]}"'
                )
                msg.attach(attachment)
                logger.info(f"Документ {asset['filename']} прикреплен к письму")
            else:
                logger.warning(f"Не удалось загрузить документ: HTTP {response.status_code}")
                
        except Exception as e:
            logger.error(f"Ошибка загрузки документа: {e}")
        
        # Отправляем email
        logger.info(f"Подключаемся к SMTP серверу {SMTP_SERVER}:{SMTP_PORT}")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.set_debuglevel(1)  # Включаем debug для SMTP
            server.starttls()
            logger.info(f"Логинимся как {EMAIL_USER}")
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"Email успешно отправлен на {recipient_email}")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"Ошибка аутентификации SMTP: {e}")
        logger.error("Проверьте EMAIL_PASSWORD - нужен пароль приложения, а не пароль от почты")
        return False
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
    
    # Инициализируем сессию пользователя
    user_sessions[user_id] = {
        'name': user_name,
        'username': username,
        'started_at': datetime.now()
    }
    
    # Создаем клавиатуру с Web App (только одна кнопка)
    keyboard = types.InlineKeyboardMarkup()
    
    # Кнопка Web App
    webapp_btn = types.InlineKeyboardButton(
        text="Выберите актив",
        web_app=types.WebAppInfo(url=WEBAPP_URL)
    )
    keyboard.add(webapp_btn)
    
    # Обновленный текст приветствия от Сбера
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
        
        # Убираем "часики" с кнопки
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        logger.error(f"Ошибка в callback: {e}")
        bot.answer_callback_query(call.id, "Произошла ошибка")

@bot.message_handler(content_types=['web_app_data'])
def handle_web_app_data(message):
    """Обработка данных от Web App"""
    try:
        # Получаем данные от веб-приложения
        web_app_data = json.loads(message.web_app_data.data)
        action = web_app_data.get('action')
        
        user_id = message.from_user.id
        user_name = message.from_user.first_name or "Пользователь"
        
        logger.info(f"Получены данные от Web App: action={action}, user={user_name}")
        
        if action == 'send_email':
            # Пользователь запросил отправку на email из веб-приложения
            email = web_app_data.get('email')
            asset_type = web_app_data.get('asset_type')
            
            logger.info(f"Запрос на отправку email: {email}, актив: {asset_type}")
            
            if not validate_email(email):
                bot.reply_to(message, "❌ Неверный формат email адреса")
                return
            
            if asset_type not in ASSETS:
                bot.reply_to(message, "❌ Неизвестный тип актива")
                return
            
            # Отправляем документ
            success = send_email_with_document(email, asset_type, user_name)
            
            asset = ASSETS[asset_type]
            
            if success:
                response_text = f"""
✅ **Документы отправлены из веб-каталога!**

📧 **Email:** `{email}`
📄 **Актив:** {asset['icon']} {asset['title']}

📬 Проверьте входящие письма в течение 5 минут.

📄 Нужны документы для другого актива? Откройте каталог снова!
"""
                # Добавляем кнопку для повторного открытия
                keyboard = types.InlineKeyboardMarkup()
                webapp_btn = types.InlineKeyboardButton(
                    "Выберите другой актив", 
                    web_app=types.WebAppInfo(url=WEBAPP_URL)
                )
                keyboard.add(webapp_btn)
                
                bot.reply_to(
                    message, 
                    response_text, 
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
                
                # Логируем для админа
                if ADMIN_CHAT_ID:
                    admin_msg = f"📧 Email из Web App\n👤 {user_name} (@{message.from_user.username})\n📄 {asset['title']}\n📧 {email}"
                    try:
                        bot.send_message(ADMIN_CHAT_ID, admin_msg)
                    except:
                        pass
            else:
                bot.reply_to(
                    message,
                    f"❌ **Ошибка отправки email**\n\n"
                    f"Не удалось отправить документы для {asset['icon']} {asset['title']} на адрес `{email}`.\n\n"
                    f"📄 Попробуйте:\n"
                    f"• Проверить правильность email\n"
                    f"• Повторить попытку через несколько минут\n"
                    f"• Написать нам напрямую: {EMAIL_USER}\n\n"
                    f"💡 Используйте команду /test_email для проверки",
                    parse_mode='Markdown'
                )
        
        elif action == 'download_completed':
            # Пользователь скачал документ из веб-приложения
            asset_type = web_app_data.get('asset_type')
            if asset_type in ASSETS:
                asset = ASSETS[asset_type]
                
                response_text = f"""
✅ **Документ скачан!**

📄 **Актив:** {asset['icon']} {asset['title']}
📂 **Файл:** {asset['filename']}

💡 **Нужна помощь?** Обращайтесь к нашим специалистам!
"""
                
                # Кнопки для дополнительных действий
                keyboard = types.InlineKeyboardMarkup()
                webapp_btn = types.InlineKeyboardButton(
                    "Выбрать другой актив", 
                    web_app=types.WebAppInfo(url=WEBAPP_URL)
                )
                contact_btn = types.InlineKeyboardButton("📞 Контакты", callback_data="contacts")
                keyboard.add(webapp_btn)
                keyboard.add(contact_btn)
                
                bot.reply_to(
                    message, 
                    response_text, 
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
        
    except Exception as e:
        logger.error(f"Ошибка обработки Web App данных: {e}")
        logger.exception("Полный traceback:")
        bot.reply_to(message, "❌ Произошла ошибка при обработке запроса")

@bot.message_handler(commands=['test_email'])
def test_email_command(message):
    """Команда для тестирования отправки email"""
    user_name = message.from_user.first_name or "Тестовый пользователь"
    
    # Проверяем настройки email
    if not EMAIL_USER or not EMAIL_PASSWORD:
        bot.reply_to(message, "❌ Email настройки не заданы в переменных окружения")
        return
    
    # Отправляем тестовое письмо на email администратора
    test_email = EMAIL_USER  # Отправляем на свой же email для теста
    
    bot.reply_to(message, f"🔄 Отправляю тестовое письмо на {test_email}...")
    
    success = send_email_with_document(test_email, 'бизнес-центр', user_name)
    
    if success:
        bot.reply_to(message, "✅ Тестовое письмо успешно отправлено! Проверьте почту.")
    else:
        bot.reply_to(message, "❌ Ошибка отправки. Проверьте логи бота для диагностики.")

@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
    """Обработка текстовых сообщений"""
    user_message = message.text.lower()
    
    # Поиск актива по ключевым словам
    found_assets = []
    for asset_key, asset_data in ASSETS.items():
        if (any(word in user_message for word in asset_key.split('-')) or
            any(word in user_message for word in asset_data['title'].lower().split())):
            found_assets.append((asset_key, asset_data))
    
    if found_assets:
        if len(found_assets) == 1:
            # Найден один актив
            asset_key, asset_data = found_assets[0]
            
            response_text = f"""
{asset_data['icon']} **{asset_data['title']}**

📝 {asset_data['description']}

🎯 **Что хотите сделать?**
"""
            
            keyboard = types.InlineKeyboardMarkup()
            
            # Кнопка Web App для этого актива
            webapp_url_with_asset = f"{WEBAPP_URL}?asset={asset_key}"
            webapp_btn = types.InlineKeyboardButton(
                f"📋 Открыть {asset_data['title']}", 
                web_app=types.WebAppInfo(url=webapp_url_with_asset)
            )
            keyboard.add(webapp_btn)
            
            # Кнопка общего каталога
            catalog_btn = types.InlineKeyboardButton(
                "📚 Весь каталог", 
                web_app=types.WebAppInfo(url=WEBAPP_URL)
            )
            keyboard.add(catalog_btn)
            
        else:
            # Найдено несколько активов
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
        # Актив не найден или общий вопрос
        response_text = f"""
🤖 Понял вас не совсем точно.

📋 **Доступно {len(ASSETS)} типов активов:**
"""
        
        # Показываем первые 4 актива
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
    logger.info("🚀 Запуск Telegram Web App бота 'Доки'")
    logger.info(f"📱 Web App URL: {WEBAPP_URL}")
    logger.info(f"📧 Email: {'✅ Настроен' if EMAIL_USER and EMAIL_PASSWORD else '❌ Не настроен'}")
    logger.info(f"👮 Админ: {'✅ Настроен' if ADMIN_CHAT_ID else '❌ Не настроен'}")
    
    print("=" * 50)
    print("🤖 TELEGRAM WEB APP БОТ 'ДОКИ' ЗАПУЩЕН")
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
    
    # Очищаем webhook и старые обновления перед запуском
    try:
        bot.remove_webhook()
        bot.delete_webhook()
        # Пропускаем накопившиеся обновления
        bot.get_updates(offset=-1)
        logger.info("✅ Webhook очищен, старые обновления пропущены")
    except Exception as e:
        logger.warning(f"Предупреждение при очистке webhook: {e}")
    
    try:
        # Проверяем соединение с Telegram API
        bot_info = bot.get_me()
        print(f"✅ Подключение к Telegram: @{bot_info.username}")
        
        # Запускаем Flask сервер в отдельном потоке
        flask_thread = Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()
        logger.info(f"🌐 HTTP сервер запущен на порту {os.environ.get('PORT', 10000)}")
        
        # Запускаем бота
        logger.info("🤖 Telegram бот запущен и готов к работе")
        bot.polling(none_stop=True, timeout=60, skip_pending=True)
        
    except telebot.apihelper.ApiTelegramException as e:
        if "Conflict" in str(e):
            logger.error("❌ Конфликт: другой экземпляр бота уже запущен")
            logger.error("Остановите другой процесс или подождите 30 секунд")
            import time
            time.sleep(30)
            main()  # Пробуем снова через 30 секунд
        else:
            logger.error(f"Telegram API ошибка: {e}")
            raise
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        
        # Уведомляем админа об ошибке
        if ADMIN_CHAT_ID:
            try:
                bot.send_message(
                    ADMIN_CHAT_ID, 
                    f"🚨 **Критическая ошибка бота:**\n```\n{str(e)}\n```",
                    parse_mode='Markdown'
                )
            except:
                pass
        
        # Пытаемся перезапустить через 5 секунд
        print("⚠️ Попытка перезапуска через 5 секунд...")
        import time
        time.sleep(5)
        main()

if __name__ == '__main__':
    main()
