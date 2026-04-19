import asyncio
import logging

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
class Support(StatesGroup):
    message = State()
from aiogram.fsm.context import FSMContext

from config import BOT_TOKEN

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📩 Получать приглашения")],
        [KeyboardButton(text="⚙️ Мои подписки")],
        [KeyboardButton(text="💬 Поддержка и обратная связь")]
    ],
    resize_keyboard=True
)

categories_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⚽ Взрослые")],
        [KeyboardButton(text="🧒 До 15")],
        [KeyboardButton(text="🧑 До 17")],
        [KeyboardButton(text="🧑‍🦱 До 20")],
        [KeyboardButton(text="✅ Готово")]
    ],
    resize_keyboard=True
)

user_subscriptions = {}

logging.basicConfig(level=logging.INFO)

router = Router()

@router.message()
async def echo(message: Message):
    await message.answer("Бот работает ⚽")

@router.message(F.text == "/start")
async def start(message: Message):
    await message.answer(
        "⚽ Привет!\nВыбери, что тебе нужно:",
        reply_markup=main_kb
    )

@router.message(F.text == "📩 Получать приглашения")
async def subscribe(message: Message):
    user_subscriptions[message.from_user.id] = []
    await message.answer(
        "Выбери категории турниров:",
        reply_markup=categories_kb
    )

@router.message(F.text.in_(["⚽ Взрослые", "🧒 До 15", "🧑 До 17", "🧑‍🦱 До 20"]))
async def select_category(message: Message):
    user_id = message.from_user.id

    if user_id not in user_subscriptions:
        user_subscriptions[user_id] = []

    if message.text not in user_subscriptions[user_id]:
        user_subscriptions[user_id].append(message.text)

    await message.answer(f"Добавлено: {message.text}")

@router.message(F.text == "✅ Готово")
async def finish_subscribe(message: Message):
    subs = user_subscriptions.get(message.from_user.id, [])

    if not subs:
        await message.answer("Ты ничего не выбрал 😅")
        return

    await message.answer(
        "✅ Подписка сохранена:\n" + "\n".join(subs),
        reply_markup=main_kb
    )


@router.message(F.text == "⚙️ Мои подписки")
async def my_subs(message: Message):
    subs = user_subscriptions.get(message.from_user.id, [])

    if not subs:
        await message.answer("У тебя пока нет подписок")
    else:
        await message.answer("Твои подписки:\n" + "\n".join(subs))









@router.message(F.text == "💬 Поддержка и обратная связь")
async def support_start(message: Message, state: FSMContext):
    await message.answer("Напиши свой вопрос или сообщение:")
    await state.set_state(Support.message)

@router.message(Support.message)
async def support_message(message: Message, state: FSMContext):
    user = message.from_user

    await message.answer("✅ Сообщение отправлено")

    await message.bot.send_message(
        ADMIN_ID,
        f"💬 Сообщение от пользователя\n\n"
        f"👤 @{user.username}\n"
        f"ID: {user.id}\n\n"
        f"{message.text}"
    )

    await state.clear()


import asyncio
import os
from aiohttp import web

class Support(StatesGroup):
    message = State()

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

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(router)

    print("Бот запущен...")
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

