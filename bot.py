from pyrogram import Client, idle
from config import API_ID, API_HASH, BOT_TOKEN
import asyncio
from aiohttp import web
from pyrogram import utils as pyroutils

pyroutils.MIN_CHAT_ID = -999999999999
pyroutils.MIN_CHANNEL_ID = -100999999999999


class Bot(Client):
    def __init__(self):
        super().__init__(
            "techvj_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            #plugins=dict(root="TechVJ"),
            workers=150,
            sleep_threshold=5
        )

    async def start(self):
        await super().start()
        print("🤖 Bot Started Successfully")

    async def stop(self, *args):
        await super().stop()
        print("👋 Bot Stopped")


async def handle(request):
    return web.Response(text="Bot is alive ✅")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    print("🌐 Web server running on port 8080")


async def main():
    bot = Bot()

    print("Starting Services...")
    await bot.start()

    asyncio.create_task(start_web_server())

    print("All services running ✔")

    await idle()   # <-- FIXED FOR PYROGRAM V2

    await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
