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
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())