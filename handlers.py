# bot.py
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode
from aiogram.utils import executor
from config import TOKEN
from db import init_db, add_habit, mark_done, get_stats

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(bot)

# Команда старт
dp.register_message_handler(lambda msg: msg.answer("Готуйся до змін! Додавай звички командою /addhabit Назва"), commands=["start"])

# Додавання звички
@dp.message_handler(commands=["addhabit"])
async def add_habit_command(message: types.Message):
    habit = message.text.replace("/addhabit ", "").strip()
    if not habit:
        await message.reply("Ну ти серйозно? Напиши хоч щось! Наприклад: /addhabit Ранкова зарядка")
        return
    add_habit(message.from_user.id, habit)
    await message.reply(f"Добре. Додав '{habit}'. Не забудь виконати!")

# Відмітити звичку як виконану
@dp.message_handler(commands=["done"])
async def done_command(message: types.Message):
    habit = message.text.replace("/done ", "").strip()
    if not habit:
        await message.reply("Що саме ти зробив? Напиши: /done Ранкова зарядка")
        return
    mark_done(message.from_user.id, habit)
    await message.reply(f"Молодець! '{habit}' відзначено як виконане. Але не розслабляйся!")

# Перегляд статистики
@dp.message_handler(commands=["stats"])
async def stats_command(message: types.Message):
    stats = get_stats(message.from_user.id)
    if not stats:
        await message.reply("Ще немає виконаних звичок. Що, думаєш, все саме зробиться?")
    else:
        stat_text = '\n'.join([f"{habit}: {count} разів" for habit, count in stats])
        await message.reply(f"Ось твоя статистика:\n{stat_text}")

# Запуск бота
if __name__ == "__main__":
    init_db()
    executor.start_polling(dp, skip_updates=True)
