import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram import Router

from config import BOT_TOKEN

logging.basicConfig(level=logging.INFO)

router = Router()

@router.message()
async def echo(message: Message):
    await message.answer("Бот работает ⚽")

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(router)

    print("Бот запущен...")
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import os
from aiohttp import web

async def handle(request):
    return web.Response(text="Bot is running")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)

    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()