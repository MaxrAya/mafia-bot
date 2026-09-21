import sys
import io
import os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from bot import dp, bot, router


async def on_startup():
    print("Mafia Bot started!")


if __name__ == "__main__":
    token = os.environ.get("BOT_TOKEN", "")
    if not token:
        print("ERROR: BOT_TOKEN env var is not set!")
        print("Set it in Railway -> Variables -> BOT_TOKEN")
        sys.exit(1)

    dp.include_router(router)
    dp.startup.register(on_startup)
    dp.run_polling(bot)
