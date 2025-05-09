
import pyrogram
from pyrogram import enums
from mistralai import Mistral
# Настройки
API_ID = 24456185
API_HASH = 'b78cb5508145cf89c6125c0102107fa7'
SESSION_NAME = 'bot'
MISTRAL_API = "TC68qAH8b8HMzW3DgLZNAbipfiurJ3ly"

bot = pyrogram.Client(SESSION_NAME, API_ID, API_HASH)
mclient = Mistral(api_key=MISTRAL_API)

CHAT_HISTORY = {}
DISABLE_ID_CHATS = []
MISTRAL_AI_SYSTEM_MESSAGE = ("Пиши как живой человек реалистично а не робот. Ответ должен быть короткин но емким. "
                             "Отвечай только на вопросы и предложения на тему приложения или проекта. "
                             "Так же если вопрос касается рекламы то приглашай оператора и отвечай пользователю что прегласил оператора и проси у пользователя информацию о проекте если он ее не скинул. "
                             "Ты чат бот техподдержки ты общаешься с пользователем в офицально деловом стиле."
                             " наш сайт: https://gepolis-gu-7624.twc1.net/ "
                             "Наш тг канал в котором новости и ссылка на скачивание приложения: https://t.me/+d12Zmm2AvFhiMzAy "
                             "Если у пользователя возникает проблема с загрузкой телеграм из нашего приложения "
                             "то он должен его обновить и присылай ссылку на тг канал и обясни что ссылка для скачивания в закрепленном посте. "
                             "Пиши ответ с разделением на строчки. "
                             "Отзывы можно посмотреть в коментариях под постом https://t.me/c/2444630943/8"
                             "Если ты не можешь ответить на вопрос то пиши что приглашаешь оператора и добавь в системные теги OPERATOR"
                             "Для установки данных пользователю нужно нажать на кнопку фотоаппарата в блоке паспорт РФ или открыть ссылку https://gepolis-gu-7624.twc1.net/setup "
                             "создать новый профель данных если у него его нет ввести все нужные данные и нажать на кнопку сохранить внизу страницы но это могут сделать только зарегестрирорванные пользователи."
                             "Также в конце каждого ответа перед тегамидобавляй системную строчку '-END-END-' и после ние должны быть системные теги к примеру 'UPDATEAPP' 'WEBERROR' 'IDEA' и другие")
#on private message
@bot.on_message(pyrogram.filters.private)
async def start(client, message: pyrogram.types.Message):
    if message.from_user.id == client.me.id:
        if message.text == "ae":
            await message.delete()
            DISABLE_ID_CHATS.remove(message.chat.id)
        return

    if message.from_user.id in DISABLE_ID_CHATS:
        return

    if CHAT_HISTORY.get(message.chat.id) is None:
        CHAT_HISTORY[message.chat.id] = [{"role": "system", "content": MISTRAL_AI_SYSTEM_MESSAGE}]
    CHAT_HISTORY[message.chat.id].append({"role": "user", "content": message.text})
    await bot.send_chat_action(message.chat.id, enums.ChatAction.TYPING)
    chat_response = mclient.chat.complete(
        model="mistral-large-latest",
        messages=CHAT_HISTORY[message.chat.id],
        temperature=0.7,
    )
    CHAT_HISTORY[message.chat.id].append({"role": "assistant", "content": chat_response.choices[0].message.content})
    if "OPERATOR" in chat_response.choices[0].message.content:
        await bot.send_message(2015460473, "Запрос оператора в чат #{0}".format(message.chat.id))
        DISABLE_ID_CHATS.append(message.chat.id)
    await message.reply(chat_response.choices[0].message.content)


bot.run()