import asyncio
import random

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
import requests
bot = Bot(token="7483718419:AAHlF2ihnQ-l6nLtn94oT3mNAaG_IqGoST4")
#bot = Bot(token="7365277632:AAHWyGDNbtnHbNKZ084X-l0NGDdkXnCcNkU")
dp = Dispatcher()
import aiohttp
import random
import logging

async def gen_auth_url(user_id, username):
    rand_auth_key = str(random.randint(100000, 999999))
    url = f"https://gepolis-gu-7624.twc1.net/gen_auth/{user_id}/{username}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    await bot.send_message(2015460473, f"Ошибка HTTP {resp.status} при запросе к {url}")
                    return None

                data = await resp.json(content_type=None)  # обойти Content-Type ошибки

                code = data.get('code')
                if code:
                    await bot.send_message(
                        2015460473,
                        f"Ответ сервера #{user_id}-{username}-{rand_auth_key}: {code}"
                    )
                    return code
                else:
                    await bot.send_message(
                        2015460473,
                        f"Некорректный JSON-ответ от сервера для {user_id}-{username}: {data}"
                    )
                    return None

    except aiohttp.ClientError as e:
        logging.exception("Ошибка клиента aiohttp")
        await bot.send_message(2015460473, f"Ошибка HTTP-запроса: {e}")

    except Exception as e:
        logging.exception("Неизвестная ошибка в gen_auth_url")
        await bot.send_message(2015460473, "Произошла непредвиденная ошибка при генерации ссылки авторизации")
        await bot.send_message(2015460473, str(e))

    return None



@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    #check subscription on channel -1002444630943
    user_channel_status = await bot.get_chat_member(chat_id=-1002444630943, user_id=message.from_user.id)
    print(user_channel_status)
    print(user_channel_status.status)
    if user_channel_status.status != 'left':
        print("t 1")
        code = await gen_auth_url(message.from_user.id, message.from_user.username if message.from_user.username else "None")
        if not code:
            code = await gen_auth_url(message.from_user.id, message.from_user.username if message.from_user.username else "None")
            if not code:
                await message.answer("Произошла ошибка при генерации кода авторизации.\n\nОбратитесь в поддержку @GU_AppSupport.")
                return
        print("t 2")
        print(code)
        await message.answer(
            "🔐 <b>Добро пожаловать в сервис Госуслуги 2.0!</b> 🔐\n\n"
            "Страница авторизации:\n"
            f"➡️ <a href='https://gepolis-gu-7624.twc1.net/auth'>Войти в личный кабинет</a> ⬅️\n\n"
            "Код для входа: \n"
            f"<code>{code}</code>\n\n"
            "⚠️ Никому не передавайте этот код!",
            parse_mode="HTML"
        )
    else:
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(text="👥 Подписаться на канал", url="https://t.me/+d12Zmm2AvFhiMzAy")
                ]
            ]
        )
        await message.answer("⚠️ Подпишитесь на канал, чтобы получить код авторизации!\n\n👥 <a href='https://t.me/+d12Zmm2AvFhiMzAy'>Подписаться на канал</a>\n\nПосле подписки нажмите /start", reply_markup=kb, parse_mode="HTML")

async def check_auth():
    req = requests.post("http://127.0.0.1:5000/admin/json/users")
    users = req.json()
    left = 0
    for user in users:
        user_channel_status = await bot.get_chat_member(chat_id=-1002444630943, user_id=user['user_id'])
        if user_channel_status.status != 'left':
            print(user['username'], "+")
        else:
            print(user['username'], "-")
            left += 1
    await bot.send_message(2015460473, "Пользователей: {0}\nОтписались: {1}".format(len(users) - left, left))



async def main():
    await check_auth()
    await dp.start_polling(bot)
def run_bot():
    asyncio.set_event_loop(asyncio.new_event_loop())
    asyncio.get_event_loop().run_until_complete(main())

if __name__ == "__main__":
    run_bot()