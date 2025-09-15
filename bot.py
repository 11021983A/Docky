# Получаем настройки
BOT_TOKEN = os.getenv('BOT_TOKEN', '8222086470:AAGCqPq0T7hFU0E0Mf7yoP39Wtc-OPqI_qA')
WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://11021983a.github.io/docs-bank-webapp/')
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.mail.ru')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
EMAIL_USER = os.getenv('EMAIL_USER', 'docs_zs@mail.ru')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')import os
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

# Получаем настройки
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://yourusername.github.io/docs-bank-app/')
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.mail.ru')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
EMAIL_USER = os.getenv('EMAIL_USER', 'docs_zs@mail.ru')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')

if not BOT_TOKEN:
    print("❌ ОШИБКА: Не найден BOT_TOKEN в файле .env")
    exit()

# Создаем бота
bot = telebot.TeleBot(BOT_TOKEN)

# Хранилище для пользователей (в памяти для простоты)
user_sessions = {}

# Данные об активах (синхронизировано с веб-приложением)
ASSETS = {
    'бизнес-центр': {
        'icon': '🏢',
        'title': 'Бизнес-центр',
        'description': 'Офисные здания и бизнес-центры',
        'documents': 15,
        'processing': '7-10 дней',
        'filename': 'бизнес-центр.pdf'
    },
    'торговый-центр': {
        'icon': '🛍️',
        'title': 'Торговый центр',
        'description': 'Торговые центры и комплексы',
        'documents': 18,
        'processing': '10-14 дней',
        'filename': 'торговый-центр.pdf'
    },
    'складской-комплекс': {
        'icon': '📦',
        'title': 'Складской комплекс',
        'description': 'Складские помещения и комплексы',
        'documents': 12,
        'processing': '5-7 дней',
        'filename': 'складской-комплекс.pdf'
    },
    'гостиница': {
        'icon': '🏨',
        'title': 'Гостиница',
        'description': 'Гостиничные комплексы',
        'documents': 20,
        'processing': '14-21 день',
        'filename': 'гостиница.pdf'
    },
    'бизнес': {
        'icon': '💼',
        'title': 'Бизнес',
        'description': 'Доли в бизнесе и акции',
        'documents': 25,
        'processing': '21-30 дней',
        'filename': 'бизнес.pdf'
    },
    'комплекс-имущества': {
        'icon': '🏗️',
        'title': 'Комплекс имущества',
        'description': 'Имущественные комплексы',
        'documents': 22,
        'processing': '14-21 день',
        'filename': 'комплекс-имущества.pdf'
    },
    'машины-и-оборудование': {
        'icon': '⚙️',
        'title': 'Машины и оборудование',
        'description': 'Промышленное оборудование',
        'documents': 16,
        'processing': '7-14 дней',
        'filename': 'машины-и-оборудование.pdf'
    },
    'имущественные-права-на-жилье': {
        'icon': '🏠',
        'title': 'ИПС на жилье',
        'description': 'Права на жилую недвижимость',
        'documents': 14,
        'processing': '10-14 дней',
        'filename': 'имущественные-права-на-жилье.pdf'
    }
}

def validate_email(email: str) -> bool:
    """Валидация email адреса"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def send_email_with_document(recipient_email: str, asset_type: str, user_name: str) -> bool:
    """Отправка email с документом через Mail.ru"""
    if not EMAIL_USER or not EMAIL_PASSWORD:
        logger.warning("Email настройки не заданы")
        return False
    
    try:
        asset = ASSETS.get(asset_type)
        if not asset:
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
                        <li><strong>Количество документов:</strong> {asset['documents']}</li>
                        <li><strong>Время обработки:</strong> {asset['processing']}</li>
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
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"Email успешно отправлен на {recipient_email}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка отправки email: {e}")
        return False

@bot.message_handler(commands=['start'])
def start_command(message):
    """Стартовое сообщение с Web App"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    # Инициализируем сессию пользователя
    user_sessions[user_id] = {
        'name': user_name,
        'username': message.from_user.username,
        'started_at': datetime.now()
    }
    
    # Создаем клавиатуру с Web App
    keyboard = types.InlineKeyboardMarkup()
    
    # Кнопка Web App
    webapp_btn = types.InlineKeyboardButton(
        text="📋 Открыть каталог документов",
        web_app=types.WebAppInfo(url=WEBAPP_URL)
    )
    keyboard.add(webapp_btn)
    
    # Дополнительные кнопки
    help_btn = types.InlineKeyboardButton("ℹ️ Справка", callback_data="help")
    contact_btn = types.InlineKeyboardButton("📞 Контакты", callback_data="contacts")
    keyboard.add(help_btn, contact_btn)
    
    welcome_text = f"""
🤖 Привет, {user_name}! Меня зовут **Доки**!

📋 Я помогаю с документами для залоговой службы банка.

🚀 **Что я умею:**
• Показать каталог всех документов
• Отправить документы на email  
• Дать подробную информацию по каждому активу
• Ответить на вопросы

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
• `/email [адрес]` - Быстрая отправка на email

**Веб-приложение:** {WEBAPP_URL}

💡 **Совет:** Используйте веб-каталог для быстрого выбора и скачивания документов!
"""
    
    keyboard = types.InlineKeyboardMarkup()
    webapp_btn = types.InlineKeyboardButton(
        "📋 Открыть каталог", 
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
        "📋 Открыть каталог", 
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

@bot.message_handler(commands=['email'])
def quick_email_command(message):
    """Быстрая команда для отправки на email"""
    try:
        # Парсим команду /email user@example.com актив
        parts = message.text.split()
        
        if len(parts) < 2:
            bot.reply_to(
                message, 
                "📧 Использование: `/email ваш@email.ru актив`\n\n"
                "Пример: `/email ivan@mail.ru бизнес-центр`\n\n"
                "Или откройте веб-каталог для удобного выбора ⬇️"
            )
            
            keyboard = types.InlineKeyboardMarkup()
            webapp_btn = types.InlineKeyboardButton(
                "📋 Открыть каталог", 
                web_app=types.WebAppInfo(url=WEBAPP_URL)
            )
            keyboard.add(webapp_btn)
            
            bot.send_message(
                message.chat.id,
                "📱 Рекомендуем использовать веб-каталог:",
                reply_markup=keyboard
            )
            return
        
        email = parts[1]
        asset_query = ' '.join(parts[2:]) if len(parts) > 2 else ''
        
        if not validate_email(email):
            bot.reply_to(message, "❌ Неверный формат email адреса")
            return
        
        # Если указан актив, ищем его
        if asset_query:
            found_asset = None
            asset_query = asset_query.lower()
            
            for asset_key, asset_data in ASSETS.items():
                if (asset_query in asset_key.lower() or 
                    asset_query in asset_data['title'].lower()):
                    found_asset = asset_key
                    break
            
            if found_asset:
                # Отправляем документ
                user_name = message.from_user.first_name
                success = send_email_with_document(email, found_asset, user_name)
                
                if success:
                    asset = ASSETS[found_asset]
                    success_text = f"""
✅ **Документы отправлены!**

📧 **Email:** `{email}`
📄 **Актив:** {asset['icon']} {asset['title']}

📬 Проверьте входящие письма в течение 5 минут.
"""
                    bot.reply_to(message, success_text, parse_mode='Markdown')
                    
                    # Логируем для админа
                    if ADMIN_CHAT_ID:
                        admin_msg = f"📧 Документы отправлены\n👤 {user_name}\n📄 {asset['title']}\n📧 {email}"
                        try:
                            bot.send_message(ADMIN_CHAT_ID, admin_msg)
                        except:
                            pass
                else:
                    bot.reply_to(
                        message, 
                        "❌ Ошибка отправки email. Попробуйте позже или используйте веб-каталог."
                    )
            else:
                # Актив не найден, показываем список
                assets_list = '\n'.join([f"• {data['title']}" for data in ASSETS.values()])
                bot.reply_to(
                    message,
                    f"❓ Актив '{asset_query}' не найден.\n\n"
                    f"**Доступные активы:**\n{assets_list}\n\n"
                    "Или откройте веб-каталог для удобного выбора:"
                )
        else:
            # Актив не указан, показываем веб-каталог
            keyboard = types.InlineKeyboardMarkup()
            webapp_btn = types.InlineKeyboardButton(
                "📋 Выбрать в каталоге", 
                web_app=types.WebAppInfo(url=WEBAPP_URL)
            )
            keyboard.add(webapp_btn)
            
            bot.reply_to(
                message,
                f"📧 Email `{email}` сохранен.\n\nВыберите актив в веб-каталоге:",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Ошибка в quick_email_command: {e}")
        bot.reply_to(message, "❌ Произошла ошибка. Попробуйте использовать веб-каталог.")

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
        user_name = message.from_user.first_name
        
        if action == 'send_email':
            # Пользователь запросил отправку на email из веб-приложения
            email = web_app_data.get('email')
            asset_type = web_app_data.get('asset_type')
            
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

🔄 Нужны документы для другого актива? Откройте каталог снова!
"""
                # Добавляем кнопку для повторного открытия
                keyboard = types.InlineKeyboardMarkup()
                webapp_btn = types.InlineKeyboardButton(
                    "📋 Открыть каталог снова", 
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
                    f"🔄 Попробуйте:\n"
                    f"• Проверить правильность email\n"
                    f"• Повторить попытку через несколько минут\n"
                    f"• Написать нам напрямую: {EMAIL_USER}",
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
                    "📋 Выбрать другой актив", 
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
                
        elif action == 'need_help':
            # Пользователь запросил помощь из веб-приложения
            help_text = """
🆘 **Нужна помощь?**

📞 **Свяжитесь с нами:**
📧 Email: docs_zs@mail.ru
📱 WhatsApp: +7 (XXX) XXX-XX-XX

⏰ **Время работы:** Пн-Пт 9:00-18:00

💬 **Или опишите вашу проблему здесь** - наши специалисты ответят в ближайшее время!
"""
            
            keyboard = types.InlineKeyboardMarkup()
            email_btn = types.InlineKeyboardButton(
                "📧 Написать на почту", 
                url=f"mailto:{EMAIL_USER}?subject=Помощь с документами"
            )
            keyboard.add(email_btn)
            
            bot.reply_to(
                message, 
                help_text, 
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        
    except Exception as e:
        logger.error(f"Ошибка обработки Web App данных: {e}")
        bot.reply_to(message, "❌ Произошла ошибка при обработке запроса")

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
📄 Документов: {asset_data['documents']}
⏱️ Время обработки: {asset_data['processing']}

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
                "📋 Открыть каталог", 
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
            "📋 Открыть каталог документов", 
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
    print(f"🔧 Функции:")
    print("   ✅ Telegram Web App интеграция")
    print("   ✅ Отправка email через Mail.ru")
    print("   ✅ Автоматическое прикрепление PDF")
    print("   ✅ Поиск активов по ключевым словам")
    print("   ✅ Обработка данных от веб-приложения")
    print("=" * 50)
    
    try:
        # Проверяем соединение с Telegram API
        bot_info = bot.get_me()
        print(f"✅ Подключение к Telegram: @{bot_info.username}")
        
        # Запускаем бота
        bot.polling(none_stop=True, timeout=60)
        
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

if __name__ == '__main__':
    main()
