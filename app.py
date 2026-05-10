import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
import aiohttp

# ========== ТВОЙ ТОКЕН (ВСТАВЬ СВОЙ) ==========
BOT_TOKEN = "8684547044:AAFduRU_IklCst-ParB4O9Yaxbxc7tqo54s"
# =============================================

ADMIN_GROUP_ID = -1003959266816
ADMIN_IDS = [6209172297, 1852789843]
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyaCxVPrZnm6I8kGNgRtt3Mm5Qa0X5_bDeqH8Tw1hGII4_6fri2JsUQhOGFtvzQSVWEcv/exec"

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

class AddPromo(StatesGroup):
    code = State()
    limit = State()
    discount = State()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def main_keyboard(user_id: int):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📝 Заполнить заявку")]],
        resize_keyboard=True
    )
    if is_admin(user_id):
        keyboard.keyboard.append([KeyboardButton(text="➕ Добавить промокод")])
    return keyboard

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("🎮 Добро пожаловать!", reply_markup=main_keyboard(message.from_user.id))

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
    await state.update_data(quantity=message.text)
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
    async with aiohttp.ClientSession() as session:
        try:
            payload = {"action": "check", "promoCode": promo_code}
            async with session.post(GOOGLE_SCRIPT_URL, json=payload) as resp:
                result = await resp.json()
                if result.get("valid"):
                    discount = result.get("discount", 0)
                    await state.update_data(promo_used=promo_code, discount=discount)
                    await message.answer(f"✅ Промокод **{promo_code}** активирован! Скидка: {discount}%")
                    await finish_order(message, state)
                else:
                    await message.answer("❌ Промокод недействителен или лимит исчерпан. Введите другой или «нет»")
        except:
            await message.answer("⚠️ Ошибка проверки. Продолжим без промокода.")
            await state.update_data(promo_used=None, discount=0)
            await finish_order(message, state)

async def finish_order(message: Message, state: FSMContext):
    data = await state.get_data()
    order_text = f"🆕 НОВЫЙ ЗАКАЗ!\n\n🎮 Игра: {data['game']}\n📦 Товар: {data['item']}\n🔢 Количество: {data['quantity']}\n👤 TG: @{data['username']}"
    if data.get('promo_used'):
        order_text += f"\n🎟️ Промокод: {data['promo_used']} (скидка {data['discount']}%)"
    order_text += f"\n📅 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
    await bot.send_message(ADMIN_GROUP_ID, order_text)
    if data.get('photo'):
        await bot.send_photo(ADMIN_GROUP_ID, data['photo'])
    await message.answer("✅ Ваш заказ принят! Скоро свяжется администратор.", reply_markup=main_keyboard(message.from_user.id))
    await state.clear()

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
    await message.answer("🔢 Введите лимит активаций (цифру)")

@dp.message(AddPromo.limit)
async def admin_add_promo_limit(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Введите число")
        return
    await state.update_data(limit=int(message.text))
    await state.set_state(AddPromo.discount)
    await message.answer("🎯 Введите процент скидки (например: 10)")

@dp.message(AddPromo.discount)
async def admin_add_promo_discount(message: Message, state: FSMContext):
    try:
        discount = float(message.text.replace(',', '.'))
        if discount < 0 or discount > 100:
            await message.answer("❌ Скидка должна быть от 0 до 100")
            return
    except:
        await message.answer("❌ Введите число")
        return
    data = await state.get_data()
    async with aiohttp.ClientSession() as session:
        payload = {"action": "add", "promoCode": data['code'], "limit": data['limit'], "discount": discount}
        await session.post(GOOGLE_SCRIPT_URL, json=payload)
    await message.answer(f"✅ Промокод {data['code']} добавлен! Скидка: {discount}%, Лимит: {data['limit']}")
    await state.clear()

async def main():
    print("🤖 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
