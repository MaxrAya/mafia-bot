import asyncio
from bot import start_bot, dp, bot


async def on_startup():
    print("🎭 Mafia Bot запущен!")
    print("Бот готов к играм!")


if __name__ == "__main__":
    from aiogram import Dispatcher
    dp.startup.register(on_startup)
    dp.run_polling(bot)
