import logging
import asyncio
import json
import re
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Налаштування логування
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = "7829682977:AAE_b4K_jrt7OqskOzdhlaZknEEjTYcqIgA"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Стан для керування режимами бота
class TaskState(StatesGroup):
    waiting_for_task = State()
    waiting_for_deletion = State()

# Збереження задач у файлі
TASKS_FILE = "tasks.json"

def load_tasks():
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return []

def save_tasks(tasks):
    with open(TASKS_FILE, "w", encoding="utf-8") as file:
        json.dump(tasks, file, ensure_ascii=False, indent=4)

def parse_time(text):
    match = re.search(r"(\d{1,2}):(\d{2})", text)
    if match:
        hour, minute = map(int, match.groups())
        now = datetime.now()
        task_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if task_time < now:
            task_time += timedelta(days=1)
        return task_time
    return None

async def reminder():
    while True:
        tasks = load_tasks()
        now = datetime.now().strftime("%H:%M")
        for task in tasks[:]:
            if "time" in task and task["time"] == now:
                chat_id = task["chat_id"]
                await bot.send_message(chat_id, f"⏰ Нагадування: {task['text']}")
                tasks.remove(task)
                save_tasks(tasks)
        await asyncio.sleep(60)

async def clear_chat():
    while True:
        now = datetime.now()
        if now.hour == 0 and now.minute == 0:
            tasks = load_tasks()
            tasks.clear()
            save_tasks(tasks)
            logger.info("Список задач очищено автоматично о 00:00")
        await asyncio.sleep(60)

# Створюємо клавіатуру
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Додати"), KeyboardButton(text="❌ Видалити")],
        [KeyboardButton(text="📜 Список"), KeyboardButton(text="🧹 Очистити чат")]
    ],
    resize_keyboard=True
)


@dp.message(CommandStart())
async def start_handler(message: types.Message, state: FSMContext):
    await state.clear()
    logger.info(f"Користувач {message.from_user.id} почав взаємодію з ботом.")

    # Текст із описом бота
    intro_text = (
        "🤖 *Вас вітає бот для управління завданнями!*\n\n"
        "📌 *Що вміє цей бот?*\n"
        "✅ ➕ Додавати завдання у зручному форматі (з часом або без)\n"
        "✅ ❌ Видаляти окремі завдання або всі одразу\n"
        "✅ 📜 Переглядати список поточних завдань\n"
        "✅ 🧹 Очищати історію чату для зручності\n"
        "✅ ⏰ Нагадувати про завдання у встановлений час\n\n"
        "⚡ *Щоб розпочати – скористайтеся кнопками нижче!*"
    )

    # Надсилаємо користувачу опис бота перед вибором дій
    await message.answer(intro_text, parse_mode="Markdown")
    await message.answer("⬇️ Оберіть дію:", reply_markup=keyboard)


@dp.message(F.text == "➕ Додати")
async def add_task(message: types.Message, state: FSMContext):
    await state.set_state(TaskState.waiting_for_task)
    await message.answer("Введіть нову задачу у форматі: '10:30 Вийти за хлібом'")

@dp.message(TaskState.waiting_for_task)
async def process_new_task(message: types.Message, state: FSMContext):
    time = parse_time(message.text)
    text = re.sub(r"\d{1,2}:\d{2}", "", message.text).strip()
    tasks = load_tasks()
    task_entry = {"chat_id": message.chat.id, "text": text, "time": time.strftime("%H:%M") if time else None}
    tasks.append(task_entry)
    save_tasks(tasks)
    await state.clear()
    response = f"✅ Задача додана: {text}"
    if time:
        response += f" на {time.strftime('%H:%M')}"
    await message.answer(response + "\n\nВиберіть наступну дію:", reply_markup=keyboard)

@dp.message(F.text == "❌ Видалити")
async def delete_options(message: types.Message, state: FSMContext):
    await state.clear()
    tasks = load_tasks()
    if not tasks:
        await message.answer("❌ Список задач порожній.")
        return

    inline_keyboard = [
        [InlineKeyboardButton(text=f"❌ {task['text']}", callback_data=f"delete_task_{i}")]
        for i, task in enumerate(tasks)
    ]
    inline_keyboard.append([InlineKeyboardButton(text="🗑 Видалити все", callback_data="delete_all")])
    markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

    await message.answer("Виберіть задачу для видалення:", reply_markup=markup)

@dp.callback_query(F.data.startswith("delete_task_"))
async def delete_task_callback(query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    task_index = int(query.data.split("_")[2])
    tasks = load_tasks()

    if 0 <= task_index < len(tasks):
        deleted_task = tasks.pop(task_index)
        save_tasks(tasks)
        logger.info(f"Користувач {query.from_user.id} видалив задачу: {deleted_task['text']}")

        await query.message.delete()  # Видаляємо вікно видалення
        await query.message.answer("✅ Задача видалена!\n\nВиберіть наступну дію:", reply_markup=keyboard)
    else:
        await query.answer("⚠️ Невірний вибір.")


@dp.callback_query(F.data == "delete_all")
async def delete_all_tasks(query: types.CallbackQuery, state: FSMContext):
    await state.clear()

    # Очищаємо задачі
    save_tasks([])
    logger.info(f"Користувач {query.from_user.id} видалив усі задачі.")

    await query.message.delete()  # Видаляємо вікно видалення
    await query.message.answer("🗑 Всі задачі видалені!\n\nВиберіть наступну дію:", reply_markup=keyboard)
    await query.answer("✅ Всі задачі успішно видалено.")

    # Завантажуємо задачі
    tasks = load_tasks()

    if not tasks:
        await query.answer("✅ Немає задач для видалення.", show_alert=True)
        return

    # Очищаємо всі задачі
    save_tasks([])
    logger.info(f"Користувач {query.from_user.id} видалив усі задачі.")

    # Редагуємо повідомлення, щоб показати зміни
    await query.message.edit_text("🗑 Всі задачі видалені.\n\nВиберіть наступну дію:", reply_markup=keyboard)
    await query.answer("✅ Всі задачі успішно видалено.")


@dp.message(F.text == "📜 Список")
async def show_tasks(message: types.Message, state: FSMContext):
    await state.clear()
    tasks = load_tasks()
    if tasks:
        task_list = "\n".join([f"{i+1}. {task['text']} ({task['time'] if task['time'] else 'без часу'})" for i, task in enumerate(tasks)])
        await message.answer(f"📋 Ваші задачі:\n{task_list}\n\nВиберіть наступну дію:", reply_markup=keyboard)
    else:
        await message.answer("📭 У вас немає задач. Виберіть наступну дію:", reply_markup=keyboard)

@dp.message(F.text == "🧹 Очистити чат")
async def clear_chat_history(message: types.Message):
    chat_id = message.chat.id
    await message.answer("🧹 Очищення чату...")

    try:
        last_message_id = message.message_id  # Отримуємо ID останнього повідомлення

        # Видаляємо останні 50 повідомлень у чаті
        for message_id in range(last_message_id, last_message_id - 50, -1):
            try:
                await bot.delete_message(chat_id, message_id)
                await asyncio.sleep(0.1)  # Запобігає rate limit у Telegram
            except Exception as e:
                logger.warning(f"Не вдалося видалити повідомлення {message_id}: {e}")

        await message.answer("🧹 Чат очищено. Виберіть наступну дію:", reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Помилка під час очищення чату: {e}")
        await message.answer("⚠️ Не вдалося очистити чат. Можливо, немає повідомлень для видалення.")

async def main():
    logger.info("Бот запущено.")
    asyncio.create_task(reminder())
    asyncio.create_task(clear_chat())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
