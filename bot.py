import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiohttp import web

from config import BOT_TOKEN, ADMIN_ID

logging.basicConfig(level=logging.INFO)

router = Router()

# ---------------- КНОПКИ ----------------

main_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📩 Получать приглашения", callback_data="subscribe")],
    [InlineKeyboardButton(text="⚙️ Мои подписки", callback_data="my_subs")],
    [InlineKeyboardButton(text="💬 Поддержка", callback_data="support")]
])

categories_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⚽ Взрослые", callback_data="cat_adult")],
    [InlineKeyboardButton(text="🧒 До 15", callback_data="cat_15")],
    [InlineKeyboardButton(text="🧑 До 17", callback_data="cat_17")],
    [InlineKeyboardButton(text="🧑‍🦱 До 20", callback_data="cat_20")],
    [InlineKeyboardButton(text="✅ Готово", callback_data="done")]
])

# ---------------- FSM ----------------

class Support(StatesGroup):
    message = State()

# ---------------- ДАННЫЕ ----------------

user_subscriptions = {}
support_map = {}  # связь сообщений (админ -> пользователь)

# ---------------- START ----------------

@router.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "⚽ Привет!\nВыбери, что тебе нужно:",
        reply_markup=main_kb
    )

# ---------------- ПОДПИСКА ----------------

@router.callback_query(F.data == "subscribe")
async def subscribe(callback: CallbackQuery):
    user_subscriptions[callback.from_user.id] = []
    await callback.message.answer("Выбери категории:", reply_markup=categories_kb)
    await callback.answer()


@router.callback_query(F.data.startswith("cat_"))
async def select_category(callback: CallbackQuery):
    user_id = callback.from_user.id

    mapping = {
        "cat_adult": "⚽ Взрослые",
        "cat_15": "🧒 До 15",
        "cat_17": "🧑 До 17",
        "cat_20": "🧑‍🦱 До 20"
    }

    category = mapping.get(callback.data)

    if user_id not in user_subscriptions:
        user_subscriptions[user_id] = []

    if category not in user_subscriptions[user_id]:
        user_subscriptions[user_id].append(category)

    await callback.message.answer(f"Добавлено: {category}")
    await callback.answer()


@router.callback_query(F.data == "done")
async def done(callback: CallbackQuery):
    subs = user_subscriptions.get(callback.from_user.id, [])

    if not subs:
        await callback.message.answer("Ты ничего не выбрал 😅")
    else:
        await callback.message.answer(
            "✅ Подписка:\n" + "\n".join(subs),
            reply_markup=main_kb
        )

    await callback.answer()

# ---------------- МОИ ПОДПИСКИ ----------------

@router.callback_query(F.data == "my_subs")
async def my_subs(callback: CallbackQuery):
    subs = user_subscriptions.get(callback.from_user.id, [])

    if not subs:
        await callback.message.answer("У тебя нет подписок")
    else:
        await callback.message.answer("Твои подписки:\n" + "\n".join(subs))

    await callback.answer()

# ---------------- ПОДДЕРЖКА ----------------

@router.callback_query(F.data == "support")
async def support_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Напиши сообщение:")
    await state.set_state(Support.message)
    await callback.answer()


@router.message(Support.message)
async def support_msg(message: Message, state: FSMContext):
    user = message.from_user

    await message.answer("✅ Сообщение отправлено")

    admin_msg = await message.bot.send_message(
        ADMIN_ID,
        f"💬 Новое сообщение\n\n"
        f"👤 @{user.username}\n"
        f"🆔 {user.id}\n\n"
        f"{message.text}"
    )

    # сохраняем связь (очень важно)
    support_map[admin_msg.message_id] = user.id

    await state.clear()

# ---------------- ОТВЕТ АДМИНА (ЧАТ) ----------------

@router.message()
async def admin_reply(message: Message):
    # только админ
    if message.from_user.id != ADMIN_ID:
        return

    # должен быть ответ на сообщение
    if not message.reply_to_message:
        return

    replied_id = message.reply_to_message.message_id

    if replied_id not in support_map:
        return

    user_id = support_map[replied_id]

    try:
        await message.bot.send_message(user_id, message.text)
        await message.answer("✅ Отправлено")
    except:
        await message.answer("❌ Ошибка отправки")

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