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

# ========== ТВОЙ ТОКЕН ==========
BOT_TOKEN = "8684547044:AAGVVDzmha4RlCLKgk_dI-DPecb20JbgFRo"
# ================================

ADMIN_GROUP_ID = -1003959266816
ADMIN_IDS = [6209172297, 1852789843]

# Ссылка на канал
CHANNEL_LINK = "https://t.me/agshopi"

# Файлы
ORDERS_FILE = "orders.json"
USERS_FILE = "users.json"

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

def get_next_order_number(user_id):
    users = load_users()
    user_id_str = str(user_id)
    if user_id_str not in users:
        users[user_id_str] = {"order_counter": 0}
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

# ========== ИНИЦИАЛИЗАЦИЯ БОТА ==========
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ========== СОСТОЯНИЯ ==========
class OrderForm(StatesGroup):
    game = State()
    item = State()
    photo = State()
    quantity = State()
    username = State()
    promo = State()

class AddPromo(StatesGroup):
    code = State()
    limit = State()
    discount = State()

# Промокоды
promocodes = {}

def add_promo(code: str, limit: int, discount: int):
    promocodes[code.upper()] = {"limit": limit, "used": 0, "discount": discount}

def check_promo(code: str):
    code = code.upper()
    if code in promocodes:
        promo = promocodes[code]
        if promo["used"] < promo["limit"]:
            promo["used"] += 1
            return True, promo["discount"]
    return False, 0

add_promo("TEST10", 5, 10)

# ========== КНОПКИ ==========
def main_keyboard(user_id: int):
    keyboard = [
        [KeyboardButton(text="📝 Заполнить заявку")],
        [KeyboardButton(text="👤 Мой профиль")]
    ]
    if user_id in ADMIN_IDS:
        keyboard.append([KeyboardButton(text="➕ Добавить промокод")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def get_status_emoji(status):
    if status == "pending":
        return "⏳"
    elif status == "paid":
        return "💳"
    elif status == "completed":
        return "✅"
    elif status == "cancelled":
        return "❌"
    return "📦"

# ========== ПРОФИЛЬ ==========
@dp.message(F.text == "👤 Мой профиль")
async def show_profile(message: Message):
    orders = load_orders()
    user_orders = [o for o in orders if o.get("user_id") == message.from_user.id]
    
    status_counts = {"pending": 0, "paid": 0, "completed": 0, "cancelled": 0}
    for o in user_orders:
        status = o.get("status", "pending")
        status_counts[status] = status_counts.get(status, 0) + 1
    
    text = (
        f"👤 Ваш профиль\n\n"
        f"📦 Всего заказов: {len(user_orders)}\n\n"
        f"📊 Статусы:\n"
        f"   ⏳ В обработке: {status_counts.get('pending', 0)}\n"
        f"   💳 Оплачено: {status_counts.get('paid', 0)}\n"
        f"   ✅ Выполнено: {status_counts.get('completed', 0)}\n"
        f"   ❌ Отменено: {status_counts.get('cancelled', 0)}"
    )
    await message.answer(text, reply_markup=main_keyboard(message.from_user.id))

# ========== ЗАЯВКА ==========
@dp.message(F.text == "📝 Заполнить заявку")
async def start_order(message: Message, state: FSMContext):
    await state.set_state(OrderForm.game)
    await message.answer("🎮 Шаг 1/6: Введите название игры")

@dp.message(OrderForm.game)
async def process_game(message: Message, state: FSMContext):
    await state.update_data(game=message.text)
    await state.set_state(OrderForm.item)
    await message.answer("📦 Шаг 2/6: Введите название товара")

@dp.message(OrderForm.item)
async def process_item(message: Message, state: FSMContext):
    await state.update_data(item=message.text)
    await state.set_state(OrderForm.photo)
    await message.answer("🖼️ Шаг 3/6: Пришлите фото товара")

@dp.message(OrderForm.photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await state.set_state(OrderForm.quantity)
    await message.answer("🔢 Шаг 4/6: Введите количество")

@dp.message(OrderForm.photo)
async def process_photo_invalid(message: Message):
    await message.answer("❌ Отправьте фото!")

@dp.message(OrderForm.quantity)
async def process_quantity(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Введите число!")
        return
    await state.update_data(quantity=int(message.text))
    await state.set_state(OrderForm.username)
    await message.answer("👤 Шаг 5/6: Введите ваш Telegram username (без @)")

@dp.message(OrderForm.username)
async def process_username(message: Message, state: FSMContext):
    username = message.text.strip().lstrip('@')
    await state.update_data(username=username)
    await state.set_state(OrderForm.promo)
    await message.answer("🎟️ Шаг 6/6: Введите промокод (если нет — напишите «нет»)")

@dp.message(OrderForm.promo)
async def process_promo(message: Message, state: FSMContext):
    promo_code = message.text.strip().upper()
    if promo_code in ["НЕТ", "NO", "SKIP"]:
        await state.update_data(promo_used=None, discount=0)
        await finish_order(message, state)
        return
    
    valid, discount = check_promo(promo_code)
    if valid:
        await state.update_data(promo_used=promo_code, discount=discount)
        await message.answer(f"✅ Промокод {promo_code} активирован! Скидка: {discount}%")
        await finish_order(message, state)
    else:
        await message.answer("❌ Промокод недействителен. Введите другой или напишите «нет»")

async def finish_order(message: Message, state: FSMContext):
    data = await state.get_data()
    
    order_number = get_next_order_number(message.from_user.id)
    order_id = str(order_number)
    
    order = {
        "order_id": order_id,
        "user_id": message.from_user.id,
        "username": data['username'],
        "game": data['game'],
        "item": data['item'],
        "quantity": data['quantity'],
        "discount": data.get('discount', 0),
        "promo_used": data.get('promo_used'),
        "status": "pending",
        "date": datetime.now().isoformat(),
        "photo": data.get('photo')
    }
    
    orders = load_orders()
    orders.append(order)
    save_orders(orders)
    
    await send_order_to_group(order)
    
    await message.answer(
        f"✅ Ваш заказ принят!\n\n"
        f"Номер заказа: #{order_id}\n\n"
        f"Скоро с вами свяжется администратор.\n"
        f"Спасибо, что выбрали нас! 🎮",
        reply_markup=main_keyboard(message.from_user.id)
    )
    
    await state.clear()

async def send_order_to_group(order):
    status_emoji = get_status_emoji(order['status'])
    
    # Формируем текст с заголовком в зависимости от статуса
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
    if order.get('discount', 0) > 0:
        body += f"🎟️ Промокод: {order['promo_used']} (скидка {order['discount']}%)\n"
    
    body += f"\n👤 Покупатель: @{order['username']}\n"
    body += f"🕒 Время: {datetime.fromisoformat(order['date']).strftime('%d.%m.%Y %H:%M:%S')}"
    
    text = header + body
    
    # КНОПКИ: НЕ пропадают после "оплачено", пропадают только после "выполнено" и "отмена"
    keyboard = []
    if order['status'] == "pending":
        keyboard = [
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_{order['order_id']}"),
                InlineKeyboardButton(text="💳 Оплачено", callback_data=f"paid_{order['order_id']}"),
                InlineKeyboardButton(text="✅ Выполнено", callback_data=f"complete_{order['order_id']}")
            ]
        ]
    elif order['status'] == "paid":
        # После оплаты оставляем только кнопку "Выполнено"
        keyboard = [
            [
                InlineKeyboardButton(text="✅ Выполнено", callback_data=f"complete_{order['order_id']}")
            ]
        ]
    # Если статус completed или cancelled — кнопок нет
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None
    
    if order.get('message_id'):
        try:
            await bot.edit_message_text(
                chat_id=ADMIN_GROUP_ID,
                message_id=order['message_id'],
                text=text,
                reply_markup=markup
            )
        except Exception as e:
            print(f"Ошибка редактирования: {e}")
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

# ========== ОБРАБОТКА КНОПОК ==========
@dp.callback_query(lambda c: c.data.startswith(('cancel_', 'paid_', 'complete_')))
async def process_order_action(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return
    
    action, order_id = callback.data.split('_', 1)
    order = get_order_by_id(order_id)
    
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    
    user_id = order['user_id']
    
    if action == 'cancel':
        new_status = 'cancelled'
        user_message = "❌ Ваш заказ был отменён администратором.\n\nЕсли у вас есть вопросы, свяжитесь с нами."
        admin_message = "❌ Заказ отменён"
    elif action == 'paid':
        new_status = 'paid'
        user_message = "💳 Ваш заказ оплачен!\n\nСпасибо за доверие! Скоро мы свяжемся с вами для уточнения деталей.\n\nПо всем вопросам: @ваш_админ"
        admin_message = "💳 Заказ оплачен"
    elif action == 'complete':
        new_status = 'completed'
        user_message = "✅ Ваш заказ выполнен!\n\nСпасибо за покупку! Ждём вас снова 🎮\n\nЕсли остались вопросы — обращайтесь."
        admin_message = "✅ Заказ выполнен"
    else:
        return
    
    update_order_status(order_id, new_status)
    order['status'] = new_status
    
    await send_order_to_group(order)
    
    # Уведомляем покупателя
    try:
        await bot.send_message(
            user_id,
            f"{user_message}\n\n📦 Заказ #{order_id}\n🎮 {order['game']} | {order['item']}\n🔢 Количество: {order['quantity']}"
        )
    except:
        pass
    
    await callback.answer(admin_message)
    
    # Убираем кнопки у callback-сообщения
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except:
        pass

# ========== АДМИН: ПРОМОКОДЫ ==========
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
    add_promo(data['code'], data['limit'], int(discount))
    await message.answer(f"✅ Промокод {data['code']} добавлен!\n📊 Лимит: {data['limit']}\n🎯 Скидка: {discount}%")
    await state.clear()

@dp.message(Command("list_promo"))
async def list_promos(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет прав")
        return
    if not promocodes:
        await message.answer("Нет активных промокодов")
        return
    text = "📋 Список промокодов:\n\n"
    for code, data in promocodes.items():
        text += f"• {code} — {data['used']}/{data['limit']} использований, скидка {data['discount']}%\n"
    await message.answer(text)

# ========== КОМАНДА /start ==========
@dp.message(Command("start"))
async def cmd_start(message: Message):
    links_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Наш канал", url=CHANNEL_LINK)]
    ])
    await message.answer(
        "🎮 Добро пожаловать в магазин!\n\n"
        "📝 Заполните заявку — и мы свяжемся с вами\n"
        "👤 В профиле можно посмотреть историю заказов\n\n"
        "🔗 Полезные ссылки:",
        reply_markup=links_kb
    )
    await message.answer(
        "📋 Главное меню",
        reply_markup=main_keyboard(message.from_user.id)
    )

# ========== ЗАПУСК ==========
async def main():
    print("🤖 Бот запущен!")
    print(f"Администраторы: {ADMIN_IDS}")
    print(f"Группа заказов: {ADMIN_GROUP_ID}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
