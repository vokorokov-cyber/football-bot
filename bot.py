import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, CommandObject
from aiohttp import web

from config import BOT_TOKEN, ADMIN_ID

# 🔥 БАЗА
from db import (
    init_db,
    add_user,
    get_subscriptions,
    toggle_subscription,
    clear_subscriptions,
    get_users_by_categories
)

logging.basicConfig(level=logging.INFO)

router = Router()

# ---------------- КАТЕГОРИИ ----------------

CATEGORIES = {
    "adult": "⚽ Взрослые",
    "u15": "🧒 До 15",
    "u17": "🧑 До 17",
    "u20": "🧑‍🦱 До 20",
}

# ---------------- SUPPORT MAP ----------------

support_map = {}

# ---------------- FSM ----------------

class Support(StatesGroup):
    message = State()

# ---------------- UI ----------------

def main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📩 Подписки", callback_data="subs")],
        [InlineKeyboardButton(text="⚙️ Мои подписки", callback_data="my_subs")],
        [InlineKeyboardButton(text="💬 Поддержка", callback_data="support")]
    ])


async def categories_kb(user_id: int):
    subs = await get_subscriptions(user_id)

    rows = []

    for key, label in CATEGORIES.items():
        prefix = "✅ " if key in subs else ""
        rows.append([
            InlineKeyboardButton(
                text=prefix + label,
                callback_data=f"toggle:{key}"
            )
        ])

    rows.append([InlineKeyboardButton(text="✔️ Готово", callback_data="done")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def manage_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить", callback_data="subs")],
        [InlineKeyboardButton(text="🚫 Отписаться от всего", callback_data="unsub_all")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
    ])

# ---------------- START ----------------

@router.message(Command("start"))
async def start(message: Message):
    await add_user(message.from_user.id)

    await message.answer(
        "⚽ Добро пожаловать!\nВыбери действие:",
        reply_markup=main_kb()
    )

# ---------------- ПОДПИСКА ----------------

@router.callback_query(F.data == "subs")
async def subs(callback: CallbackQuery):
    kb = await categories_kb(callback.from_user.id)

    await callback.message.edit_text(
        "Выбери категории турниров:",
        reply_markup=kb
    )
    await callback.answer()


@router.callback_query(F.data.startswith("toggle:"))
async def toggle_category(callback: CallbackQuery):
    user_id = callback.from_user.id
    key = callback.data.split(":")[1]

    await toggle_subscription(user_id, key)

    kb = await categories_kb(user_id)

    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "done")
async def done(callback: CallbackQuery):
    subs = await get_subscriptions(callback.from_user.id)

    if not subs:
        text = "Ты пока не подписан ни на одну категорию"
    else:
        text = "✅ Твои подписки:\n\n" + "\n".join(CATEGORIES[s] for s in subs)

    await callback.message.edit_text(text, reply_markup=main_kb())
    await callback.answer()

# ---------------- МОИ ПОДПИСКИ ----------------

@router.callback_query(F.data == "my_subs")
async def my_subs(callback: CallbackQuery):
    subs = await get_subscriptions(callback.from_user.id)

    if not subs:
        text = "У тебя нет подписок"
    else:
        text = "Твои подписки:\n\n" + "\n".join(CATEGORIES[s] for s in subs)

    await callback.message.edit_text(text, reply_markup=manage_kb())
    await callback.answer()

# ---------------- ОТПИСКА ----------------

@router.callback_query(F.data == "unsub_all")
async def unsub_all(callback: CallbackQuery):
    await clear_subscriptions(callback.from_user.id)

    await callback.message.edit_text(
        "🚫 Ты отписался от всех категорий",
        reply_markup=main_kb()
    )
    await callback.answer()

# ---------------- НАВИГАЦИЯ ----------------

@router.callback_query(F.data == "back")
async def back(callback: CallbackQuery):
    await callback.message.edit_text(
        "Главное меню:",
        reply_markup=main_kb()
    )
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

    await message.answer("✅ Отправлено")

    admin_msg = await message.bot.send_message(
        ADMIN_ID,
        f"💬 Сообщение\n\n"
        f"👤 @{user.username}\n"
        f"🆔 {user.id}\n\n"
        f"{message.text}"
    )

    support_map[admin_msg.message_id] = user.id

    await state.clear()

# ---------------- ОТВЕТ КАК ЧАТ ----------------

@router.message()
async def admin_reply(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    if not message.reply_to_message:
        return

    replied_id = message.reply_to_message.message_id

    if replied_id not in support_map:
        return

    user_id = support_map[replied_id]

    await message.bot.send_message(user_id, message.text)

# ---------------- РАССЫЛКА ----------------

@router.message(Command("send"))
async def send_broadcast(message: Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID:
        return

    args = command.args

    if not args:
        await message.answer("Формат: /send категории текст")
        return

    try:
        parts = args.split(" ", 1)
        categories = parts[0].split(",")
        text = parts[1]
    except:
        await message.answer("Ошибка формата")
        return

    valid = [c for c in categories if c in CATEGORIES]

    if not valid:
        await message.answer(f"Нет валидных категорий\nДоступно: {list(CATEGORIES.keys())}")
        return

    users = await get_users_by_categories(valid)

    print("CATEGORIES:", valid)
    print("USERS:", users)

    if not users:
        await message.answer("❌ Нет пользователей для рассылки")
        return

    sent = 0
    failed = 0

    await message.answer(f"🚀 Рассылка: {len(users)} пользователей")

    for user_id in users:
        try:
            await message.bot.send_message(user_id, text)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            print("ERROR:", e)
            failed += 1

    await message.answer(
        f"✅ Готово\n\n"
        f"Отправлено: {sent}\n"
        f"Ошибки: {failed}"
    )

# ---------------- WEB SERVER ----------------

async def handle(request):
    return web.Response(text="OK")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)

    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# ---------------- MAIN ----------------

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(router)

    await init_db()

    print("Бот запущен")

    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())