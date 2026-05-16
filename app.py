import asyncio
import json
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import aiohttp

# ========== ТВОЙ ТОКЕН ==========
BOT_TOKEN = "8684547044:AAGVVDzmha4RlCLKgk_dI-DPecb20JbgFRo"
# ================================

ADMIN_GROUP_ID = -1003959266816
ADMIN_IDS = [6209172297, 1852789843]

# ========== ССЫЛКА НА GOOGLE APPS SCRIPT ==========
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwdGC0z9K2RGxGAthSeomA3ozju_tRk615IShqWNgL6gDjZ0LOcKGXlPSe2NR02QDaH/exec"
# ===================================================

CHANNEL_LINK = "https://t.me/agshopi"

ORDERS_FILE = "orders.json"
USERS_FILE = "users.json"
REFERRALS_FILE = "referrals.json"

def load_orders():
    if os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, "r") as f:
            return json.load(f)
    return []

def save_orders(orders):
    with open(ORDERS_FILE, "w") as f:
        json.dump(orders, f, indent=4, ensure_ascii=False)

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4, ensure_ascii=False)

def load_referrals():
    if os.path.exists(REFERRALS_FILE):
        with open(REFERRALS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_referrals(refs):
    with open(REFERRALS_FILE, "w") as f:
        json.dump(refs, f, indent=4, ensure_ascii=False)

def get_next_order_number(user_id):
    users = load_users()
    user_id_str = str(user_id)
    if user_id_str not in users:
        users[user_id_str] = {"order_counter": 0, "bonus_balance": 0}
    users[user_id_str]["order_counter"] += 1
    save_users(users)
    return users[user_id_str]["order_counter"]

def update_order_status(order_id, status):
    orders = load_orders()
    for order in orders:
        if order.get("order_id") == order_id:
            order["status"] = status
            order["status_updated_at"] = datetime.now().isoformat()
            save_orders(orders)
            return True
    return False

def get_order_by_id(order_id):
    orders = load_orders()
    for order in orders:
        if order.get("order_id") == order_id:
            return order
    return None

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class OrderForm(StatesGroup):
    game = State()
    item = State()
    photo = State()
    quantity = State()
    username = State()
    promo = State()
    use_bonus = State()

class AddPromo(StatesGroup):
    code = State()
    limit = State()
    discount = State()

class AddBonus(StatesGroup):
    user_id = State()
    amount = State()

async def check_promo_google(promo_code):
    async with aiohttp.ClientSession() as session:
        try:
            payload = {"action": "check", "promoCode": promo_code.upper()}
            async with session.post(GOOGLE_SCRIPT_URL, json=payload) as resp:
                result = await resp.json()
                return result.get("valid", False), result.get("discount", 0)
        except:
            return False, 0

async def use_promo_google(promo_code):
    async with aiohttp.ClientSession() as session:
        try:
            payload = {"action": "use", "promoCode": promo_code.upper()}
            async with session.post(GOOGLE_SCRIPT_URL, json=payload) as resp:
                result = await resp.json()
                return result.get("success", False)
        except:
            return False

async def return_promo_google(promo_code):
    async with aiohttp.ClientSession() as session:
        try:
            payload = {"action": "return", "promoCode": promo_code.upper()}
            async with session.post(GOOGLE_SCRIPT_URL, json=payload) as resp:
                result = await resp.json()
                return result.get("success", False)
        except:
            return False

async def add_promo_google(code, limit, discount):
    async with aiohttp.ClientSession() as session:
        try:
            payload = {"action": "add", "promoCode": code.upper(), "limit": limit, "discount": discount}
            async with session.post(GOOGLE_SCRIPT_URL, json=payload) as resp:
                result = await resp.json()
                return result.get("status") == "success", result.get("message", "")
        except:
            return False, "Ошибка подключения"

def add_bonus_to_user(user_id, amount):
    users = load_users()
    user_id_str = str(user_id)
    if user_id_str not in users:
        users[user_id_str] = {"order_counter": 0, "bonus_balance": 0}
    users[user_id_str]["bonus_balance"] = users[user_id_str].get("bonus_balance", 0) + amount
    save_users(users)
    return users[user_id_str]["bonus_balance"]

def get_user_bonus(user_id):
    users = load_users()
    user_id_str = str(user_id)
    if user_id_str not in users:
        return 0
    return users[user_id_str].get("bonus_balance", 0)

def use_bonus(user_id, amount):
    users = load_users()
    user_id_str = str(user_id)
    if user_id_str not in users:
        return False
    current = users[user_id_str].get("bonus_balance", 0)
    if current >= amount:
        users[user_id_str]["bonus_balance"] = current - amount
        save_users(users)
        return True
    return False

def return_bonus(user_id, amount):
    users = load_users()
    user_id_str = str(user_id)
    if user_id_str not in users:
        users[user_id_str] = {"order_counter": 0, "bonus_balance": 0}
    users[user_id_str]["bonus_balance"] = users[user_id_str].get("bonus_balance", 0) + amount
    save_users(users)
    return users[user_id_str]["bonus_balance"]

def main_keyboard(user_id: int):
    keyboard = [
        [KeyboardButton(text="📝 Заполнить заявку")],
        [KeyboardButton(text="👤 Мой профиль")],
        [KeyboardButton(text="🔗 Моя реферальная ссылка")]
    ]
    if user_id in ADMIN_IDS:
        keyboard.append([KeyboardButton(text="➕ Добавить промокод")])
        keyboard.append([KeyboardButton(text="📊 Рефералы и бонусы")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

cancel_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Отменить заказ")]],
    resize_keyboard=True
)

bonus_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ Да, использовать бонусы")],
        [KeyboardButton(text="❌ Нет, не использовать")]
    ],
    resize_keyboard=True
)

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def get_status_emoji(status):
    if status == "pending":
        return "⏳"
    elif status == "completed":
        return "✅"
    elif status == "cancelled":
        return "❌"
    return "📦"

async def get_username(user_id):
    try:
        user = await bot.get_chat(user_id)
        return user.username or f"user_{user_id}"
    except:
        return f"user_{user_id}"

@dp.message(Command("start"))
async def cmd_start(message: Message):
    args = message.text.split()
    ref_id = None
    if len(args) > 1 and args[1].startswith("ref_"):
        ref_id = int(args[1].replace("ref_", ""))
    
    user_id = message.from_user.id
    
    users = load_users()
    if str(user_id) not in users:
        users[str(user_id)] = {"order_counter": 0, "bonus_balance": 0}
        save_users(users)
    
    referrals = load_referrals()
    if str(user_id) not in referrals and ref_id and ref_id != user_id:
        referrals[str(user_id)] = {"referred_by": ref_id, "total_orders": 0, "bonus_earned": 0}
        save_referrals(referrals)
        
        try:
            await bot.send_message(
                ref_id,
                f"🎉 По вашей реферальной ссылке зарегистрировался новый пользователь!\n"
                f"👤 @{message.from_user.username or message.from_user.first_name}\n\n"
                f"Когда он сделает заказ, вы получите бонус (админ начислит вручную)."
            )
        except:
            pass
        await message.answer("🔗 Вы зарегистрированы по реферальной ссылке! Приятных покупок 🎮")
    
    links_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Наш канал", url=CHANNEL_LINK)]
    ])
    await message.answer(
        "🎮 Добро пожаловать в магазин!\n\n"
        "📝 Заполните заявку — и мы свяжемся с вами\n"
        "👤 В профиле можно посмотреть историю заказов и бонусы\n"
        "🔗 Приглашайте друзей и получайте бонусы с их покупок!",
        reply_markup=links_kb
    )
    await message.answer(
        "📋 Главное меню",
        reply_markup=main_keyboard(message.from_user.id)
    )

@dp.message(F.text == "🔗 Моя реферальная ссылка")
async def show_ref_link(message: Message):
    bot_info = await bot.get_me()
    bot_username = bot_info.username
    
    link = f"https://t.me/{bot_username}?start=ref_{message.from_user.id}"
    referrals = load_referrals()
    my_refs = [uid for uid, data in referrals.items() if data.get("referred_by") == message.from_user.id]
    
    text = (
        f"🔗 **Ваша реферальная ссылка:**\n"
        f"`{link}`\n\n"
        f"👥 Приглашено друзей: {len(my_refs)}\n"
        f"💰 Бонусный баланс: {get_user_bonus(message.from_user.id)} BYN\n\n"
        f"💡 **Как это работает:**\n"
        f"• Пригласите друга по вашей ссылке\n"
        f"• Когда он сделает заказ, администратор начислит вам бонус\n"
        f"• Бонусы можно использовать при следующем заказе"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=main_keyboard(message.from_user.id))

@dp.message(F.text == "👤 Мой профиль")
async def show_profile(message: Message):
    orders = load_orders()
    user_orders = [o for o in orders if o.get("user_id") == message.from_user.id]
    
    status_counts = {"pending": 0, "completed": 0, "cancelled": 0}
    for o in user_orders:
        status = o.get("status", "pending")
        status_counts[status] = status_counts.get(status, 0) + 1
    
    bonus = get_user_bonus(message.from_user.id)
    
    text = (
        f"👤 **Ваш профиль**\n\n"
        f"📦 Всего заказов: {len(user_orders)}\n"
        f"💰 Бонусный баланс: {bonus} BYN\n\n"
        f"📊 Статусы заказов:\n"
        f"   ⏳ В обработке: {status_counts.get('pending', 0)}\n"
        f"   ✅ Выполнено: {status_counts.get('completed', 0)}\n"
        f"   ❌ Отменено: {status_counts.get('cancelled', 0)}\n\n"
        f"💡 Бонусы начисляются администратором за приглашённых друзей."
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=main_keyboard(message.from_user.id))

@dp.message(F.text == "📊 Рефералы и бонусы")
async def admin_ref_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет прав")
        return
    
    users = load_users()
    
    if not users:
        await message.answer("📭 Список пользователей пуст.\n\nПользователи появляются после того, как напишут /start или сделают заказ.")
        return
    
    text = "📊 **Панель управления бонусами**\n\n"
    text += "Нажми на пользователя, чтобы увидеть информацию.\n\n"
    text += "👥 **Список пользователей:**"
    
    keyboard = []
    for uid in users:
        try:
            username = await get_username(int(uid))
            keyboard.append([InlineKeyboardButton(text=f"👤 {username}", callback_data=f"user_{uid}")])
        except:
            keyboard.append([InlineKeyboardButton(text=f"👤 user_{uid}", callback_data=f"user_{uid}")])
    
    if not keyboard:
        await message.answer("❌ Не удалось загрузить список пользователей.")
        return
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer(text, reply_markup=markup, parse_mode="Markdown")

@dp.callback_query(lambda c: c.data and c.data.startswith("user_"))
async def user_detail(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return
    
    try:
        user_id = int(callback.data.split("_")[1])
    except:
        await callback.answer("Ошибка: неверный формат", show_alert=True)
        return
    
    referrals = load_referrals()
    users = load_users()
    
    referred_by = referrals.get(str(user_id), {}).get("referred_by")
    bonus = users.get(str(user_id), {}).get("bonus_balance", 0)
    
    text = (
        f"👤 **Информация о пользователе**\n\n"
        f"🆔 ID: {user_id}\n"
        f"💰 Бонусный баланс: {bonus} BYN\n"
    )
    
    if referred_by:
        text += f"🔗 Приглашён пользователем: @{await get_username(referred_by)}\n\n"
        text += f"👇 Нажмите кнопку ниже, чтобы начислить бонус **пригласившему** (@{await get_username(referred_by)}) за покупки этого реферала."
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 Начислить бонус пригласившему", callback_data=f"bonus_to_referrer_{user_id}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_users")]
        ])
    else:
        text += f"🔗 Приглашён: никем\n"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 Начислить бонус напрямую", callback_data=f"direct_bonus_{user_id}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_users")]
        ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "back_to_users")
async def back_to_users(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return
    
    users = load_users()
    keyboard = []
    for uid in users:
        try:
            username = await get_username(int(uid))
            keyboard.append([InlineKeyboardButton(text=f"👤 {username}", callback_data=f"user_{uid}")])
        except:
            keyboard.append([InlineKeyboardButton(text=f"👤 user_{uid}", callback_data=f"user_{uid}")])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None
    text = "📊 **Панель управления бонусами**\n\nНажми на пользователя для управления бонусами."
    await callback.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("bonus_to_referrer_"))
async def bonus_to_referrer(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return
    
    referred_user_id = int(callback.data.split("_")[3])
    referrals = load_referrals()
    
    referrer_id = referrals.get(str(referred_user_id), {}).get("referred_by")
    
    if not referrer_id:
        await callback.answer("Ошибка: не найден пригласивший", show_alert=True)
        return
    
    await state.update_data(bonus_user_id=referrer_id, referred_user_id=referred_user_id)
    await state.set_state(AddBonus.amount)
    await callback.message.answer(f"💰 Введите сумму бонуса (в BYN) для пользователя @{await get_username(referrer_id)}\n(бонус за покупку его реферала @{await get_username(referred_user_id)})")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("direct_bonus_"))
async def direct_bonus(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[2])
    await state.update_data(bonus_user_id=user_id, referred_user_id=None)
    await state.set_state(AddBonus.amount)
    await callback.message.answer(f"💰 Введите сумму бонуса (в BYN) для пользователя @{await get_username(user_id)}:")
    await callback.answer()

@dp.message(AddBonus.amount)
async def add_bonus_amount(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Нет прав")
        return
    
    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0")
            return
    except:
        await message.answer("❌ Введите число (например: 5 или 10.5)")
        return
    
    data = await state.get_data()
    user_id = data.get("bonus_user_id")
    referred_user_id = data.get("referred_user_id")
    
    new_balance = add_bonus_to_user(user_id, amount)
    
    # Правильное сообщение: бонус за покупку реферала
    if referred_user_id:
        referred_username = await get_username(referred_user_id)
        bonus_text = f"за покупку вашего реферала @{referred_username}"
    else:
        bonus_text = ""
    
    try:
        await bot.send_message(
            user_id,
            f"🎉 **Вам начислен бонус!** {bonus_text}\n\n"
            f"💰 Сумма: {amount} BYN\n"
            f"💎 Ваш бонусный баланс: {new_balance} BYN\n\n"
            f"Бонусы можно использовать при следующем заказе.",
            parse_mode="Markdown"
        )
    except:
        pass
    
    await message.answer(f"✅ Начислено {amount} BYN пользователю @{await get_username(user_id)}\n💰 Новый баланс: {new_balance} BYN")
    await state.clear()

@dp.message(F.text == "❌ Отменить заказ")
async def cancel_order(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
        await message.answer(
            "❌ Создание заказа отменено.\n\n"
            "Если передумаете — нажмите «📝 Заполнить заявку» снова.",
            reply_markup=main_keyboard(message.from_user.id)
        )
    else:
        await message.answer(
            "У вас нет активного заказа для отмены.",
            reply_markup=main_keyboard(message.from_user.id)
        )

@dp.message(F.text == "📝 Заполнить заявку")
async def start_order(message: Message, state: FSMContext):
    await state.set_state(OrderForm.game)
    await message.answer(
        "🎮 Шаг 1/6: Введите название игры\n\n"
        "Если передумаете — нажмите «❌ Отменить заказ»",
        reply_markup=cancel_keyboard
    )

@dp.message(OrderForm.game)
async def process_game(message: Message, state: FSMContext):
    if message.text == "❌ Отменить заказ":
        await cancel_order(message, state)
        return
    await state.update_data(game=message.text)
    await state.set_state(OrderForm.item)
    await message.answer("📦 Шаг 2/6: Введите название товара", reply_markup=cancel_keyboard)

@dp.message(OrderForm.item)
async def process_item(message: Message, state: FSMContext):
    if message.text == "❌ Отменить заказ":
        await cancel_order(message, state)
        return
    await state.update_data(item=message.text)
    await state.set_state(OrderForm.photo)
    await message.answer("🖼️ Шаг 3/6: Пришлите фото товара", reply_markup=cancel_keyboard)

@dp.message(OrderForm.photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await state.set_state(OrderForm.quantity)
    await message.answer("🔢 Шаг 4/6: Введите количество", reply_markup=cancel_keyboard)

@dp.message(OrderForm.photo)
async def process_photo_invalid(message: Message):
    await message.answer("❌ Отправьте фото!\n\nИли нажмите «❌ Отменить заказ»", reply_markup=cancel_keyboard)

@dp.message(OrderForm.quantity)
async def process_quantity(message: Message, state: FSMContext):
    if message.text == "❌ Отменить заказ":
        await cancel_order(message, state)
        return
    if not message.text.isdigit():
        await message.answer("❌ Введите число!", reply_markup=cancel_keyboard)
        return
    await state.update_data(quantity=int(message.text))
    await state.set_state(OrderForm.username)
    await message.answer("👤 Шаг 5/6: Введите ваш Telegram username (без @)", reply_markup=cancel_keyboard)

@dp.message(OrderForm.username)
async def process_username(message: Message, state: FSMContext):
    if message.text == "❌ Отменить заказ":
        await cancel_order(message, state)
        return
    username = message.text.strip().lstrip('@')
    await state.update_data(username=username)
    await state.set_state(OrderForm.promo)
    await message.answer("🎟️ Шаг 6/6: Введите промокод (если нет — напишите «нет»)", reply_markup=cancel_keyboard)

@dp.message(OrderForm.promo)
async def process_promo(message: Message, state: FSMContext):
    if message.text == "❌ Отменить заказ":
        await cancel_order(message, state)
        return
    
    promo_code = message.text.strip().upper()
    if promo_code in ["НЕТ", "NO", "SKIP"]:
        await state.update_data(promo_used=None, promo_discount=0)
        await ask_use_bonus(message, state)
        return
    
    valid, discount = await check_promo_google(promo_code)
    if valid:
        await use_promo_google(promo_code)
        await state.update_data(promo_used=promo_code, promo_discount=discount)
        await message.answer(f"✅ Промокод {promo_code} активирован! Скидка: {discount}%")
        await ask_use_bonus(message, state)
    else:
        await message.answer("❌ Промокод недействителен. Введите другой или напишите «нет»", reply_markup=cancel_keyboard)

async def ask_use_bonus(message: Message, state: FSMContext):
    data = await state.get_data()
    has_promo = data.get('promo_used') is not None
    bonus_balance = get_user_bonus(message.from_user.id)
    
    if has_promo and bonus_balance > 0:
        await state.set_state(OrderForm.use_bonus)
        await message.answer(
            f"⚠️ У вас активен промокод и есть бонусы ({bonus_balance} BYN).\n\n"
            f"❌ Нельзя использовать промокод и бонусы одновременно!\n\n"
            f"Выберите, что использовать:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="🎟️ Оставить промокод (без бонусов)")],
                    [KeyboardButton(text="💰 Использовать бонусы (без промокода)")]
                ],
                resize_keyboard=True
            )
        )
    elif bonus_balance > 0:
        await state.set_state(OrderForm.use_bonus)
        await message.answer(
            f"💰 У вас есть бонусы: {bonus_balance} BYN\n\n"
            f"Желаете использовать их для оплаты заказа?\n\n"
            f"(Бонусы сгорят после использования)",
            reply_markup=bonus_keyboard
        )
    else:
        await state.update_data(used_bonus=0)
        await finish_order(message, state)

@dp.message(OrderForm.use_bonus)
async def process_use_bonus(message: Message, state: FSMContext):
    data = await state.get_data()
    bonus_balance = get_user_bonus(message.from_user.id)
    
    if message.text == "🎟️ Оставить промокод (без бонусов)":
        await state.update_data(used_bonus=0)
        await finish_order(message, state)
        return
    
    if message.text == "💰 Использовать бонусы (без промокода)":
        if data.get('promo_used'):
            await return_promo_google(data['promo_used'])
        await state.update_data(promo_used=None, promo_discount=0)
        await message.answer("✅ Промокод отменён. Теперь вы можете использовать бонусы.")
        await ask_use_bonus(message, state)
        return
    
    if message.text == "✅ Да, использовать бонусы":
        if bonus_balance <= 0:
            await message.answer("❌ У вас нет бонусов для использования! Приглашайте друзей, чтобы получать бонусы.", reply_markup=cancel_keyboard)
            return
        await state.update_data(used_bonus=bonus_balance)
        await message.answer(f"✅ Будут использованы бонусы: {bonus_balance} BYN\n\n💰 Вы сможете оплатить заказ полностью или частично при встрече с администратором.")
        await finish_order(message, state)
    
    elif message.text == "❌ Нет, не использовать":
        await state.update_data(used_bonus=0)
        await finish_order(message, state)

async def finish_order(message: Message, state: FSMContext):
    data = await state.get_data()
    
    order_number = get_next_order_number(message.from_user.id)
    order_id = str(order_number)
    
    used_bonus = data.get('used_bonus', 0)
    if used_bonus > 0:
        use_bonus(message.from_user.id, used_bonus)
    
    order = {
        "order_id": order_id,
        "user_id": message.from_user.id,
        "username": data['username'],
        "game": data['game'],
        "item": data['item'],
        "quantity": data['quantity'],
        "promo_discount": data.get('promo_discount', 0),
        "promo_used": data.get('promo_used'),
        "used_bonus": used_bonus,
        "status": "pending",
        "date": datetime.now().isoformat(),
        "photo": data.get('photo')
    }
    
    orders = load_orders()
    orders.append(order)
    save_orders(orders)
    
    await send_order_to_group(order)
    
    bonus_text = ""
    if used_bonus > 0:
        bonus_text = f"\n\n💰 Списано бонусов: {used_bonus} BYN"
    
    await message.answer(
        f"✅ Ваш заказ принят!\n\n"
        f"📦 Номер заказа: #{order_id}\n\n"
        f"Скоро с вами свяжется администратор.\n"
        f"Спасибо, что выбрали нас! 🎮{bonus_text}",
        reply_markup=main_keyboard(message.from_user.id)
    )
    
    await state.clear()

async def send_order_to_group(order):
    status_emoji = get_status_emoji(order['status'])
    
    if order['status'] == "completed":
        header = "✅ ЗАКРЫТО\n\n"
    elif order['status'] == "cancelled":
        header = "❌ ОТМЕНЕНО\n\n"
    else:
        header = ""
    
    body = (
        f"{status_emoji} Заказ #{order['order_id']}\n\n"
        f"🎮 Игра: {order['game']}\n"
        f"📦 Товар: {order['item']}\n"
        f"🔢 Количество: {order['quantity']}\n"
    )
    if order.get('promo_discount', 0) > 0:
        body += f"🎟️ Промокод: {order['promo_used']} (скидка {order['promo_discount']}%)\n"
    if order.get('used_bonus', 0) > 0:
        body += f"💰 Списано бонусов: {order['used_bonus']} BYN\n"
    
    body += f"\n👤 Покупатель: @{order['username']}\n"
    body += f"🕒 Время: {datetime.fromisoformat(order['date']).strftime('%d.%m.%Y %H:%M:%S')}"
    
    text = header + body
    
    keyboard = []
    if order['status'] == "pending":
        keyboard = [
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_{order['order_id']}"),
                InlineKeyboardButton(text="✅ Выполнено", callback_data=f"complete_{order['order_id']}")
            ]
        ]
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None
    
    if order.get('message_id'):
        try:
            await bot.edit_message_text(
                chat_id=ADMIN_GROUP_ID,
                message_id=order['message_id'],
                text=text,
                reply_markup=markup
            )
        except:
            pass
    else:
        if order.get('photo'):
            msg = await bot.send_photo(ADMIN_GROUP_ID, order['photo'], caption=text, reply_markup=markup)
        else:
            msg = await bot.send_message(ADMIN_GROUP_ID, text, reply_markup=markup)
        
        orders = load_orders()
        for o in orders:
            if o['order_id'] == order['order_id']:
                o['message_id'] = msg.message_id
                save_orders(orders)
                break

@dp.callback_query(lambda c: c.data.startswith(('cancel_', 'complete_')))
async def process_order_action(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return
    
    action, order_id = callback.data.split('_', 1)
    order = get_order_by_id(order_id)
    
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    
    buyer_user_id = int(order['user_id'])
    game = order.get('game', '')
    item = order.get('item', '')
    quantity = order.get('quantity', '')
    used_bonus = order.get('used_bonus', 0)
    promo_used = order.get('promo_used')
    
    if action == 'cancel':
        new_status = 'cancelled'
        
        if used_bonus > 0:
            return_bonus(buyer_user_id, used_bonus)
        
        if promo_used:
            await return_promo_google(promo_used)
        
        user_message = (
            "❌ Ваш заказ был отменён администратором.\n\n"
            "По всем вопросам:\n"
            "[t.me/enforce1](t.me/enforce1)\n"
            "[t.me/artemixs_4](t.me/artemixs_4)"
        )
        admin_message = "❌ Заказ отменён"
    elif action == 'complete':
        new_status = 'completed'
        user_message = "✅ Ваш заказ выполнен!\n\nСпасибо за покупку! Ждём вас снова 🎮"
        admin_message = "✅ Заказ выполнен"
    else:
        return
    
    update_order_status(order_id, new_status)
    order['status'] = new_status
    
    await send_order_to_group(order)
    
    try:
        await bot.send_message(
            chat_id=buyer_user_id,
            text=f"{user_message}\n\n📦 Заказ #{order_id}\n🎮 {game} | {item}\n🔢 Количество: {quantity}",
            parse_mode="Markdown"
        )
    except:
        pass
    
    await callback.answer(admin_message)

@dp.message(F.text == "➕ Добавить промокод")
async def admin_add_promo_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет прав")
        return
    await state.set_state(AddPromo.code)
    await message.answer("🔑 Введите код промокода (латиницей)")

@dp.message(AddPromo.code)
async def admin_add_promo_code(message: Message, state: FSMContext):
    await state.update_data(code=message.text.strip().upper())
    await state.set_state(AddPromo.limit)
    await message.answer("🔢 Введите лимит активаций")

@dp.message(AddPromo.limit)
async def admin_add_promo_limit(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Введите число")
        return
    await state.update_data(limit=int(message.text))
    await state.set_state(AddPromo.discount)
    await message.answer("🎯 Введите процент скидки")

@dp.message(AddPromo.discount)
async def admin_add_promo_discount(message: Message, state: FSMContext):
    try:
        discount = float(message.text.replace(',', '.'))
        if discount < 0 or discount > 100:
            await message.answer("❌ От 0 до 100")
            return
    except:
        await message.answer("❌ Введите число")
        return
    
    data = await state.get_data()
    success, msg = await add_promo_google(data['code'], data['limit'], int(discount))
    if success:
        await message.answer(f"✅ Промокод {data['code']} добавлен!\n📊 Лимит: {data['limit']}\n🎯 Скидка: {discount}%")
    else:
        await message.answer(f"❌ Ошибка: {msg}")
    await state.clear()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    print("🤖 Бот запущен!")
    print(f"Администраторы: {ADMIN_IDS}")
    print(f"Группа заказов: {ADMIN_GROUP_ID}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
