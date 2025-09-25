from aiogram.client.default import DefaultBotProperties
from aiogram.utils.markdown import hide_link
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from aiogram import Bot, Dispatcher, F, Router
import asyncio
import logging
import sqlite3
import sys
import re
from keyboards.keyboards_admins import *
from keyboards.keyboards_user import *
from db import init_db, add_application, add_reply, get_application_data
from states import *
from utils import *
from config import *

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
storage = MemoryStorage()
dp.fsm_storage = storage
router = Router()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
applications = {}

# Инициализация базы данных при запуске
init_db()


# START
@dp.message(Command("start"))
async def handleStart(message: Message, state: FSMContext):
    await state.clear()  # Очищаем состояние при старте
    user_id = message.from_user.id
    is_admin = user_id == ADMIN_ID[0] if ADMIN_ID and isinstance(ADMIN_ID[0], int) else False

    if is_admin:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚗 Выставить машину", callback_data="car"),
             InlineKeyboardButton(text="📦 Перевезти груз", callback_data="cargo")],
            [InlineKeyboardButton(text="🔍 Фильтровать/искать заказы", callback_data="search_orders")]
        ])
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚗 Выставить машину", callback_data="car"),
             InlineKeyboardButton(text="📦 Перевезти груз", callback_data="cargo")]
        ])

    await message.answer(
        text=f"Добро пожаловать! Вы хотите <b>выставить машину</b> или <b>перевезти груз</b>?\n"
             f"Выберите опцию с помощью кнопок ниже.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

# Обработка ввода для поиска
@dp.message(StateFilter(SearchState.search_date))
async def processSearchDate(message: Message, state: FSMContext):
    date = message.text
    if not validate_date(date):
        await message.answer("Неверный формат даты! Используйте ДД.ММ.ГГГГ (например, 25.09.2025). Повторите ввод:")
        return
    await search_applications(message, "date", date)
    await state.clear()

@dp.message(StateFilter(SearchState.search_city))
async def processSearchCity(message: Message, state: FSMContext):
    city = message.text
    await search_applications(message, "city", city)
    await state.clear()

@dp.message(StateFilter(SearchState.search_type))
async def processSearchType(message: Message, state: FSMContext):
    type_car = message.text
    await search_applications(message, "type", type_car)
    await state.clear()

# Функция поиска заявок
async def search_applications(message: Message, filter_type: str, filter_value: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    query = "SELECT * FROM applications"
    params = []
    if filter_type == "date":
        query += " WHERE upload_date = ?"
        params.append(filter_value)
    elif filter_type == "city":
        query += " WHERE cities LIKE ?"
        params.append(f"%{filter_value}%")
    elif filter_type == "type":
        query += " WHERE type_car = ?"
        params.append(filter_value)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await message.answer("⚠️ Заявки не найдены по заданным критериям.")
        return

    response = "Найденные заявки:\n"
    for row in rows:
        response += f"\n<b>ID:</b> {row[0]}\n"
        response += f"<b>Тип:</b> {row[1]}\n"
        response += f"<b>Номер:</b> {row[2]}\n"
        response += f"<b>Дата загрузки:</b> {row[3]}\n"
        response += f"<b>Текущая дата:</b> {row[4]}\n"
        response += f"<b>Города:</b> {row[5]}\n"
        response += f"<b>Тип машины:</b> {row[6]}\n"
        response += f"<b>Менеджер номер:</b> {row[7]}\n"
        response += f"<b>Менеджер имя:</b> {row[8]}\n"
        response += f"<b>Менеджер email:</b> {row[9]}\n"
    await message.answer(response, parse_mode="HTML")

# Обработка возврата к началу
@dp.callback_query(F.data == "back_to_start")
async def handleBackToStart(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await handleStart(callback.message, state)
    await callback.answer()

# Обработка выбора критерия поиска
@dp.callback_query(F.data.startswith("search_by_"))
async def handleSearchBy(callback: CallbackQuery, state: FSMContext):
    criterion = callback.data.replace("search_by_", "")
    logging.info(f"Selected criterion: {criterion}")  # Отладка
    await callback.answer(f"Введите значение для поиска по {criterion}:", show_alert=False)
    await callback.message.edit_reply_markup(reply_markup=None)  # Убираем клавиатуру
    # Устанавливаем состояние, соответствующее SearchState
    state_to_set = getattr(SearchState, f"search_{criterion}", None)
    if state_to_set:
        await state.set_state(state_to_set)
        logging.info(f"Set state to: {state_to_set}")
    else:
        await callback.message.answer("Ошибка: Неизвестный критерий поиска.")
        await callback.answer()

# Обработка поиска заказов (для администратора)
@dp.callback_query(F.data == "search_orders")
async def handleSearchOrders(callback: CallbackQuery):
    search_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 По дате", callback_data="search_by_date")],
        [InlineKeyboardButton(text="🏙 По городу", callback_data="search_by_city")],
        [InlineKeyboardButton(text="🚚 По типу машины", callback_data="search_by_type")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_start")]
    ])
    await callback.answer("Выберите критерий поиска:", show_alert=False)
    await callback.message.edit_text(
        text="Выберите критерий поиска:",
        reply_markup=search_keyboard,
        parse_mode="HTML"
    )
# Обработка выбора критерия поиска
@dp.callback_query(F.data.startswith("search_by_"))
async def handleSearchBy(callback: CallbackQuery, state: FSMContext):
    criterion = callback.data.replace("search_by_", "")
    await callback.answer(f"Введите значение для поиска по {criterion}:", show_alert=False)
    await callback.message.edit_reply_markup(reply_markup=None)  # Убираем клавиатуру
    await state.set_state(f"search_{criterion}")  # Устанавливаем состояние

# Кнопка Машина
@dp.callback_query(F.data == "car")
async def handleCar(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("Введите номер машины (например, 'А123БС77').")
    await state.set_state(CarState.number)

# FSM шаги для машины с валидацией и подсказками
@dp.message(CarState.number)
async def handleCarNumber(message: Message, state: FSMContext):
    await state.update_data(number=message.text)
    await message.answer("Введите дату загрузки (ДД.ММ.ГГГГ, например, 25.09.2025).")
    await state.set_state(CarState.upload_date)

@dp.message(CarState.upload_date)
async def handleCarUploadDate(message: Message, state: FSMContext):
    if not validate_date(message.text):
        await message.answer("Неверный формат даты! Используйте ДД.ММ.ГГГГ (например, 25.09.2025). Повторите ввод:")
        return
    await state.update_data(upload_date=message.text)
    await message.answer("Введите текущую дату (ДД.ММ.ГГГГ, например, 25.09.2025).")
    await state.set_state(CarState.current_date)

@dp.message(CarState.current_date)
async def handleCarCurrentDate(message: Message, state: FSMContext):
    if not validate_date(message.text):
        await message.answer("Неверный формат даты! Используйте ДД.ММ.ГГГГ (например, 25.09.2025). Повторите ввод:")
        return
    await state.update_data(current_date=message.text)
    await message.answer("Введите города маршрута через запятую (например, Москва, Санкт-Петербург).")
    await state.set_state(CarState.cities)

@dp.message(CarState.cities)
async def handleCarCities(message: Message, state: FSMContext):
    await state.update_data(cities=message.text)
    await message.answer("Введите тип машины (например, фура, газель).")
    await state.set_state(CarState.type_car)

@dp.message(CarState.type_car)
async def handleCarTypeCar(message: Message, state: FSMContext):
    await state.update_data(type_car=message.text)
    await message.answer("Введите номер менеджера (+7XXXXXXXXXX, например, +71234567890).")
    await state.set_state(CarState.manager_number)

@dp.message(CarState.manager_number)
async def handleCarManagerNumber(message: Message, state: FSMContext):
    if not validate_phone(message.text):
        await message.answer("Неверный формат телефона! Используйте +7XXXXXXXXXX (например, +71234567890). Повторите ввод:")
        return
    await state.update_data(manager_number=message.text)
    await message.answer("Введите имя менеджера (например, Иван Иванов).")
    await state.set_state(CarState.manager_name)

@dp.message(CarState.manager_name)
async def handleCarManagerName(message: Message, state: FSMContext):
    await state.update_data(manager_name=message.text)
    await message.answer("Введите email менеджера (например, ivan@example.com).")
    await state.set_state(CarState.manager_email)

@dp.message(CarState.manager_email)
async def handleCarManagerEmail(message: Message, state: FSMContext):
    await state.update_data(manager_email=message.text)
    data = await state.get_data()
    await state.update_data(ready_to_send=True)  # Устанавливаем флаг готовности
    text = (
        f"🚗 Данные сохранены:\n"
        f"<b>Номер машины:</b> {data.get('number')}\n"
        f"<b>Дата загрузки:</b> {data.get('upload_date')}\n"
        f"<b>Текущая дата:</b> {data.get('current_date')}\n"
        f"<b>Города:</b> {data.get('cities')}\n"
        f"<b>Тип машины:</b> {data.get('type_car')}\n"
        f"<b>Менеджер номер:</b> {data.get('manager_number')}\n"
        f"<b>Менеджер имя:</b> {data.get('manager_name')}\n"
        f"<b>Менеджер email:</b> {data.get('manager_email')}\n"
        f"Нажмите 'Отправить', чтобы опубликовать заявку."
    )
    await message.answer(text, reply_markup=keyboard_sendorno_users(), parse_mode="HTML")

# Кнопка Груз
@dp.callback_query(F.data == "cargo")
async def handleCargo(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("Введите номер заказа (например, 'ZA123').")
    await state.set_state(CargoState.number)

# FSM шаги для груза
@dp.message(CargoState.number)
async def handleCargoNumber(message: Message, state: FSMContext):
    await state.update_data(number=message.text)
    await message.answer("Введите дату загрузки (ДД.ММ.ГГГГ, например, 25.09.2025).")
    await state.set_state(CargoState.upload_date)

@dp.message(CargoState.upload_date)
async def handleCargoUploadDate(message: Message, state: FSMContext):
    if not validate_date(message.text):
        await message.answer("Неверный формат даты! Используйте ДД.ММ.ГГГГ (например, 25.09.2025). Повторите ввод:")
        return
    await state.update_data(upload_date=message.text)
    await message.answer("Введите текущую дату (ДД.ММ.ГГГГ, например, 25.09.2025).")
    await state.set_state(CargoState.current_date)

@dp.message(CargoState.current_date)
async def handleCargoCurrentDate(message: Message, state: FSMContext):
    if not validate_date(message.text):
        await message.answer("Неверный формат даты! Используйте ДД.ММ.ГГГГ (например, 25.09.2025). Повторите ввод:")
        return
    await state.update_data(current_date=message.text)
    await message.answer("Введите города маршрута через запятую (например, Москва, Санкт-Петербург).")
    await state.set_state(CargoState.cities)

@dp.message(CargoState.cities)
async def handleCargoCities(message: Message, state: FSMContext):
    await state.update_data(cities=message.text)
    await message.answer("Введите тип машины (например, фура, газель).")
    await state.set_state(CargoState.type_car)

@dp.message(CargoState.type_car)
async def handleCarTypeCar(message: Message, state: FSMContext):
    await state.update_data(type_car=message.text)
    await message.answer("Введите номер менеджера (+7XXXXXXXXXX, например, +71234567890).")
    await state.set_state(CargoState.manager_number)

@dp.message(CargoState.manager_number)
async def handleCargoManagerNumber(message: Message, state: FSMContext):
    if not validate_phone(message.text):
        await message.answer("Неверный формат телефона! Используйте +7XXXXXXXXXX (например, +71234567890). Повторите ввод:")
        return
    await state.update_data(manager_number=message.text)
    await message.answer("Введите имя менеджера (например, Иван Иванов).")
    await state.set_state(CargoState.manager_name)

@dp.message(CargoState.manager_name)
async def handleCargoManagerName(message: Message, state: FSMContext):
    await state.update_data(manager_name=message.text)
    await message.answer("Введите email менеджера (например, ivan@example.com).")
    await state.set_state(CargoState.manager_email)

@dp.message(CargoState.manager_email)
async def handleCargoManagerEmail(message: Message, state: FSMContext):
    await state.update_data(manager_email=message.text)
    data = await state.get_data()
    await state.update_data(ready_to_send=True)  # Устанавливаем флаг готовности
    text = (
        f"📦 Данные сохранены:\n"
        f"<b>Номер заказа:</b> {data.get('number')}\n"
        f"<b>Дата загрузки:</b> {data.get('upload_date')}\n"
        f"<b>Текущая дата:</b> {data.get('current_date')}\n"
        f"<b>Города:</b> {data.get('cities')}\n"
        f"<b>Тип машины:</b> {data.get('type_car')}\n"
        f"<b>Менеджер номер:</b> {data.get('manager_number')}\n"
        f"<b>Менеджер имя:</b> {data.get('manager_name')}\n"
        f"<b>Менеджер email:</b> {data.get('manager_email')}\n"
        f"Нажмите 'Отправить', чтобы опубликовать заявку."
    )
    await message.answer(text, reply_markup=keyboard_sendorno_users(), parse_mode="HTML")

# Отправка заявки в группу с сохранением в базу
@dp.callback_query(F.data == "send")
async def handleSend(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_state = await state.get_state()
    user_id = callback.from_user.id

    # Проверка флага готовности
    if not data.get("ready_to_send"):
        restart_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Начать заново", callback_data="start_over")]
        ])
        await callback.message.answer(
            "⚠️ Ошибка: Заявка не готова к отправке. Пожалуйста, начните процесс заново.",
            reply_markup=restart_markup
        )
        return

    app_type = "car" if "CarState" in current_state else "cargo"

    # Сохранение в базу данных
    app_id = add_application(data, user_id, app_type)

    if "CarState" in current_state:
        text = (
            f"🚗 <b>Новая заявка на машину</b>\n\n"
            f"<b>Номер машины:</b> {data.get('number')}\n"
            f"<b>Дата загрузки:</b> {data.get('upload_date')}\n"
            f"<b>Текущая дата:</b> {data.get('current_date')}\n"
            f"<b>Города:</b> {data.get('cities')}\n"
            f"<b>Тип машины:</b> {data.get('type_car')}\n"
            f"<b>Менеджер номер:</b> {data.get('manager_number')}\n"
            f"<b>Менеджер имя:</b> {data.get('manager_name')}\n"
            f"<b>Менеджер email:</b> {data.get('manager_email')}"
        )
    else:
        text = (
            f"📦 <b>Новая заявка на груз</b>\n\n"
            f"<b>Номер заказа:</b> {data.get('number')}\n"
            f"<b>Дата загрузки:</b> {data.get('upload_date')}\n"
            f"<b>Текущая дата:</b> {data.get('current_date')}\n"
            f"<b>Города:</b> {data.get('cities')}\n"
            f"<b>Тип машины:</b> {data.get('type_car')}\n"
            f"<b>Менеджер номер:</b> {data.get('manager_number')}\n"
            f"<b>Менеджер имя:</b> {data.get('manager_name')}\n"
            f"<b>Менеджер email:</b> {data.get('manager_email')}"
        )

    # Временный username (замените на реальный или настройте динамически)
    username = callback.from_user.username # Замените на username логиста
    manager_id = ADMIN_ID[0] if ADMIN_ID and isinstance(ADMIN_ID[0], int) else None
    if not manager_id:
        await callback.message.answer("⚠️ Ошибка: Не указан валидный manager_id. Обратитесь к администратору.")
        return

    try:
        sent_msg = await callback.bot.send_message(
            chat_id=GROUP_ID,
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard_ingroup_users(manager_id, username)
        )
    except TelegramBadRequest as e:
        fallback_markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Откликнуться", callback_data="reply")]
            ]
        )
        sent_msg = await callback.bot.send_message(
            chat_id=GROUP_ID,
            text=text,
            parse_mode="HTML",
            reply_markup=fallback_markup
        )
        await callback.message.answer(f"⚠️ Ошибка: {str(e)}. Кнопка 'Чат с логистом' отключена. Проверьте username.")

    # Сохранение данных с использованием app_id как ключа
    applications[app_id] = {"message_id": sent_msg.message_id, **data}
    logging.info(f"Saved application: app_id={app_id}, message_id={sent_msg.message_id}, data={data}")
    await state.clear()  # Очищаем состояние после успешной отправки
    await callback.message.answer("✅ Данные успешно отправлены в группу и сохранены!")
    await callback.answer()

# Обработка команды "Начать заново"
@dp.callback_query(F.data == "start_over")
async def handleStartOver(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer(
        "🔄 Процесс начат заново. Выберите опцию:\n"
        f"Вы хотите <b>выставить машину</b> или <b>перевезти груз</b>?",
        reply_markup=keyboard_start_users(),
        parse_mode="HTML"
    )
    await callback.answer()

# Обработка отклика с сохранением в базу
@dp.callback_query(F.data == "reply")
async def handleReply(callback: CallbackQuery):
    responder = callback.from_user
    message_id = callback.message.message_id
    # Поиск данных по message_id в applications
    data = next((app_data for app_id, app_data in applications.items() if app_data.get("message_id") == message_id), {})
    app_id = data.get("app_id") if data else None

    if app_id:
        add_reply(app_id, responder.id, responder.full_name)

    text_to_manager = (
        f"📦 <b>Новая откликнутая заявка</b>\n\n"
        f"<b>Номер машины/заказа:</b> {data.get('number', 'Не указано')}\n"
        f"<b>Дата загрузки:</b> {data.get('upload_date', 'Не указано')}\n"
        f"<b>Текущая дата:</b> {data.get('current_date', 'Не указано')}\n"
        f"<b>Города:</b> {data.get('cities', 'Не указано')}\n"
        f"<b>Тип машины:</b> {data.get('type_car', 'Не указано')}\n"
        f"<b>Менеджер номер:</b> {data.get('manager_number', 'Не указано')}\n"
        f"<b>Менеджер имя:</b> {data.get('manager_name', 'Не указано')}\n"
        f"<b>Менеджер email:</b> {data.get('manager_email', 'Не указано')}\n\n"
        f"👤 <b>Откликнулся пользователь:</b> {responder.full_name} (ID: {responder.id})\n"
        f"<a href='tg://user?id={responder.id}'>Написать пользователю</a>"
    )
    try:
        # Логирование попытки отправки
        logging.info(f"Attempting to send to ADMIN_ID: {ADMIN_ID[0]}")
        # Отправка сообщения администратору из ADMIN_ID
        await bot.send_message(chat_id=ADMIN_ID[0], text=text_to_manager, parse_mode="HTML", disable_web_page_preview=True)
        await callback.answer("✅ Вы откликнулись! Администратор получит сообщение.", show_alert=True)
    except TelegramBadRequest as e:
        # Логирование ошибки
        logging.error(f"Failed to send to ADMIN_ID: {e}")
        # Отправляем сообщение в группу как резерв
        await bot.send_message(chat_id=GROUP_ID, text=f"⚠️ Ошибка: Не удалось отправить сообщение администратору.\n\n{text_to_manager}", parse_mode="HTML")
        await callback.answer("⚠️ Ошибка: Не удалось уведомить администратора. Сообщение отправлено в группу.", show_alert=True)

# Команда для поиска заказов
@dp.message(Command("search"))
async def handleSearch(message: Message):
    args = message.text.split()[1:]  # Аргументы после /search
    filter_type = args[0] if args else None
    filter_value = args[1] if len(args) > 1 else None

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    query = "SELECT * FROM applications"
    params = []
    if filter_type and filter_value:
        if filter_type.lower() == "date":
            query += " WHERE upload_date = ?"
            params.append(filter_value)
        elif filter_type.lower() == "city":
            query += " WHERE cities LIKE ?"
            params.append(f"%{filter_value}%")
        elif filter_type.lower() == "type":
            query += " WHERE type_car = ?"
            params.append(filter_value)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await message.answer("⚠️ Заявки не найдены по заданным критериям.")
        return

    response = "Найденные заявки:\n"
    for row in rows:
        response += f"\n<b>ID:</b> {row[0]}\n"
        response += f"<b>Тип:</b> {row[1]}\n"
        response += f"<b>Номер:</b> {row[2]}\n"
        response += f"<b>Дата загрузки:</b> {row[3]}\n"
        response += f"<b>Текущая дата:</b> {row[4]}\n"
        response += f"<b>Города:</b> {row[5]}\n"
        response += f"<b>Тип машины:</b> {row[6]}\n"
        response += f"<b>Менеджер номер:</b> {row[7]}\n"
        response += f"<b>Менеджер имя:</b> {row[8]}\n"
        response += f"<b>Менеджер email:</b> {row[9]}\n"
    await message.answer(response, parse_mode="HTML")

async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())