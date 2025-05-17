import sqlite3
import datetime
import logging
from collections import defaultdict
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TELEGRAM_TOKEN = "7525233908:AAHWcQqjE-BO8BeW66bmhGrwYm6FvWus6lQ"
user_action_counts = defaultdict(int)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

conn = sqlite3.connect("birthdays.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS birthdays (
        user_id INTEGER,
        name TEXT,
        date TEXT
    )
''')
conn.commit()

def detect_gender(name: str) -> str:
    first_name = name.strip().split()[0].lower()
    return 'female' if first_name[-1] in ['а', 'я'] else 'male'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cursor.execute('SELECT COUNT(*) FROM birthdays WHERE user_id = ?', (user_id,))
    count = cursor.fetchone()[0]

    text = ("👋 <b>Привет!</b> Я бот-напоминалка о днях рождениях.\n\n"
            "<b>Напомню тебе:</b>\n"
            "— За день до ДР\n"
            "— В сам день ДР 🎂\n\n"
            "📌 <b>Команды:</b>\n"
            "<code>/add Имя ДД.ММ.ГГГГ</code> — добавить дату рождения\n"
            "<i>Пример:</i> <code>/add Иван Иванов 16.05.1992</code>\n\n"
            "<code>/list</code> — список всех добавленных людей\n"
            "<code>/remove Имя</code> — удалить человека (можно часть имени)\n"
            "<i>Пример:</i> <code>/remove Иван</code>\n\n"
            "<code>/check</code> — кто празднует сегодня\n\n")

    if count == 0:
        text += ("🎈 <b>Всё просто</b> — начни с команды <code>/add</code>, <b>чтобы добавить первую дату.</b>\n"
                 "❤️ Я помогу тебе не забыть самое важное.\n\n"
                 "Не забудь включить звук 🔔 — чтобы получить уведомление!")
    else:
        text += "Не забудь включить звук 🔔 — чтобы получить уведомление!"

    await update.message.reply_text(text, parse_mode="HTML")

async def add_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        name = " ".join(context.args[:-1])
        raw_date = context.args[-1]
        datetime.datetime.strptime(raw_date, "%d.%m.%Y")
        user_id = update.effective_user.id

        cursor.execute('INSERT INTO birthdays (user_id, name, date) VALUES (?, ?, ?)', (user_id, name, raw_date))
        conn.commit()

        cursor.execute('SELECT COUNT(*) FROM birthdays WHERE user_id = ?', (user_id,))
        count = cursor.fetchone()[0]

        gender = detect_gender(name)
        verb = "добавлена" if gender == "female" else "добавлен"
        pronoun = "её" if gender == "female" else "его"

        if count == 1:
            await update.message.reply_text(
                f"""
🎈 <b>Поздравляем!</b> Первый человек успешно добавлен! 🎉\n\n
✅ <b>{name}</b> с датой рождения <b>{raw_date}</b> {verb}.\n\n
📬 Напоминания будут приходить:\n
— За день до {pronoun} дня рождения\n
— В сам день рождения 🎂\n\n
🧾 <code>/list</code> — покажет всех добавленных тобой людей.\n\n
🗑 Чтобы удалить — напиши <code>/remove</code> и имя, фамилию или оба слова.\n
Например: <code>/remove {name.split()[0]}</code>, <code>/remove {name.split()[-1]}</code> или <code>/remove {name}</code>\n\n
❤️ Я напомню вовремя — и никто не останется без поздравлений.
                """,
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text(f"✅ {name} с датой {raw_date} {verb}.", parse_mode="HTML")
            if count % 2 == 1:
                await update.message.reply_text("ℹ️ Введи <code>/list</code> — и я покажу тебе список людей перед днями рождения которых ты уже будешь получать уведомления 🎂", parse_mode="HTML")

        user_action_counts[user_id] += 1
        if user_action_counts[user_id] % 5 == 0:
            await update.message.reply_text("ℹ️ Напоминание: список всех команд — по команде <code>/help</code>", parse_mode="HTML")

    except (IndexError, ValueError):
        await update.message.reply_text("❗ Неверный формат. Пиши: <code>/add Имя ДД.ММ.ГГГГ</code>\nПример: <code>/add Иван Иванов 12.03.1990</code>", parse_mode="HTML")

async def remove_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("❗ Укажи имя человека, которого хочешь удалить из списка напоминаний.\nПример: <code>/remove Иван</code>", parse_mode="HTML")
        return

    keyword = " ".join(context.args).strip().lower()
    cursor.execute('SELECT name FROM birthdays WHERE user_id = ?', (user_id,))
    all_names = cursor.fetchall()
    deleted = []

    for (name,) in all_names:
        if keyword in name.lower():
            cursor.execute('DELETE FROM birthdays WHERE user_id = ? AND name = ?', (user_id, name))
            deleted.append((name, detect_gender(name)))

    conn.commit()

    if not deleted:
        await update.message.reply_text("🙅‍♂️ Совпадений не найдено.", parse_mode="HTML")
    elif len(deleted) == 1:
        gender = deleted[0][1]
        verb = "Удалена" if gender == "female" else "Удалён"
        await update.message.reply_text(f"🗑 {verb}: {deleted[0][0]}", parse_mode="HTML")
    else:
        await update.message.reply_text(f"🗑 Удалены: {', '.join(name for name, _ in deleted)}", parse_mode="HTML")

    user_action_counts[user_id] += 1
    if user_action_counts[user_id] % 5 == 0:
        await update.message.reply_text("ℹ️ Напоминание: список всех команд — по команде <code>/help</code>", parse_mode="HTML")

async def list_birthdays(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cursor.execute('SELECT name, date FROM birthdays WHERE user_id = ?', (user_id,))
    rows = cursor.fetchall()
    if rows:
        reply = "<b>📋 Список добавленных:</b>\n" + "\n".join([f"{name}: {date}" for name, date in rows])
        reply += "\n\n🗑 Чтобы удалить кого-то из списка — напиши команду\n<code>/remove</code> и укажи имя, фамилию или оба слова.\n"

        # Формируем примеры
        examples = []
        for name, _ in rows[:3]:
            parts = name.strip().split()
            if len(parts) == 1:
                examples.append(f"<code>/remove {parts[0]}</code>")
            elif len(parts) >= 2:
                examples.append(f"<code>/remove {parts[0]}</code>")
                examples.append(f"<code>/remove {parts[1]}</code>")
                examples.append(f"<code>/remove {name}</code>")

        reply += "Например: " + ", ".join(examples)
    else:
        reply = "📭 Список пуст. Добавь кого-то через <code>/add</code>"
    await update.message.reply_text(reply, parse_mode="HTML")

async def check_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.datetime.now().strftime("%d.%m")
    cursor.execute('SELECT name, date FROM birthdays')
    rows = cursor.fetchall()
    celebrants = []
    for name, full_date in rows:
        if full_date.startswith(today):
            birth_year = int(full_date.split(".")[-1])
            current_year = datetime.datetime.now().year
            age = current_year - birth_year
            celebrants.append(f"🎉 {name} — {age} лет!")
    if celebrants:
        await update.message.reply_text("Сегодня день рождения у:\n" + "\n".join(celebrants), parse_mode="HTML")
    else:
        await update.message.reply_text("🎈 Сегодня никто не празднует", parse_mode="HTML")

    user_id = update.effective_user.id
    user_action_counts[user_id] += 1
    if user_action_counts[user_id] % 5 == 0:
        await update.message.reply_text("ℹ️ Напоминание: список всех команд — по команде <code>/help</code>", parse_mode="HTML")

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", start))
app.add_handler(CommandHandler("add", add_birthday))
app.add_handler(CommandHandler("remove", remove_birthday))
app.add_handler(CommandHandler("list", list_birthdays))
app.add_handler(CommandHandler("check", check_today))

print("🤖 Бот запущен...")
app.run_polling()
