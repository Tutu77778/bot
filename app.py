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
        referrals[str(user_id)] = {"referred_by": ref_id}
        save_referrals(referrals)
        
        try:
            await bot.send_message(
                ref_id,
                f"🎉 По вашей реферальной ссылке зарегистрировался новый пользователь!\n"
                f"👤 @{message.from_user.username or message.from_user.first_name}"
            )
        except:
            pass
        await message.answer("🔗 Вы зарегистрированы по реферальной ссылке!")
    
    links_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Наш канал", url=CHANNEL_LINK)]
    ])
    await message.answer("🎮 Добро пожаловать!", reply_markup=links_kb)
    await message.answer("📋 Главное меню", reply_markup=main_keyboard(message.from_user.id))

@dp.message(F.text == "🔗 Моя реферальная ссылка")
async def show_ref_link(message: Message):
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{message.from_user.id}"
    referrals = load_referrals()
    my_refs = [uid for uid, data in referrals.items() if data.get("referred_by") == message.from_user.id]
    await message.answer(
        f"🔗 Ваша ссылка:\n`{link}`\n\n👥 Приглашено: {len(my_refs)}\n💰 Бонусов: {get_user_bonus(message.from_user.id)} BYN",
        parse_mode="Markdown", reply_markup=main_keyboard(message.from_user.id)
    )

@dp.message(F.text == "👤 Мой профиль")
async def show_profile(message: Message):
    orders = load_orders()
    user_orders = [o for o in orders if o.get("user_id") == message.from_user.id]
    await message.answer(
        f"👤 Профиль\n\n📦 Заказов: {len(user_orders)}\n💰 Бонусов: {get_user_bonus(message.from_user.id)} BYN",
        reply_markup=main_keyboard(message.from_user.id)
    )

@dp.message(F.text == "📊 Рефералы и бонусы")
async def admin_ref_panel(message: Message):
    if not is_admin(message.from_user.id):
        return
    users = load_users()
    if not users:
        await message.answer("Нет пользователей")
        return
    keyboard = []
    for uid in users:
        username = await get_username(int(uid))
        keyboard.append([InlineKeyboardButton(text=f"👤 {username}", callback_data=f"user_{uid}")])
    await message.answer("📊 Список пользователей:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@dp.callback_query(lambda c: c.data.startswith("user_"))
async def user_detail(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔", show_alert=True)
        return
    user_id = int(callback.data.split("_")[1])
    referrals = load_referrals()
    referred_by = referrals.get(str(user_id), {}).get("referred_by")
    bonus = get_user_bonus(user_id)
    text = f"👤 ID: {user_id}\n💰 Баланс: {bonus} BYN\n"
    if referred_by:
        text += f"🔗 Приглашён: @{await get_username(referred_by)}\n"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 Начислить бонус пригласившему", callback_data=f"bonus_to_{user_id}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_users")]
        ])
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 Начислить бонус напрямую", callback_data=f"bonus_direct_{user_id}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_users")]
        ])
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "back_to_users")
async def back_to_users(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔", show_alert=True)
        return
    users = load_users()
    keyboard = []
    for uid in users:
        username = await get_username(int(uid))
        keyboard.append([InlineKeyboardButton(text=f"👤 {username}", callback_data=f"user_{uid}")])
    await callback.message.edit_text("📊 Список пользователей:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("bonus_to_"))
async def bonus_to_referrer(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔", show_alert=True)
        return
    referred_id = int(callback.data.split("_")[2])
    referrals = load_referrals()
    referrer_id = referrals.get(str(referred_id), {}).get("referred_by")
    if not referrer_id:
        await callback.answer("Ошибка")
        return
    await state.update_data(bonus_user_id=referrer_id, referred_user_id=referred_id)
    await state.set_state(AddBonus.amount)
    await callback.message.answer(f"💰 Сумма бонуса для @{await get_username(referrer_id)} (за реферала @{await get_username(referred_id)}):")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("bonus_direct_"))
async def bonus_direct(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔", show_alert=True)
        return
    user_id = int(callback.data.split("_")[2])
    await state.update_data(bonus_user_id=user_id)
    await state.set_state(AddBonus.amount)
    await callback.message.answer(f"💰 Сумма бонуса для @{await get_username(user_id)}:")
    await callback.answer()

@dp.message(AddBonus.amount)
async def add_bonus_amount(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔")
        return
    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0:
            await message.answer("❌ >0")
            return
    except:
        await message.answer("❌ Число")
        return
    data = await state.get_data()
    user_id = data.get("bonus_user_id")
    referred_id = data.get("referred_user_id")
    new_balance = add_bonus_to_user(user_id, amount)
    try:
        text = f"🎉 Вам начислен бонус {amount} BYN!"
        if referred_id:
            text += f"\n\nЗа покупку вашего реферала @{await get_username(referred_id)}"
        await bot.send_message(user_id, text)
    except:
        pass
    await message.answer(f"✅ Начислено {amount} BYN. Новый баланс: {new_balance}")
    await state.clear()

@dp.message(F.text == "❌ Отменить заказ")
async def cancel_order(message: Message, state: FSMContext):
    if await state.get_state():
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=main_keyboard(message.from_user.id))
    else:
        await message.answer("Нет активного заказа", reply_markup=main_keyboard(message.from_user.id))

@dp.message(F.text == "📝 Заполнить заявку")
async def start_order(message: Message, state: FSMContext):
    await state.set_state(OrderForm.game)
    await message.answer("🎮 Шаг 1/6: Название игры\n\n❌ Отменить заказ", reply_markup=cancel_keyboard)

@dp.message(OrderForm.game)
async def process_game(message: Message, state: FSMContext):
    if message.text == "❌ Отменить заказ":
        await cancel_order(message, state)
        return
    await state.update_data(game=message.text)
    await state.set_state(OrderForm.item)
    await message.answer("📦 Шаг 2/6: Товар", reply_markup=cancel_keyboard)

@dp.message(OrderForm.item)
async def process_item(message: Message, state: FSMContext):
    if message.text == "❌ Отменить заказ":
        await cancel_order(message, state)
        return
    await state.update_data(item=message.text)
    await state.set_state(OrderForm.photo)
    await message.answer("🖼️ Шаг 3/6: Фото", reply_markup=cancel_keyboard)

@dp.message(OrderForm.photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await state.set_state(OrderForm.quantity)
    await message.answer("🔢 Шаг 4/6: Количество", reply_markup=cancel_keyboard)

@dp.message(OrderForm.photo)
async def process_photo_invalid(message: Message):
    await message.answer("❌ Отправьте фото!", reply_markup=cancel_keyboard)

@dp.message(OrderForm.quantity)
async def process_quantity(message: Message, state: FSMContext):
    if message.text == "❌ Отменить заказ":
        await cancel_order(message, state)
        return
    if not message.text.isdigit():
        await message.answer("❌ Число!", reply_markup=cancel_keyboard)
        return
    await state.update_data(quantity=int(message.text))
    await state.set_state(OrderForm.username)
    await message.answer("👤 Шаг 5/6: Username (без @)", reply_markup=cancel_keyboard)

@dp.message(OrderForm.username)
async def process_username(message: Message, state: FSMContext):
    if message.text == "❌ Отменить заказ":
        await cancel_order(message, state)
        return
    await state.update_data(username=message.text.strip().lstrip('@'))
    await state.set_state(OrderForm.promo)
    await message.answer("🎟️ Шаг 6/6: Промокод (или «нет»)", reply_markup=cancel_keyboard)

@dp.message(OrderForm.promo)
async def process_promo(message: Message, state: FSMContext):
    if message.text == "❌ Отменить заказ":
        await cancel_order(message, state)
        return
    promo = message.text.strip().upper()
    if promo in ["НЕТ", "NO"]:
        await state.update_data(promo_used=None, promo_discount=0)
        await ask_use_bonus(message, state)
        return
    valid, disc = await check_promo_google(promo)
    if valid:
        await use_promo_google(promo)
        await state.update_data(promo_used=promo, promo_discount=disc)
        await message.answer(f"✅ Промокод {promo} активирован! Скидка: {disc}%")
        await ask_use_bonus(message, state)
    else:
        await message.answer("❌ Недействителен", reply_markup=cancel_keyboard)

async def ask_use_bonus(message: Message, state: FSMContext):
    data = await state.get_data()
    bonus = get_user_bonus(message.from_user.id)
    if data.get('promo_used') and bonus > 0:
        await state.set_state(OrderForm.use_bonus)
        await message.answer("⚠️ Нельзя использовать промокод и бонусы вместе!\nВыберите:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🎟️ Промокод")], [KeyboardButton(text="💰 Бонусы")]], resize_keyboard=True))
    elif bonus > 0:
        await state.set_state(OrderForm.use_bonus)
        await message.answer(f"💰 У вас {bonus} BYN. Использовать?", reply_markup=bonus_keyboard)
    else:
        await state.update_data(used_bonus=0)
        await finish_order(message, state)

@dp.message(OrderForm.use_bonus)
async def process_use_bonus(message: Message, state: FSMContext):
    data = await state.get_data()
    bonus = get_user_bonus(message.from_user.id)
    if message.text == "🎟️ Промокод":
        await state.update_data(used_bonus=0)
        await finish_order(message, state)
    elif message.text == "💰 Бонусы":
        if data.get('promo_used'):
            await return_promo_google(data['promo_used'])
        await state.update_data(promo_used=None, promo_discount=0, used_bonus=bonus)
        await message.answer(f"✅ Бонусы {bonus} BYN будут использованы")
        await finish_order(message, state)
    elif message.text == "✅ Да":
        await state.update_data(used_bonus=bonus)
        await message.answer(f"✅ Бонусы {bonus} BYN будут использованы")
        await finish_order(message, state)
    elif message.text == "❌ Нет":
        await state.update_data(used_bonus=0)
        await finish_order(message, state)

async def finish_order(message: Message, state: FSMContext):
    data = await state.get_data()
    order_id = str(get_next_order_number(message.from_user.id))
    used_bonus = data.get('used_bonus', 0)
    if used_bonus > 0:
        use_bonus(message.from_user.id, used_bonus)
    order = {
        "order_id": order_id, "user_id": message.from_user.id, "username": data['username'],
        "game": data['game'], "item": data['item'], "quantity": data['quantity'],
        "promo_discount": data.get('promo_discount', 0), "promo_used": data.get('promo_used'),
        "used_bonus": used_bonus, "status": "pending", "date": datetime.now().isoformat(), "photo": data.get('photo')
    }
    orders = load_orders()
    orders.append(order)
    save_orders(orders)
    await send_order_to_group(order, is_new=True)
    await message.answer(f"✅ Заказ #{order_id} принят!", reply_markup=main_keyboard(message.from_user.id))
    await state.clear()

async def send_order_to_group(order, is_new=False):
    status_emoji = get_status_emoji(order['status'])
    
    # Заголовок в зависимости от статуса
    if order['status'] == "completed":
        header = "✅ ЗАКРЫТО\n\n"
        show_buttons = False
    elif order['status'] == "cancelled":
        header = "❌ ОТМЕНЕНО\n\n"
        show_buttons = False
    else:
        header = ""
        show_buttons = True
    
    body = (
        f"{status_emoji} Заказ #{order['order_id']}\n\n"
        f"🎮 {order['game']}\n📦 {order['item']}\n🔢 {order['quantity']}\n"
    )
    if order.get('promo_discount', 0) > 0:
        body += f"🎟️ Промокод: {order['promo_used']} (-{order['promo_discount']}%)\n"
    if order.get('used_bonus', 0) > 0:
        body += f"💰 Бонусов: {order['used_bonus']} BYN\n"
    body += f"\n👤 @{order['username']}\n🕒 {datetime.fromisoformat(order['date']).strftime('%d.%m.%Y %H:%M:%S')}"
    
    text = header + body
    
    # Кнопки только для pending
    keyboard = []
    if show_buttons and order['status'] == "pending":
        keyboard = [[
            InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_{order['order_id']}"),
            InlineKeyboardButton(text="✅ Выполнено", callback_data=f"complete_{order['order_id']}")
        ]]
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None
    
    if is_new or not order.get('message_id'):
        # Отправляем новое сообщение
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
    else:
        # Редактируем существующее сообщение
        try:
            await bot.edit_message_text(
                chat_id=ADMIN_GROUP_ID,
                message_id=order['message_id'],
                text=text,
                reply_markup=markup
            )
        except Exception as e:
            print(f"Ошибка редактирования: {e}")

@dp.callback_query(lambda c: c.data.startswith(('cancel_', 'complete_')))
async def process_order_action(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔", show_alert=True)
        return
    
    action, order_id = callback.data.split('_', 1)
    order = get_order_by_id(order_id)
    if not order:
        await callback.answer("Ошибка")
        return
    
    user_id = int(order['user_id'])
    
    if action == 'cancel':
        if order.get('used_bonus', 0) > 0:
            return_bonus(user_id, order['used_bonus'])
        if order.get('promo_used'):
            await return_promo_google(order['promo_used'])
        update_order_status(order_id, 'cancelled')
        order['status'] = 'cancelled'
        
        # ОБНОВЛЯЕМ СООБЩЕНИЕ В ГРУППЕ
        await send_order_to_group(order, is_new=False)
        
        try:
            await bot.send_message(user_id, f"❌ Заказ #{order_id} отменён\n\nПо вопросам: @enforce1, @artemixs_4")
        except:
            pass
        await callback.answer("❌ Отменён")
        
    elif action == 'complete':
        update_order_status(order_id, 'completed')
        order['status'] = 'completed'
        
        # ОБНОВЛЯЕМ СООБЩЕНИЕ В ГРУППЕ
        await send_order_to_group(order, is_new=False)
        
        try:
            await bot.send_message(user_id, f"✅ Заказ #{order_id} выполнен!\nСпасибо за покупку!")
        except:
            pass
        await callback.answer("✅ Выполнен")
    
    # Убираем кнопки у callback-сообщения (чтобы не висели)
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except:
        pass

@dp.message(F.text == "➕ Добавить промокод")
async def admin_add_promo_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AddPromo.code)
    await message.answer("🔑 Код промокода:")

@dp.message(AddPromo.code)
async def admin_add_promo_code(message: Message, state: FSMContext):
    await state.update_data(code=message.text.strip().upper())
    await state.set_state(AddPromo.limit)
    await message.answer("🔢 Лимит:")

@dp.message(AddPromo.limit)
async def admin_add_promo_limit(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Число")
        return
    await state.update_data(limit=int(message.text))
    await state.set_state(AddPromo.discount)
    await message.answer("🎯 % скидки:")

@dp.message(AddPromo.discount)
async def admin_add_promo_discount(message: Message, state: FSMContext):
    try:
        disc = float(message.text.replace(',', '.'))
        if disc < 0 or disc > 100:
            await message.answer("❌ 0-100")
            return
    except:
        await message.answer("❌ Число")
        return
    data = await state.get_data()
    success, msg = await add_promo_google(data['code'], data['limit'], int(disc))
    await message.answer(f"✅ {msg}" if success else f"❌ {msg}")
    await state.clear()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    print("🤖 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
