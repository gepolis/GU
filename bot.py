import asyncio
import aiohttp
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
from aiogram.types import ReplyKeyboardRemove

# Настройки бота
#bot = Bot(token="7483718419:AAHlF2ihnQ-l6nLtn94oT3mNAaG_IqGoST4")
bot = Bot(token="7707847470:AAGJmprISRa2Q_eTYTDMNZyNwmcy0uAeP8c")
dp = Dispatcher()
ADMINS = [2015460473, 8068306751]  # Ваши ID администраторов
CHANNEL_ID = -1002444630943  # ID вашего канала
SUPPORT_USERNAME = "@GU_AppSupport"  # Юзернейм поддержки
AUTH_URL = "https://gosuslugi.com.ru/gen_auth"
USERS_API_URL = "https://gosuslugi.com.ru/admin/json/users"

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Эмодзи для оформления
EMOJI = {
    "lock": "🔐",
    "key": "🔑",
    "tools": "🛠",
    "feedback": "📝",
    "users": "👥",
    "broadcast": "📢",
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "fire": "🔥",
    "refresh": "🔄",
    "star": "⭐",
    "mail": "✉️",
    "chart": "📊",
    "clock": "⏳",
    "search": "🔍",
    "star": "🌟"
}

import aiohttp

API_BASE = "http://127.0.0.1:5000"  # поменяй на нужный адрес


async def get_user_tasks(user_id: int):
    url = f"{API_BASE}/api/tasks/{user_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            # предположим, что API возвращает список заданий в формате
            # [{"id":1, "description":"...", "url_id":-10012345}, ...]
            print(data)
            return data
from aiogram.utils.keyboard import InlineKeyboardBuilder

@dp.message(Command("tasks"))
async def show_tasks(message: types.Message):
    user_id = message.from_user.id
    tasks = await get_user_tasks(user_id)
    if not tasks:
        await message.answer("Заданий для вас нет.")
        return

    kb = InlineKeyboardBuilder()
    for task in tasks:
        kb.add(
            types.InlineKeyboardButton(
                text=task.get("description", "Задание"),
                callback_data=f"show_task:{task['id']}"
            )
        )
    await message.answer("Доступные задания:", reply_markup=kb.as_markup())
@dp.callback_query(lambda c: c.data and c.data.startswith("show_task:"))
async def show_task_detail(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    task_id = int(callback.data.split(":")[1])

    tasks = await get_user_tasks(user_id)
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        await callback.answer("Задание не найдено.", show_alert=True)
        return

    text = (
        f"✨ <b>{task.get('title', 'Задание')}</b>\n\n"
        f"📝 <b>Описание:</b>\n{task.get('description', 'Описание отсутствует')}\n\n"
        f"🎁 <b>Награда:</b> <b>{task.get('reward', 0)}</b> скрытий"
    )


    kb = InlineKeyboardBuilder()
    kb.row(
        types.InlineKeyboardButton(
            text="Перейти",
            url=task.get("url")
        )
    )
    kb.row(types.InlineKeyboardButton(
        text="✅ Проверить",
        callback_data=f"check_task:{task['id']}"
    ))
    kb.row(
        types.InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="back_to_tasks"
        )
    )

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.as_markup())
    await callback.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith("check_task:"))
async def check_task_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    task_id = int(callback.data.split(":")[1])

    # Получаем задания заново, чтобы найти нужное
    tasks = await get_user_tasks(user_id)
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        await callback.answer("⚠️ Задание не найдено. Попробуйте обновить или выбрать другое.", show_alert=True)
        return

    # Проверяем подписку на канал с url_id
    url_id = task.get("url_id")
    try:
        member = await bot.get_chat_member(url_id, user_id)
        if member.status not in ["member", "administrator", "creator"]:
            await callback.answer("⚠️ Вы ещё не подписаны на канал.", show_alert=True)
            return
    except Exception as e:
        await callback.answer(f"Ошибка проверки: {e}", show_alert=True)
        return

    # Отправляем запрос на API о выполнении задания
    async with aiohttp.ClientSession() as session:
        try:
            complete_url = f"{API_BASE}/api/tasks/complete"
            resp = await session.post(complete_url, json={"user_id": user_id, "task_id": task_id})
            if resp.status == 200:
                data = await resp.json()
                if data.get("status") == "success":
                    await callback.answer("Задание успешно выполнено! Ваш приз уже на аккаунте", show_alert=True)
                else:
                    await callback.answer(f"Ошибка API: {data.get('message', 'неизвестно')}", show_alert=True)
            else:
                await callback.answer(f"Ошибка сервера: {resp.status}", show_alert=True)
        except Exception as e:
            await callback.answer(f"Ошибка запроса к API: {e}", show_alert=True)
@dp.callback_query(lambda c: c.data == "back_to_tasks")
async def back_to_tasks_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    tasks = await get_user_tasks(user_id)
    if not tasks:
        await callback.message.edit_text("<b>Подписывайтесь на каналы наших партнёров и получайте Скрытия!</b> \n\n<i>Сейчас заданий нет — загляните позже.</i>", reply_markup=None, parse_mode="HTML")
        await callback.answer()
        return

    kb = InlineKeyboardBuilder()
    for task in tasks:
        kb.add(
            types.InlineKeyboardButton(
                text=task.get("description", "Задание"),
                callback_data=f"show_task:{task['id']}"
            )
        )
    await callback.message.edit_text("<b>Подписывайтесь на каналы наших партнёров и получайте Скрытия! </b>\n\nДоступные задания:", reply_markup=kb.as_markup(), parse_mode="HTML")
    await callback.answer()

# Состояния
class BroadcastStates(StatesGroup):
    waiting_for_message = State()
    confirm_sending = State()


class FeedbackStates(StatesGroup):
    waiting_for_rating = State()
    waiting_for_comment = State()


async def notify_admins(message: str):
    """Отправка уведомлений всем админам"""
    for admin_id in ADMINS:
        try:
            await bot.send_message(
                admin_id,
                message,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Failed to send admin notification to {admin_id}: {str(e)}")


async def gen_auth_url(user_id: int, username: str) -> str:
    """Генерация кода авторизации"""
    url = f"{AUTH_URL}/{user_id}/{username}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    error_message = (
                        f"{EMOJI['fire']} <b>Ошибка генерации кода</b>\n\n"
                        f"<b>• User ID:</b> <code>{user_id}</code>\n"
                        f"<b>• Username:</b> @{username or 'нет'}\n"
                        f"<b>• Status:</b> {resp.status}\n"
                        f"<b>• Error:</b> <code>{error_text[:200]}</code>\n"
                        f"<b>• URL:</b> <code>{url}</code>"
                    )
                    await notify_admins(error_message)
                    return None

                data = await resp.json()
                code = data.get('code')
                if code:
                    success_message = (
                        f"{EMOJI['success']} <b>Новый код авторизации</b>\n\n"
                        f"<b>• User ID:</b> <code>{user_id}</code>\n"
                        f"<b>• Username:</b> @{username or 'нет'}\n"
                        f"<b>• Код:</b> <code>{code}</code>\n"
                        f"<b>• Время:</b> {datetime.now().strftime('%H:%M:%S')}"
                    )
                    await notify_admins(success_message)
                return code
    except Exception as e:
        error_message = (
            f"{EMOJI['fire']} <b>Критическая ошибка</b>\n\n"
            f"<b>• User ID:</b> <code>{user_id}</code>\n"
            f"<b>• Username:</b> @{username or 'нет'}\n"
            f"<b>• Ошибка:</b> <code>{str(e)}</code>\n"
            f"<b>• Тип:</b> {type(e).__name__}"
        )
        await notify_admins(error_message)
        return None


def create_main_menu(user_id: int) -> types.InlineKeyboardMarkup:
    """Создает красивое главное меню"""
    builder = InlineKeyboardBuilder()

    # Основные кнопки
    builder.row(
        types.InlineKeyboardButton(
            text=f"{EMOJI['key']} Получить код",
            callback_data="get_code"
        )
    )
    builder.row(
        types.InlineKeyboardButton(
            text=f"{EMOJI['tools']} Поддержка",
            url=f"https://t.me/{SUPPORT_USERNAME[1:]}"
        ),
        types.InlineKeyboardButton(
            text=f"{EMOJI['feedback']} Оценить бота",
            callback_data="leave_feedback"
        )
    )
    builder.row(
        types.InlineKeyboardButton(
            text=f"{EMOJI['star']} Задания",
            callback_data="back_to_tasks"
        )
    )

    # Админ-кнопки
    if user_id in ADMINS:
        builder.row(
            types.InlineKeyboardButton(
                text=f"{EMOJI['users']} Проверить подписки",
                callback_data="check_all_subs"
            ),
            types.InlineKeyboardButton(
                text=f"{EMOJI['broadcast']} Рассылка",
                callback_data="start_broadcast"
            )
        )

    return builder.as_markup()


async def check_subscription(user_id: int) -> bool:
    """Проверка подписки на канал"""
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Ошибка проверки подписки: {str(e)}")
        return False


async def get_all_users() -> list:
    """Получение списка пользователей через API"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(USERS_API_URL, timeout=30) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"API error {resp.status}: {error_text[:200]}")
                    return []

                if 'application/json' not in resp.headers.get('Content-Type', ''):
                    error_text = await resp.text()
                    logger.error(f"Invalid content type: {error_text[:200]}")
                    return []

                users = await resp.json()
                if not isinstance(users, list):
                    logger.error(f"Invalid data format: {type(users)}")
                    return []

                return users
    except Exception as e:
        logger.error(f"Failed to get users: {str(e)}")
        return []


@dp.message(Command("start", "menu"))
async def cmd_start(message: types.Message):
    """Обработка команды /start с красивым оформлением"""
    user = message.from_user

    # Красивое приветственное сообщение
    welcome_text = (
        f"{EMOJI['lock']} <b>Добро пожаловать, {user.first_name}!</b>\n\n"
        "Я - ваш помощник в доступе к системе. Вот что я могу:\n\n"
        f"<i>Важно: данный сервис не является государственным "
        "учреждением или официальным сервисом.</i>"
    )


    # Проверка подписки
    if not await check_subscription(user.id):
        await message.answer(
            f"{EMOJI['warning']} <b>Требуется подписка</b>\n\n"
            "Для доступа к функциям бота необходимо подписаться на наш канал:",
            parse_mode="HTML",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[[
                    types.InlineKeyboardButton(
                        text=f"{EMOJI['success']} Подписаться на канал",
                        url="https://t.me/+d12Zmm2AvFhiMzAy"
                    )
                ]]
            )
        )
        return

    # Отправка красивого меню
    await message.answer(
        welcome_text,
        parse_mode="HTML",
        reply_markup=create_main_menu(user.id)
    )


@dp.callback_query(lambda c: c.data == "get_code")
async def process_get_code(callback: types.CallbackQuery):
    """Генерация кода авторизации с красивым оформлением"""
    user = callback.from_user

    # Проверка подписки
    if not await check_subscription(user.id):
        await callback.answer(
            f"{EMOJI['error']} Вы не подписаны на канал",
            show_alert=True
        )
        return

    await callback.answer(f"{EMOJI['clock']} Генерируем код...")

    # Уведомление админам
    request_info = (
        f"{EMOJI['refresh']} <b>Запрос кода</b>\n\n"
        f"<b>• User ID:</b> <code>{user.id}</code>\n"
        f"<b>• Username:</b> @{user.username or 'нет'}\n"
        f"<b>• Имя:</b> {user.full_name}\n"
        f"<b>• Время:</b> {datetime.now().strftime('%H:%M:%S')}"
    )
    await notify_admins(request_info)

    # Генерация кода
    code = await gen_auth_url(user.id, user.username or str("None"))
    if not code:
        await callback.message.answer(
            f"{EMOJI['error']} <b>Ошибка генерации кода</b>\n\n"
            "Пожалуйста, попробуйте позже или обратитесь в поддержку.",
            parse_mode="HTML"
        )
        return

    # Красивое сообщение с кодом
    await callback.message.answer(
        f"{EMOJI['key']} <b>Ваш код авторизации:</b>\n\n"
        f"<code>{code}</code>\n\n"
        f"{EMOJI['warning']} <i>Никому не сообщайте этот код!</i>",
        parse_mode="HTML"
    )


@dp.callback_query(lambda c: c.data == "check_all_subs")
async def check_all_subscriptions(callback: types.CallbackQuery):
    """Проверка подписок с красивым прогресс-баром"""
    if callback.from_user.id not in ADMINS:
        return

    await callback.answer(f"{EMOJI['clock']} Начинаем проверку...")

    users = await get_all_users()
    if not users:
        await callback.message.answer(
            f"{EMOJI['error']} <b>Ошибка</b>\nНе удалось получить список пользователей",
            parse_mode="HTML"
        )
        return

    total = len(users)
    subscribed = 0
    not_subscribed = 0
    errors = 0

    # Красивое сообщение о начале проверки
    progress_msg = await callback.message.answer(
        f"{EMOJI['search']} <b>Проверка подписок</b>\n\n"
        f"<b>Всего пользователей:</b> {total}\n"
        "Прогресс: [░░░░░░░░░░] 0%\n"
        f"{EMOJI['success']} Подписаны: 0\n"
        f"{EMOJI['error']} Не подписаны: 0\n"
        f"{EMOJI['warning']} Ошибки: 0",
        parse_mode="HTML"
    )

    # Процесс проверки
    for i, user in enumerate(users, 1):
        try:
            user_id = user.get('user_id')
            if not user_id:
                continue

            is_subscribed = await check_subscription(user_id)
            if is_subscribed:
                subscribed += 1
            else:
                not_subscribed += 1
        except Exception as e:
            errors += 1
            logger.error(f"Ошибка проверки пользователя {user_id}: {str(e)}")

        # Обновление прогресс-бара
        if i % 10 == 0 or i == total:
            progress = int(i / total * 100)
            bars = '█' * (progress // 10)
            spaces = '░' * (10 - len(bars))

            await progress_msg.edit_text(
                f"{EMOJI['search']} <b>Проверка подписок</b>\n\n"
                f"<b>Всего пользователей:</b> {total}\n"
                f"Прогресс: [{bars}{spaces}] {progress}%\n"
                f"{EMOJI['success']} Подписаны: {subscribed}\n"
                f"{EMOJI['error']} Не подписаны: {not_subscribed}\n"
                f"{EMOJI['warning']} Ошибки: {errors}",
                parse_mode="HTML"
            )

    # Красивый финальный отчет
    result_message = (
        f"{EMOJI['chart']} <b>Результаты проверки</b>\n\n"
        f"<b>• Всего пользователей:</b> {total}\n"
        f"<b>• {EMOJI['success']} Подписаны:</b> {subscribed}\n"
        f"<b>• {EMOJI['error']} Не подписаны:</b> {not_subscribed}\n"
        f"<b>• {EMOJI['warning']} Ошибки:</b> {errors}\n\n"
        f"<b>Охват аудитории:</b> {round(subscribed / total * 100 if total > 0 else 0, 1)}%"
    )

    await progress_msg.edit_text(result_message, parse_mode="HTML")


# ========== КРАСИВАЯ СИСТЕМА FEEDBACK ==========

@dp.callback_query(lambda c: c.data == "leave_feedback")
async def start_feedback(callback: types.CallbackQuery, state: FSMContext):
    """Красивый запуск системы отзывов"""
    await callback.answer()

    # Создаем клавиатуру с оценками
    rating_kb = ReplyKeyboardBuilder()
    for i in range(1, 6):
        rating_kb.add(types.KeyboardButton(text=f"{i}"))

    await callback.message.answer(
        f"{EMOJI['feedback']} <b>Оцените наш сервис</b>\n\n"
        "Пожалуйста, поставьте оценку от 1 до 5:\n"
        "1 - Плохо, 5 - Отлично",
        parse_mode="HTML",
        reply_markup=rating_kb.as_markup(resize_keyboard=True)
    )
    await state.set_state(FeedbackStates.waiting_for_rating)


@dp.message(FeedbackStates.waiting_for_rating)
async def process_rating(message: types.Message, state: FSMContext):
    """Обработка оценки с красивым оформлением"""
    if not message.text or not message.text[0].isdigit() or int(message.text[0]) not in range(1, 6):
        await message.answer(
            f"{EMOJI['error']} Пожалуйста, выберите оценку от 1 до 5",
            reply_markup=types.ReplyKeyboardRemove()
        )
        return

    rating = int(message.text[0])
    await state.update_data(rating=rating)

    # Создаем inline-кнопку для пропуска
    skip_kb = InlineKeyboardBuilder()
    skip_kb.add(types.InlineKeyboardButton(
        text=f"{EMOJI['success']} Пропустить комментарий",
        callback_data="skip_comment"
    ))

    await message.answer(
        f"{EMOJI['mail']} <b>Спасибо за оценку!</b>\n\n"
        "Хотите оставить комментарий? (необязательно)\n"
        "Напишите ваше мнение или нажмите кнопку ниже:",
        parse_mode="HTML",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await message.answer(
        "Ваш комментарий:",
        reply_markup=skip_kb.as_markup()
    )
    await state.set_state(FeedbackStates.waiting_for_comment)


@dp.callback_query(FeedbackStates.waiting_for_comment, lambda c: c.data == "skip_comment")
async def skip_comment(callback: types.CallbackQuery, state: FSMContext):
    """Пропуск комментария с уведомлением админов"""
    data = await state.get_data()
    rating = data.get('rating', '?')
    user = callback.from_user

    feedback_msg = (
        f"{EMOJI['star']} <b>Новый отзыв</b>\n\n"
        f"<b>• Оценка:</b> {'⭐' * int(rating)} ({rating}/5)\n"
        f"<b>• User ID:</b> <code>{user.id}</code>\n"
        f"<b>• Username:</b> @{user.username or 'нет'}\n"
        f"<b>• Имя:</b> {user.full_name}\n"
        f"<b>• Время:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"<b>• Комментарий:</b> <i>не указан</i>"
    )

    await notify_admins(feedback_msg)
    await callback.message.edit_text(
        f"{EMOJI['success']} <b>Спасибо за вашу оценку!</b>\n\n"
        "Ваше мнение очень важно для нас!",
        parse_mode="HTML"
    )
    await state.clear()


@dp.message(FeedbackStates.waiting_for_comment)
async def process_comment(message: types.Message, state: FSMContext):
    """Обработка комментария с красивым оформлением"""
    data = await state.get_data()
    rating = data.get('rating', '?')
    user = message.from_user

    feedback_msg = (
        f"{EMOJI['star']} <b>Новый отзыв</b>\n\n"
        f"<b>• Оценка:</b> {'⭐' * int(rating)} ({rating}/5)\n"
        f"<b>• User ID:</b> <code>{user.id}</code>\n"
        f"<b>• Username:</b> @{user.username or 'нет'}\n"
        f"<b>• Имя:</b> {user.full_name}\n"
        f"<b>• Время:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"<b>• Комментарий:</b> <i>{message.text}</i>"
    )

    await notify_admins(feedback_msg)
    await message.answer(
        f"{EMOJI['success']} <b>Спасибо за ваш отзыв!</b>\n\n"
        "Мы ценим ваше мнение и учтем его при улучшении сервиса.",
        parse_mode="HTML"
    )
    await state.clear()


# ========== КРАСИВАЯ СИСТЕМА РАССЫЛКИ ==========

@dp.callback_query(lambda c: c.data == "start_broadcast")
async def start_broadcast_handler(callback: types.CallbackQuery, state: FSMContext):
    """Красивый запуск рассылки"""
    if callback.from_user.id not in ADMINS:
        return

    await callback.message.answer(
        f"{EMOJI['broadcast']} <b>Создание рассылки</b>\n\n"
        "Пожалуйста, отправьте сообщение, которое хотите разослать:\n"
        "(текст, фото, видео или документ)",
        parse_mode="HTML"
    )
    await state.set_state(BroadcastStates.waiting_for_message)
    await callback.answer()


@dp.message(BroadcastStates.waiting_for_message)
async def process_broadcast_message(message: types.Message, state: FSMContext):
    """Обработка сообщения для рассылки с предпросмотром"""
    await state.update_data(broadcast_message=message)

    preview_text = f"{EMOJI['mail']} <b>Предпросмотр рассылки:</b>\n\n"
    if message.text:
        preview_text += message.text
    elif message.caption:
        preview_text += message.caption
    else:
        preview_text += "Медиа-сообщение"

    # Красивые кнопки подтверждения
    kb = InlineKeyboardBuilder()
    kb.row(
        types.InlineKeyboardButton(
            text=f"{EMOJI['success']} Начать рассылку",
            callback_data="confirm_broadcast"
        ),
        types.InlineKeyboardButton(
            text=f"{EMOJI['error']} Отменить",
            callback_data="cancel_broadcast"
        )
    )

    if message.text:
        await message.answer(
            preview_text,
            parse_mode="HTML",
            reply_markup=kb.as_markup()
        )
    else:
        if message.photo:
            await message.answer_photo(
                message.photo[-1].file_id,
                caption=preview_text,
                parse_mode="HTML",
                reply_markup=kb.as_markup()
            )
        elif message.video:
            await message.answer_video(
                message.video.file_id,
                caption=preview_text,
                parse_mode="HTML",
                reply_markup=kb.as_markup()
            )
        elif message.document:
            await message.answer_document(
                message.document.file_id,
                caption=preview_text,
                parse_mode="HTML",
                reply_markup=kb.as_markup()
            )

    await state.set_state(BroadcastStates.confirm_sending)


@dp.callback_query(BroadcastStates.confirm_sending, lambda c: c.data == "confirm_broadcast")
async def confirm_broadcast_handler(callback: types.CallbackQuery, state: FSMContext):
    """Красивое выполнение рассылки с прогресс-баром"""
    data = await state.get_data()
    message = data['broadcast_message']
    await callback.answer(f"{EMOJI['clock']} Начинаем рассылку...")

    users = await get_all_users()
    if not users:
        await callback.message.answer(
            f"{EMOJI['error']} <b>Ошибка</b>\nНе удалось получить список пользователей",
            parse_mode="HTML"
        )
        await state.clear()
        return

    user_ids = [u.get('user_id') for u in users if u.get('user_id')]
    total = len(user_ids)
    success = 0
    failed = 0

    # Красивое сообщение о начале рассылки
    progress_msg = await callback.message.answer(
        f"{EMOJI['broadcast']} <b>Рассылка начата</b>\n\n"
        f"<b>Всего получателей:</b> {total}\n"
        "Прогресс: [░░░░░░░░░░] 0%\n"
        f"{EMOJI['success']} Успешно: 0\n"
        f"{EMOJI['error']} Ошибок: 0",
        parse_mode="HTML"
    )

    # Процесс рассылки
    for i, user_id in enumerate(user_ids, 1):
        try:
            if message.text:
                await bot.send_message(user_id, message.text, parse_mode="HTML")
            elif message.photo:
                await bot.send_photo(user_id, message.photo[-1].file_id, caption=message.caption)
            elif message.video:
                await bot.send_video(user_id, message.video.file_id, caption=message.caption)
            elif message.document:
                await bot.send_document(user_id, message.document.file_id, caption=message.caption)
            success += 1
        except Exception as e:
            logger.error(f"Broadcast failed for {user_id}: {str(e)}")
            failed += 1

        # Обновление прогресс-бара
        if i % 10 == 0 or i == total:
            progress = int(i / total * 100)
            bars = '█' * (progress // 10)
            spaces = '░' * (10 - len(bars))

            await progress_msg.edit_text(
                f"{EMOJI['broadcast']} <b>Рассылка</b>\n\n"
                f"<b>Всего получателей:</b> {total}\n"
                f"Прогресс: [{bars}{spaces}] {progress}%\n"
                f"{EMOJI['success']} Успешно: {success}\n"
                f"{EMOJI['error']} Ошибок: {failed}",
                parse_mode="HTML"
            )

    # Красивый финальный отчет
    result_message = (
        f"{EMOJI['success']} <b>Рассылка завершена!</b>\n\n"
        f"<b>• Всего получателей:</b> {total}\n"
        f"<b>• {EMOJI['success']} Успешно:</b> {success}\n"
        f"<b>• {EMOJI['error']} Ошибок:</b> {failed}\n\n"
        f"<b>Процент доставки:</b> {round(success / total * 100, 1)}%"
    )

    await progress_msg.edit_text(result_message, parse_mode="HTML")
    await state.clear()


@dp.callback_query(BroadcastStates.confirm_sending, lambda c: c.data == "cancel_broadcast")
async def cancel_broadcast_handler(callback: types.CallbackQuery, state: FSMContext):
    """Красивая отмена рассылки"""
    await callback.answer(f"{EMOJI['error']} Рассылка отменена")
    await callback.message.edit_text(
        f"{EMOJI['error']} <b>Рассылка отменена</b>\n\n"
        "Вы можете начать новую рассылку в любое время.",
        parse_mode="HTML"
    )
    await state.clear()


async def main():
    """Запуск бота"""
    logger.info("Starting bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())