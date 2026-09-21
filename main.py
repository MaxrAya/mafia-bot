import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from bot import dp, bot, router


async def on_startup():
    print("Mafia Bot started!")


if __name__ == "__main__":
    dp.include_router(router)
    dp.startup.register(on_startup)
    dp.run_polling(bot)
