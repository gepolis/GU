import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
import requests
bot = Bot(token="7265152642:AAFpcGe1PLizHrsaq9ir3Sma22U9MDAnZNA")
dp = Dispatcher()
def gen_auth_url(user_id, username):
    req = requests.get("https://gepolis-gu-7624.twc1.net/gen_auth/{0}/{1}".format(user_id, user_id))
    return req.json()['code']
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    code = gen_auth_url(message.from_user.id, message.from_user.username if message.from_user.username else "None")
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