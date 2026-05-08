
```python
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton
)

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import sqlite3

# =========================
# TOKEN
# =========================
TOKEN = "ВСТАВ_СВІЙ_НОВИЙ_TOKEN"

# =========================
# ADMIN
# =========================
ADMIN_USERNAME = "@buchen_ko"

# =========================
# ФОТО
# Встав сюди свої фото
# =========================
PHOTO_1 = ""
PHOTO_2 = ""
PHOTO_3 = ""

# =========================
# ПОСЛУГИ
# =========================
services = {
    "Манікюр без нарощування": {
        "price": "600 грн",
        "photo": PHOTO_1
    },
    "Манікюр з нарощуванням": {
        "price": "900 грн",
        "photo": PHOTO_2
    },
    "Педикюр": {
        "price": "750 грн",
        "photo": PHOTO_3
    }
}

# =========================
# ЧАС
# =========================
TIME_SLOTS = [
    "10:00",
    "12:00",
    "14:00",
    "16:00"
]

# =========================
# СТАНИ
# =========================
SERVICE, DATE, TIME, NAME, PHONE, CONFIRM = range(6)

# =========================
# БАЗА ДАНИХ
# =========================
conn = sqlite3.connect('appointments.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service TEXT,
    date TEXT,
    time TEXT,
    name TEXT,
    phone TEXT
)
''')

conn.commit()

# =========================
# START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = []

    for service in services:
        keyboard.append([
            InlineKeyboardButton(service, callback_data=service)
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Вітаємо ❤️\nОберіть послугу:",
        reply_markup=reply_markup
    )

    return SERVICE

# =========================
# ВИБІР ПОСЛУГИ
# =========================
async def choose_service(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    service = query.data
    context.user_data['service'] = service

    info = services[service]

    keyboard = [
        [InlineKeyboardButton("Записатись", callback_data="book")],
        [InlineKeyboardButton("Назад", callback_data="back")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if info['photo']:
        await query.message.reply_photo(
            photo=info['photo'],
            caption=f"{service} ❤️\nЦіна: {info['price']}",
            reply_markup=reply_markup
        )
    else:
        await query.message.reply_text(
            f"{service} ❤️\nЦіна: {info['price']}",
            reply_markup=reply_markup
        )

    return DATE

# =========================
# ДАТИ
# =========================
async def choose_date(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.data == "back":
        return await start_again(query, context)

    keyboard = []

    for i in range(7):
        day = datetime.now() + timedelta(days=i)
        formatted = day.strftime("%d.%m.%Y")

        keyboard.append([
            InlineKeyboardButton(formatted, callback_data=formatted)
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(
        "Оберіть дату ❤️",
        reply_markup=reply_markup
    )

    return TIME

# =========================
# ЧАС
# =========================
async def choose_time(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    selected_date = query.data
    context.user_data['date'] = selected_date

    cursor.execute(
        "SELECT time FROM appointments WHERE date = ?",
        (selected_date,)
    )

    booked = [row[0] for row in cursor.fetchall()]

    available = []

    for slot in TIME_SLOTS:
        if slot not in booked:
            available.append(slot)

    if not available:
        await query.message.reply_text(
            "На цей день все зайнято 😔\nОберіть інший день"
        )

        return DATE

    keyboard = []

    for slot in available:
        keyboard.append([
            InlineKeyboardButton(slot, callback_data=slot)
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(
        "Оберіть час ❤️",
        reply_markup=reply_markup
    )

    return NAME

# =========================
# ІМʼЯ
# =========================
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.callback_query:

        query = update.callback_query
        await query.answer()

        context.user_data['time'] = query.data

        await query.message.reply_text(
            "Введіть ім’я та прізвище ❤️"
        )

        return PHONE

# =========================
# ТЕЛЕФОН
# =========================
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data['name'] = update.message.text

    button = KeyboardButton(
        "Надіслати номер",
        request_contact=True
    )

    keyboard = ReplyKeyboardMarkup(
        [[button]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await update.message.reply_text(
        "Надішліть номер телефону ❤️",
        reply_markup=keyboard
    )

    return CONFIRM

# =========================
# ПІДТВЕРДЖЕННЯ
# =========================
async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):

    phone = update.message.contact.phone_number
    context.user_data['phone'] = phone

    service = context.user_data['service']
    date = context.user_data['date']
    time = context.user_data['time']
    name = context.user_data['name']

    text = f"""
Перевірте дані ❤️

Послуга: {service}
Дата: {date}
Час: {time}
Ім’я: {name}
Телефон: {phone}
"""

    keyboard = [
        [InlineKeyboardButton("Підтвердити", callback_data="confirm")],
        [InlineKeyboardButton("Скасувати", callback_data="cancel")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        text,
        reply_markup=reply_markup
    )

    return ConversationHandler.END

# =========================
# ЗБЕРЕЖЕННЯ
# =========================
async def save_appointment(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        await query.message.reply_text("Запис скасовано 😔")
        return

    service = context.user_data['service']
    date = context.user_data['date']
    time = context.user_data['time']
    name = context.user_data['name']
    phone = context.user_data['phone']

    cursor.execute(
        "INSERT INTO appointments (service, date, time, name, phone) VALUES (?, ?, ?, ?, ?)",
        (service, date, time, name, phone)
    )

    conn.commit()

    await query.message.reply_text(
        f"Запис успішно створено ❤️\n\n{date} о {time}"
    )

    admin_message = f"""
Новий запис 🔔

{name}
{phone}

{service}
{date}
{time}
"""

    try:
        await context.bot.send_message(
            chat_id=ADMIN_USERNAME,
            text=admin_message
        )
    except:
        pass

# =========================
# НАЗАД
# =========================
async def start_again(query, context):

    keyboard = []

    for service in services:
        keyboard.append([
            InlineKeyboardButton(service, callback_data=service)
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(
        "Оберіть послугу ❤️",
        reply_markup=reply_markup
    )

    return SERVICE

# =========================
# НАГАДУВАННЯ
# =========================
async def reminders(context: ContextTypes.DEFAULT_TYPE):

    now = datetime.now()
    target = now + timedelta(hours=3)

    date = target.strftime("%d.%m.%Y")
    time = target.strftime("%H:00")

    cursor.execute(
        "SELECT name, phone FROM appointments WHERE date = ? AND time = ?",
        (date, time)
    )

# =========================
# APP
# =========================
app = ApplicationBuilder().token(TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        SERVICE: [CallbackQueryHandler(choose_service)],
        DATE: [CallbackQueryHandler(choose_date)],
        TIME: [CallbackQueryHandler(choose_time)],
        NAME: [CallbackQueryHandler(get_name)],
        PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
        CONFIRM: [MessageHandler(filters.CONTACT, confirm)]
    },
    fallbacks=[]
)

app.add_handler(conv_handler)
app.add_handler(CallbackQueryHandler(save_appointment, pattern="^(confirm|cancel)$"))

scheduler = AsyncIOScheduler()
scheduler.start()

print("Бот запущений ❤️")

app.run_polling()
```
