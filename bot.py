# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

from pyrogram import Client, idle
from config import API_ID, API_HASH, BOT_TOKEN, STRING_SESSION, LOGIN_SYSTEM
import asyncio
from aiohttp import web

# Create clients but don't start them yet
if STRING_SESSION is not None and LOGIN_SYSTEM == False:
    TechVJUser = Client(
        "TechVJ",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=STRING_SESSION
    )
else:
    TechVJUser = None


class Bot(Client):
    def __init__(self):
        super().__init__(
            "techvj login",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins=dict(root="TechVJ"),
            workers=150,
            sleep_threshold=5
        )

    async def start(self):
        await super().start()
        print('Bot Started ✅ Powered By @VJ_Botz')

    async def stop(self, *args):
        await super().stop()
        print('Bot Stopped 👋')


# Simple web server for hosting (port 8080)
async def handle(request):
    return web.Response(text="Bot is alive ✅")

async def run_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    print("Web server running on port 8080 🌐")


async def main():
    bot = Bot()
    await bot.start()

    if TechVJUser is not None:
        await TechVJUser.start()
        print("User Client Started ✅")

    # Start web server
    asyncio.create_task(run_web_server())

    await idle()  # Keeps both running

    await bot.stop()
    if TechVJUser is not None:
        await TechVJUser.stop()

if __name__ == "__main__":
    asyncio.run(main())
