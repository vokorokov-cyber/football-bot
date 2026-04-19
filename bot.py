import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiohttp import web

from config import BOT_TOKEN, ADMIN_ID

logging.basicConfig(level=logging.INFO)

router = Router()


# ---------------- КЛАВИАТУРЫ ----------------

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📩 Получать приглашения")],
        [KeyboardButton(text="⚙️ Мои подписки")],
        [KeyboardButton(text="💬 Поддержка и обратная связь")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False,
    input_field_placeholder="Выбери действие 👇"
)

categories_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⚽ Взрослые")],
        [KeyboardButton(text="🧒 До 15")],
        [KeyboardButton(text="🧑 До 17")],
        [KeyboardButton(text="🧑‍🦱 До 20")],
        [KeyboardButton(text="✅ Готово")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)


# ---------------- FSM ----------------

class Support(StatesGroup):
    message = State()


# ---------------- ВРЕМЕННОЕ ХРАНЕНИЕ ----------------

user_subscriptions = {}


# ---------------- START ----------------

@router.message(Command("start"))
async def start(message: Message):
    await message.answer("⚽ Привет!")
    await message.answer(
        "Выбери, что тебе нужно:",
        reply_markup=main_kb
    )


# ---------------- ПОДПИСКА ----------------

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


# ---------------- МОИ ПОДПИСКИ ----------------

@router.message(F.text == "⚙️ Мои подписки")
async def my_subs(message: Message):
    subs = user_subscriptions.get(message.from_user.id, [])

    if not subs:
        await message.answer("У тебя пока нет подписок")
    else:
        await message.answer("Твои подписки:\n" + "\n".join(subs))


# ---------------- ПОДДЕРЖКА ----------------

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


# ---------------- DEBUG (гарантирует кнопки) ----------------

@router.message()
async def fallback(message: Message):
    await message.answer(
        "👇 Используй кнопки ниже",
        reply_markup=main_kb
    )


# ---------------- WEB SERVER ----------------

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


# ---------------- ЗАПУСК ----------------

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(router)

    print("Бот запущен...")

    await start_web_server()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())