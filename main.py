import json
import random
import time
import uuid
import warnings
import zipfile
from datetime import timedelta, datetime, timezone
from io import BytesIO
from threading import Thread

import requests
from flask import Flask, render_template, send_from_directory, request, jsonify, session, redirect, send_file, \
    make_response, g, copy_current_request_context
from sqlalchemy import and_, desc
from sqlalchemy.exc import SAWarning
from user_agents import parse
from yoomoney import Quickpay, Client

from db import db, User, AuthUrl, Profile, Payment, Promocode, UserPromocode, ConsentLog, FakeMessageClose, \
    DocumentScan, ActionLog, TaskCompletion, Task, BlackListIP
import logging
logging.basicConfig(level=logging.DEBUG)
# Игнорируем специфические предупреждения SQLAlchemy
warnings.filterwarnings('ignore', category=SAWarning, message='.*fully NULL primary key.*')
warnings.filterwarnings('ignore', category=DeprecationWarning, message='.*datetime.utcnow().*')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://gen_user:ovLX1T)Hpg-5%3E_@94.198.216.178:5432/default_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,      # Проверять соединение перед использованием
    "pool_recycle": 1800        # Пересоздавать каждые 30 минут
}
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.permanent_session_lifetime = timedelta(days=7)
app.config['JSON_AS_ASCII'] = False
app.secret_key = 'GU_GEPOLIS_GUAPPSUPPORT_ADMIN_SECRET_KEY_2'
db.init_app(app)
LAST_UA_DATE = "01-07-2025"

# Конфигурация Telegram
TELEGRAM_TOKEN = "7705002195:AAE_9eNFFfaRxhwV54OT-mtm01L5BgXh7V4"
TELEGRAM_CHAT_ID = "-1002557822121"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
CALLBACK_URL = "https://gepolis-gu-7624.twc1.net/callback"
SUPPORT_ACCESS_KEY = "a7Fk3pR9qW2zYb6LmN8cX4vT5sJ1dG0hU7iO"
WALLET_NUMBER = "4100118081125029"
YOOMONEY_TOKEN = "4100118081125029.B5C5190A0515584D546589668EC04D03BC6680B00269B70913A64220E6657D73ED166EE15820FC4DAA5A15A0A3800E17A9C872A52D07A2D2D43ABDE200C217FE881563B8DC1CC3BE7484958B3FF0EE10B6E5763DDEE322D9D6F45825DA8BA923AE111928DBFE686683BF6C10DC1D4326C0640258434C8D2C89BF885A319CD650"
BLOCKED_PATHS = [
    ".git",
    "restore.php",
    "phpunit.xml",

    # Все .env и похожие файлы с расширениями или без
    ".env",         # основной .env файл
    ".envfile",
    ".env-vars",
    ".app-env",
    ".system-env",
    ".prod-env",
    ".env.yml",
    ".env.yaml",
    ".env.json",
    ".env.txt",

    # Общее для сервисов и облаков
    "github",
    "azure",
    "gcp",
    "k8s",
    "terraform",

    # Docker и оркестрация
    "docker-compose",
    "docker",

    # Конфигурации
    "config",
    "config.php",
    "config.json",
    "config.yaml",
    "config.yml",

    # Фреймворки и платформы
    "django",
    "laravel",
    "wp-admin",
    "wp-login",
    "wp-config.php",
    "wordpress",
    "joomla",
    "drupal",

    # Веб-серверы и публичные папки
    "htdocs",
    "public_html",
    "server-status",
    "server-info",

    # Системные и служебные папки/файлы
    "old",
    "backups",
    "temp",
    "tmp",
    "server",
    "error_log",

    # Часто атакуемые скрипты и файлы
    "phpmyadmin",
    "pma",
    "sql",
    "sql.php",
    "dbadmin",
    "adminer.php",
    "webdav",
    "shell",
    "cmd.php",
    "exec.php",
    "upload.php",
    "readme.html",
    "install.php",
    "update.php",
    "license.txt",

    # Осторожно, могут быть обычные папки в проектах
    # "src",
    # "var",

    # Распространённые попытки доступа к бэкапам и дампам
    "dump.sql",
    "backup.sql",
    "backup.zip",
    "backup.tar.gz",

    # Попытки доступа к конфиденциальным данным
    ".htaccess",
    ".htpasswd",
    ".ssh",
    "id_rsa",
    "id_rsa.pub",

    # Популярные пути для атак на уязвимости
    "xmlrpc.php",
    "wp-json",
    "autodiscover",
    "owa",
    "owa/auth",
    "owa/auth/x.js",
    "actuator",
    "solr",
]
client = Client(YOOMONEY_TOKEN)

# Вспомогательные функции
def safe_json(data):
    def default(o):
        if isinstance(o, datetime):
            return o.isoformat()
        return str(o)

    return json.loads(json.dumps(data, default=default))


def parse_browser(user_agent_string: str) -> str:
    user_agent = parse(user_agent_string)
    return f"{user_agent.browser.family} {user_agent.browser.version_string}"


def parse_os(user_agent_string: str) -> str:
    user_agent = parse(user_agent_string)
    return f"{user_agent.os.family} {user_agent.os.version_string}"


def parse_device(user_agent_string: str) -> str:
    user_agent = parse(user_agent_string)
    if user_agent.is_mobile:
        return "Mobile"
    elif user_agent.is_tablet:
        return "Tablet"
    elif user_agent.is_pc:
        return "PC"
    elif user_agent.is_bot:
        return "Bot"
    return "Unknown"


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
    except Exception:
        return "Ошибка определения"


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
    except Exception:
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
    ua = parse(user_agent)
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
        device_type=(
            "Mobile" if ua.is_mobile else "Tablet" if ua.is_tablet else "PC" if ua.is_pc else "Bot" if ua.is_bot else "Unknown"),
        device_brand=ua.device.brand or None,
        device_model=ua.device.model or None,
        location_city=geo.get('city'),
        location_region=geo.get('region'),
        location_country=geo.get('country'),
        location_lat=geo.get('lat'),
        location_lon=geo.get('lon'),
        location_provider=geo.get('provider'),
        timestamp=datetime.now(timezone.utc)
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


def get_client_info(request):
    try:
        ip = request.headers.get('X-Real-IP', request.remote_addr)
        if ',' in ip:
            ip = ip.split(',')[0].strip()

        user_agent = request.headers.get('User-Agent')
        ua_info = parse_user_agent(user_agent)

        return {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
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


def parse_user_agent(user_agent_str):
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


def format_visit_message(client_info, page):
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


def log_user_consent(req, user_id=None, comment="-"):
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


# Создание таблиц
with app.app_context():
    db.create_all()


@app.before_request
def before_request():
    session.permanent = True
@app.route('/set')
def set_session():
    session['data'] = 'привет'
    return 'Сессия установлена'

@app.route('/get')
def get_session():
    return f"Данные: {session.get('data')}"
# Middleware для отслеживания посещений
@app.after_request
def track_visits(response):
    if getattr(g, 'blocked', False):
        # Пропускаем любую обработку, сразу возвращаем ответ
        return response
    if all(x not in request.path for x in ["favicon.ico", "static"]):
        uid = session.get('user_id')
        log_action_async(
            request=request,
            user_id=uid,
            action_type="page_visit",
            description=f"Посещение страницы {request.path}",
            mdata={"page": request.path},
            detail_url=request.path,
        )
    if all(x not in request.path for x in ['api', '6329', 'static']):
        client_info = get_client_info(request)
        message = format_visit_message(client_info, request.path)
        Thread(target=send_to_telegram, args=(message,), daemon=True).start()

    return response


# Роуты приложения
@app.route('/')
def index():
    if not session.get('user_id'):
        return redirect('/auth')
    return send_from_directory('templates', 'test.htm')


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
        request=request,
        user_id=uid,
        action_type="code_request",
        description="Запрос кода для входа",
        mdata={"telegram_id": user_id, "user_id": uid, "code": str(otp_code), "registration": not auth},
        detail_url=None,
    )

    return jsonify({'code': otp_code, 'user_id': user_id, "registration": not auth})


@app.route('/check_auth/<int:otp_code>')
def check_auth(otp_code):
    try:
        auth_url = AuthUrl.query.filter(AuthUrl.code == otp_code, AuthUrl.is_active == True).first()
        if auth_url:
            user = User.query.filter(User.user_id == auth_url.user_id).first()

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
                request=request,
                user_id=user.id,
                action_type="login",
                description="Вход в аккаунт",
                mdata={"code": otp_code, "user_id": user.id, "username": user.username},
                detail_url=None,
            )

            return jsonify({'status': 'success', 'user_id': user.id})
        else:
            log_action_async(
                request=request,
                user_id=None,
                action_type="login_fail",
                description="Неудачная попытка входа",
                mdata={"code": otp_code, "user_id": None, "username": None},
                detail_url=None,
            )
            return jsonify({'status': 'error'})
    except Exception as e:
        send_to_telegram(f"Ошибка проверки авторизации: {e}")
        return jsonify({'status': 'error'})


@app.route('/auth')
def auth():
    return render_template('auth_new.html')
@app.route('/admin-login-9f7a2b4c3d1e')
def admin_login():
    return render_template('admin_auth.html')

@app.route('/api/user', methods=['GET'])
def get_or_create_user():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    user = User.query.filter(User.id == user_id).first()
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

    profiles = (
        db.session.query(Profile.id, Profile.name)
        .filter(Profile.user_id == user_id)
        .limit(100)
        .all()
    )

    if not profiles:
        return jsonify([])

    return jsonify([
        {'id': p.id, 'name': p.name} for p in profiles
    ])


@app.route('/api/profile', methods=['GET'])
def get_profile():
    profile_id = request.args.get('profile_id')
    if not profile_id:
        return jsonify({'error': 'profile_id is required'}), 400

    profile = db.session.get(Profile, profile_id)
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404

    return jsonify(profile.to_dict())


@app.route('/api/profile', methods=['POST'])
def create_profile():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()
    name = data.get('name', 'Новый профиль')
    is_primary = data.get('is_primary', False)

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
        inn_number=data.get('inn_number'),
        gender=data.get('gender')
    )
    db.session.add(new_profile)
    db.session.commit()

    log_action_async(
        request=request,
        user_id=user.id,
        action_type="create_profile",
        description="Создание профиля",
        mdata={"profile": new_profile.to_dict(), "user_id": user.id},
        detail_url=None,
    )

    return jsonify(new_profile.to_dict()), 201


@app.route('/api/profile', methods=['PUT'])
def update_profile():
    user_id = session.get('user_id')
    profile_id = request.args.get('profile_id')
    if not user_id or not profile_id:
        return jsonify({'error': 'user_id and profile_id are required'}), 400

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    profile = Profile.query.filter_by(id=profile_id, user_id=user_id).first()
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404

    data = request.get_json()
    profile_before = profile.to_dict()

    # Обновляем все доступные поля
    fields = [
        'name', 'is_primary', 'photo', 'last_name', 'first_name', 'middle_name',
        'birth_date', 'birth_place', 'passport_number', 'passport_issued',
        'passport_code', 'passport_date', 'registration_address', 'living_address',
        'snils_number', 'inn_number', 'gender'
    ]

    for field in fields:
        if field in data:
            setattr(profile, field, data[field])

    db.session.commit()

    log_action_async(
        request=request,
        user_id=user.id,
        action_type="update_profile",
        description="Изменение профиля",
        mdata={
            "id": profile.id,
            "before": profile_before,
            "after": profile.to_dict(),
            "user_id": user.id,
        },
    )

    return jsonify(profile.to_dict())


@app.route('/api/profile', methods=['DELETE'])
def delete_profile():
    user_id = session.get('user_id')
    profile_id = request.args.get('profile_id')
    if not user_id or not profile_id:
        return jsonify({'error': 'user_id and profile_id are required'}), 400

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    profile = Profile.query.filter_by(id=profile_id, user_id=user_id).first()
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404

    log_action_async(
        request=request,
        user_id=user.id,
        action_type="delete_profile",
        description="Удаление профиля",
        mdata={"id": profile.id, "data": profile.to_dict(), "user_id": user.id},
        detail_url=None,
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
    user = db.session.get(User, user_id) if user_id else None
    if not user or not user.is_admin:
        return jsonify({'error': 'Access denied'}), 403

    photos = Profile.query.filter(Profile.photo != None).all()
    html = ""
    for photo in photos:
        html += f"<img src='{photo.photo}' style='width: 200px; height: auto;'>"
    return html


@app.route('/admin/json/users', methods=['POST'])
def admin_json_users():
    users = User.query.all()
    return jsonify([{
        'id': user.id,
        'username': user.username,
        'user_id': user.user_id,
        'is_admin': user.is_admin
    } for user in users])


@app.route('/static/&lt;path:path&gt;')
def send_static(path):
    return send_from_directory('static', path)


@app.route("/premium")
def premium():
    return render_template("pay.html")


@app.route("/api/subscription", methods=["GET"])
def get_subscription():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    current_time = int(time.time())

    # Инициализация подписки если нужно
    if user.subscription_expiration is None or user.subscription_type is None:
        user.subscription_type = "N"
        user.subscription_expiration = 0
        db.session.commit()

    # Проверка истекшей подписки
    if user.subscription_expiration < current_time:
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


@app.route("/payment/<plan>/<t>", methods=['POST', 'GET'])
def payment(plan, t):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    log_user_consent(request, user_id, f"Покупка подписки {plan} {t}")
    payment_uuid = str(uuid.uuid4())
    promo_code = None

    if request.method == 'POST':
        promo_code = request.json.get('promo_code')
    else:
        promo_code = request.args.get('promo_code', "NONEPROMOCODE")

    # Обработка покупки скрытий
    if plan == "hides":
        prices = {
            "1": 20, "3": 54, "5": 80, "10": 140,
            "15": 195, "20": 250, "25": 275, "30": 300
        }
        amount = t
        price = prices.get(amount, 0)

        if not price:
            return jsonify({'error': 'Invalid amount'}), 400

        # Применение промокода
        promo = Promocode.query.filter_by(code=promo_code, promo_type="discount").first()
        if promo:
            price = max(1, round(price - (price / 100 * promo.value)))

        pay = Payment(
            user_id=user_id,
            amount=price,
            plan=plan,
            time=amount,
            status="pending",
            uuid=payment_uuid
        )
    else:
        # Обработка подписок
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

        # Применение промокода
        promo = Promocode.query.filter_by(code=promo_code, promo_type="discount").first()
        if promo:
            price = max(1, round(price - (price / 100 * promo.value)))

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

    log_action_async(
        request=request,
        user_id=user_id,
        action_type="create_payment",
        description=f"Создание платежа",
        mdata={"data": pay.to_dict(), "promo": promo_code},
        detail_url="/payment/url/" + payment_uuid,
    )

    return jsonify({
        "url": "/payment/url/" + payment_uuid,
        "status": "success"
    })


@app.route("/api/check-promo", methods=['POST'])
def check_promo():
    promo_code = request.json.get('promo_code')
    if not promo_code:
        return jsonify({"valid": False, "message": "Промокод не указан"})

    user_id = session.get('user_id')
    promo = Promocode.query.filter_by(code=promo_code, promo_type="discount").first()

    if not promo:
        log_action_async(
            request=request,
            user_id=user_id,
            action_type="promo_use",
            description=f"Попытка использования промокода",
            mdata={"promo": promo_code, "message": "Промокод не найден", "user_id": user_id},
            detail_url=None,
        )
        return jsonify({"valid": False, "message": "Промокод не найден"})

    # Проверка принадлежности промокода
    if promo.user_id and promo.user_id != user_id:
        log_action_async(
            request=request,
            user_id=user_id,
            action_type="promo_use",
            description=f"Попытка использования промокода",
            mdata={"promo": promo.to_dict(), "message": "Промокод другого пользователя", "user_id": user_id},
            detail_url=None,
        )
        return jsonify({"valid": False, "message": "Промокод принадлежит не вам"})

    # Проверка многократного использования
    if not promo.discount_multi_use:
        if UserPromocode.query.filter_by(promocode_id=promo.id, user_id=user_id).first():
            log_action_async(
                request=request,
                user_id=user_id,
                action_type="promo_use",
                description=f"Повторное использование промокода",
                mdata={"promo": promo.to_dict(), "message": "Повторное использование промокода", "user_id": user_id},
                detail_url=None,
            )
            return jsonify({"valid": False, "message": "Вы не можете использовать этот промокод повторно"})

    # Проверка лимита использований
    if promo.max_uses <= promo.current_uses:
        log_action_async(
            request=request,
            user_id=user_id,
            action_type="promo_use",
            description=f"Лимит использования промокода",
            mdata={"promo": promo.to_dict(), "message": "Лимит использования промокода", "user_id": user_id},
            detail_url=None,
        )
        return jsonify({"valid": False, "message": "Промокод достиг лимита использований"})

    # Проверка активности
    if not promo.is_active:
        log_action_async(
            request=request,
            user_id=user_id,
            action_type="promo_use",
            description=f"Промокод неактивен",
            mdata={"promo": promo.to_dict(), "message": "Промокод неактивен", "user_id": user_id},
            detail_url=None,
        )
        return jsonify({"valid": False, "message": "Промокод неактивен"})

    log_action_async(
        request=request,
        user_id=user_id,
        action_type="promo_use",
        description=f"Использование промокода",
        mdata=safe_json({"promo": promo.to_dict(), "message": "Успешное использование промокода", "user_id": user_id}),
        detail_url=None,
    )

    return jsonify({"valid": True, "discount": promo.value})


@app.route("/payment/url/<uuid>")
def get_payment_url(uuid):
    pay = Payment.query.filter_by(uuid=uuid).first()
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
        request=request,
        user_id=pay.user_id,
        action_type="payment_url_open",
        description=f"Открытие ссылки для оплаты",
        mdata={"pay": pay.to_dict()},
        detail_url=None,
    )

    return redirect(quickpay.redirected_url)


def check_payment(uuid):
    client = Client(YOOMONEY_TOKEN)
    history = client.operation_history(label=uuid)
    time.sleep(0.2)

    for operation in history.operations:
        if operation.status == 'success':
            pay = Payment.query.filter_by(uuid=uuid).first()
            if not pay or pay.status == "success":
                return {"status": "already_processed"}

            pay.status = "success"
            user = db.session.get(User, pay.user_id)

            if not user:
                return {"status": "user_not_found"}

            if pay.plan == "hides":
                user.free_closes += int(pay.time)
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
def pay_check(uuid):
    user_id = session.get("user_id")
    action_description = f"Проверка оплаты: UUID={uuid}"

    for attempt in range(3):
        result = check_payment(uuid)
        if result["status"] in ["success", "already_processed"]:
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
    for _ in range(3):
        result = check_payment(uuid)
        if result["status"] in ["success", "already_processed"]:
            return jsonify({"status": "success"})
        elif result["status"] == "pending":
            time.sleep(0.1)
            continue
    return jsonify({"status": "not_found"})


@app.route("/api/promocode/<code>")
def promocode(code):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "Не указан user_id"}), 400

    promocode = Promocode.query.filter_by(code=code).first()
    if not promocode:
        log_action_async(
            request=request,
            user_id=user_id,
            action_type="promo_use",
            description=f"Попытка использования промокода",
            mdata={"promo": code, "message": "Промокод не найден", "user_id": user_id},
            detail_url=None,
        )
        return jsonify({"status": "error", "message": "Промокод не найден"}), 400

    if promocode.current_uses >= promocode.max_uses:
        log_action_async(
            request=request,
            user_id=user_id,
            action_type="promo_use",
            description=f"Лимит использований промокода",
            mdata={"promo": promocode.to_dict(), "message": "Лимит использований промокода", "user_id": user_id},
            detail_url=None,
        )
        return jsonify({"status": "error", "message": "Промокод превысил лимит использований"}), 400

    if not promocode.is_active:
        log_action_async(
            request=request,
            user_id=user_id,
            action_type="promo_use",
            description=f"Промокод неактивен",
            mdata={"promo": promocode.to_dict(), "message": "Промокод неактивен", "user_id": user_id},
            detail_url=None,
        )
        return jsonify({"status": "error", "message": "Промокод неактивен"}), 400

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"status": "error", "message": "Пользователь не найден"}), 400

    if UserPromocode.query.filter_by(promocode_id=promocode.id, user_id=user_id).first():
        log_action_async(
            request=request,
            user_id=user_id,
            action_type="promo_use",
            description=f"Повторное использование промокода",
            mdata={"promo": code, "message": "Повторное использование промокода", "user_id": user_id},
            detail_url=None,
        )
        return jsonify({"status": "error", "message": "Вы уже использовали этот промокод"}), 400

    now = int(time.time())
    user_before = user.to_dict()

    # Бесплатные скрытия
    if promocode.promo_type == "free_closes":
        user.free_closes += promocode.value
        promocode.current_uses += 1
        db.session.add(UserPromocode(user_id=user_id, promocode_id=promocode.id))
        db.session.commit()

        log_action_async(
            request=request,
            user_id=user_id,
            action_type="promo_use",
            description=f"Использование промокода",
            mdata=safe_json({
                "promo": promocode.to_dict(),
                "user_before": user_before,
                "user_after": user.to_dict()
            }),
            detail_url=None,
        )
        return jsonify({
            "status": "success",
            "message": f"Вы получили {promocode.value} бесплатных закрытий"
        }), 200

    # Подписка
    elif promocode.promo_type in ["plus", "premium"]:
        priority = {"N": 0, "plus": 1, "premium": 2}
        user_priority = priority.get(user.subscription_type or "N", 0)
        promo_priority = priority.get(promocode.promo_type, 0)

        # Проверка уровня подписки
        if user_priority > promo_priority and user.subscription_expiration > now:
            log_action_async(
                request=request,
                user_id=user_id,
                action_type="promo_use",
                description=f"Отказ в использование промокода",
                mdata={"promo": promocode.to_dict(),
                       "message": f"Активная подписка более высокого уровня ({user.subscription_type})",
                       "user_id": user_id},
                detail_url=None,
            )
            return jsonify({
                "status": "error",
                "message": f"У вас уже есть активная подписка более высокого уровня ({user.subscription_type})"
            }), 400

        # Обновление подписки
        if user.subscription_expiration > now and user.subscription_type == promocode.promo_type:
            user.subscription_expiration += promocode.value
        else:
            user.subscription_expiration = now + promocode.value

        user.subscription_type = promocode.promo_type
        promocode.current_uses += 1
        db.session.add(UserPromocode(user_id=user_id, promocode_id=promocode.id))
        db.session.commit()

        log_action_async(
            request=request,
            user_id=user_id,
            action_type="promo_use",
            description=f"Использование промокода",
            mdata=safe_json({
                "promo": promocode.to_dict(),
                "user_before": user_before,
                "user_after": user.to_dict()
            }),
            detail_url=None,
        )
        return jsonify({
            "status": "success",
            "message": f"Вы получили подписку {promocode.promo_type}"
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
        log_user_consent(request, user_id, "Согласие на обработку персональных данных")
    return {"status": "success"}


@app.route("/user-agreement")
def user_agreement():
    return send_file(
        f'static/user-agreement-{LAST_UA_DATE}.pdf',
        mimetype='application/pdf',
        as_attachment=False,
        download_name=f'user-agreement-{LAST_UA_DATE}.pdf'
    )


@app.route("/api/close/fake")
def close_fake():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    now = int(time.time())
    active_close = FakeMessageClose.query.filter(
        FakeMessageClose.user_id == user_id,
        FakeMessageClose.closed_to > now
    ).first()

    if active_close:
        return jsonify({"status": "success", "message": "You have already closed today"}), 200

    can_close = (
            user.subscription_type in ["plus", "premium"] or
            user.free_closes > 0
    )

    if not can_close:
        log_action_async(
            request=request,
            user_id=user_id,
            action_type="fake_close",
            description=f"Недостаточно скрытий для скрытия плашки",
            mdata={"user_id": user_id},
            detail_url=None,
        )
        return jsonify({
            "status": "error",
            "message": "У вас закончились бесплатные скрытия. Приобретите <a href='/premium'>подписку</a> или активируйте промокод"
        }), 400

    try:
        with db.session.begin_nested():
            # Списание только если пользователь не на подписке
            if user.free_closes > 0 and user.subscription_type not in ["plus", "premium"]:
                user.free_closes -= 1

            client_data = get_client_info(request)
            if not client_data:
                return jsonify({"status": "error", "message": "Ошибка, попробуйте позже"}), 400

            fk = FakeMessageClose(
                user_id=user_id,
                ip=client_data['network']['ip'],
                user_agent=client_data['network']['user_agent'],
                browser=client_data['device']['browser'],
                system=client_data['device']['os'],
                device=client_data['device']['device'],
                closed_to=now + 24 * 60 * 60
            )
            db.session.add(fk)

        db.session.commit()
        log_action_async(
            request=request,
            user_id=user_id,
            action_type="fake_close",
            description=f"Успешное скрытие плашки фейк",
            mdata={"data": fk.to_dict(), "user_id": user_id},
            detail_url=None,
        )
        return jsonify({"status": "success"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": "Ошибка, попробуйте позже"}), 500


@app.route("/api/close/check")
def close_check():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"status": "error"}), 400

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"status": "error"}), 400

    now = int(time.time())

    # Проверка активной подписки
    if user.subscription_type in ["plus", "premium"] and user.subscription_expiration > now:
        return jsonify({"status": "success"}), 200

    # Проверка активного закрытия
    entry = FakeMessageClose.query.filter(
        FakeMessageClose.user_id == user_id,
        FakeMessageClose.closed_to > now
    ).first()

    if entry:
        return jsonify({"status": "success"}), 200

    return jsonify({"status": "error"}), 400


@app.route("/api/support/profiles")
def support_profiles():
    key = request.args.get("key")
    user_id = request.args.get("id")

    if key != SUPPORT_ACCESS_KEY:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    profiles = Profile.query.filter_by(user_id=user.id).all()
    return jsonify({"status": "success", "profiles": [profile.to_dict() for profile in profiles]}), 200


@app.route("/api/support/payments")
def support_payments():
    key = request.args.get("key")
    user_id = request.args.get("id")

    if key != SUPPORT_ACCESS_KEY:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    payments = Payment.query.filter_by(user_id=user.id).all()
    return jsonify({"status": "success", "payments": [payment.to_dict() for payment in payments]}), 200


@app.route("/api/support/closes")
def support_close():
    key = request.args.get("key")
    user_id = request.args.get("id")

    if key != SUPPORT_ACCESS_KEY:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    closes = FakeMessageClose.query.filter_by(user_id=user.id).all()
    return jsonify({"status": "success", "closes": [close.to_dict() for close in closes]}), 200


@app.route("/api/support/info")
def support_clients():
    key = request.args.get("key")
    user_id = request.args.get("id")

    if key != SUPPORT_ACCESS_KEY:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    return jsonify({"status": "success", "user": user.to_dict()}), 200


@app.route("/api/support/promocodes")
def support_promocodes():
    key = request.args.get("key")
    user_id = request.args.get("id")

    if key != SUPPORT_ACCESS_KEY:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    promos = UserPromocode.query.filter_by(user_id=user.id).all()
    promocodes = [Promocode.query.get(p.promocode_id) for p in promos]
    return jsonify({"status": "success", "promocodes": [p.to_dict() for p in promocodes if p]}), 200


# API для промокодов
@app.route('/api/promocodes', methods=['GET', 'POST'])
def handle_promocodes():
    user_id = session.get('user_id')
    if user_id is None:
        return jsonify({"error": "Access denied"}), 403

    user = db.session.get(User, user_id)
    if not user or not user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    if request.method == 'GET':
        promocodes = Promocode.query.all()
        return jsonify([p.to_dict() for p in promocodes])

    elif request.method == 'POST':
        data = request.get_json()

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
        return jsonify(promocode.to_dict()), 201


@app.route('/api/promocodes/<int:promo_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_promocode(promo_id):
    user_id = session.get('user_id')
    if user_id is None:
        return jsonify({"error": "Access denied"}), 403

    user = db.session.get(User, user_id)
    if not user or not user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    promocode = db.session.get(Promocode, promo_id)
    if not promocode:
        return jsonify({"error": "Promocode not found"}), 404

    if request.method == 'GET':
        return jsonify(promocode.to_dict())

    elif request.method == 'PUT':
        data = request.get_json()

        if 'code' in data and Promocode.query.filter(Promocode.code == data['code'], Promocode.id != promo_id).first():
            return jsonify({'message': 'Промокод с таким кодом уже существует'}), 400

        fields = ['code', 'promo_type', 'value', 'max_uses', 'user_id', 'discount_multi_use', 'is_active']
        for field in fields:
            if field in data:
                setattr(promocode, field, data[field])

        db.session.commit()
        return jsonify(promocode.to_dict())

    elif request.method == 'DELETE':
        UserPromocode.query.filter_by(promocode_id=promo_id).delete()
        db.session.delete(promocode)
        db.session.commit()
        return jsonify({'message': 'Промокод удален'}), 200


@app.route('/api/promocodes/<int:promo_id>/status', methods=['PATCH'])
def toggle_promocode_status(promo_id):
    user_id = session.get('user_id')
    if user_id is None:
        return jsonify({"error": "Access denied"}), 403

    user = db.session.get(User, user_id)
    if not user or not user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    promocode = db.session.get(Promocode, promo_id)
    if not promocode:
        return jsonify({"error": "Promocode not found"}), 404

    data = request.get_json()
    promocode.is_active = data['is_active']
    db.session.commit()
    return jsonify(promocode.to_dict())


@app.route('/api/promocodes/<int:promo_id>/activations', methods=['GET'])
def get_promocode_activations(promo_id):
    user_id = session.get('user_id')
    if user_id is None:
        return jsonify({"error": "Access denied"}), 403

    user = db.session.get(User, user_id)
    if not user or not user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    promocode = db.session.get(Promocode, promo_id)
    if not promocode:
        return jsonify({'message': 'Promocode not found'}), 404

    activations = db.session.query(
        UserPromocode,
        User
    ).join(
        User, User.id == UserPromocode.user_id
    ).filter(
        UserPromocode.promocode_id == promo_id
    ).all()

    result = [{
        'id': act.UserPromocode.id,
        'created_at': None,
        'user': {
            'id': act.User.id,
            'user_id': act.User.user_id,
            'username': act.User.username,
            'is_admin': act.User.is_admin,
            'subscription_type': act.User.subscription_type,
            'subscription_expiration': act.User.subscription_expiration,
            'free_closes': act.User.free_closes
        } if act.User else None
    } for act in activations]

    return jsonify({
        'promocode': promocode.to_dict(),
        'activations': result
    })


@app.route('/api/activations', methods=['GET'])
def get_all_activations():
    user_id = session.get('user_id')
    if user_id is None:
        return jsonify({"error": "Access denied"}), 403

    user = db.session.get(User, user_id)
    if not user or not user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    activations = db.session.query(
        UserPromocode,
        User,
        Promocode
    ).join(
        User, User.id == UserPromocode.user_id
    ).join(
        Promocode, Promocode.id == UserPromocode.promocode_id
    ).all()

    if not activations:
        return jsonify([])

    result = []
    for activation in activations:
        result.append({
            'id': activation.UserPromocode.id,
            'created_at': None,
            'user': activation.User.to_dict() if activation.User else None,
            'promocode': activation.Promocode.to_dict() if activation.Promocode else None
        })

    return jsonify(result)


@app.route('/admin/promo')
def admin_promo():
    user_id = session.get('user_id')
    if user_id is None:
        return jsonify({"error": "Access denied"}), 403

    user = db.session.get(User, user_id)
    if not user or not user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    return render_template("admin_promo.html")


@app.route("/test-log", methods=["GET", "POST"])
def test_log():
    log_action_async(
        request=request,
        user_id=session.get('user_id'),
        action_type="test_action",
        description="Ручной тест логирования через функцию",
        mdata={"source": "test"},
        detail_url="/admin/users/1"
    )
    return "✅ Лог успешно создан"


@app.route('/api/user/<int:user_id>')
def api_user(user_id):
    adm_user_id = session.get('user_id')
    if adm_user_id is None:
        return jsonify({"error": "Access denied"}), 403

    adm_user = db.session.get(User, adm_user_id)
    if not adm_user or not adm_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    profiles = Profile.query.filter_by(user_id=user_id).all()
    return jsonify({
        "user": user.to_dict(),
        "profiles": [p.to_dict() for p in profiles]
    })


@app.route('/api/logs')
def api_logs():
    user_id = session.get('user_id')
    if user_id is None:
        return jsonify({"error": "Access denied"}), 403

    user = db.session.get(User, user_id)
    if not user or not user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    # Параметры фильтрации
    user_id_filter = request.args.get('user_id', type=int)
    action_type = request.args.get('action_type', type=str)
    date_from = request.args.get('date_from', type=str)
    date_to = request.args.get('date_to', type=str)
    ip = request.args.get('ip', type=str)
    page = request.args.get('page', default=1, type=int)
    limit = request.args.get('limit', default=100, type=int)

    filters = []
    if user_id_filter:
        filters.append(ActionLog.user_id == user_id_filter)
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

    query = ActionLog.query
    if filters:
        query = query.filter(and_(*filters))
    query = query.order_by(ActionLog.timestamp.desc())

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
    user_id = session.get('user_id')
    if user_id is None:
        return jsonify({"error": "Access denied"}), 403

    user = db.session.get(User, user_id)
    if not user or not user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    log = db.session.get(ActionLog, log_id)
    if not log:
        return jsonify({"error": "Log not found"}), 404
    return jsonify(log.to_dict())


@app.route('/api/export')
def export_action_logs():
    user_id = session.get('user_id')
    if user_id is None:
        return jsonify({"error": "Access denied"}), 403

    user = db.session.get(User, user_id)
    if not user or not user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    # Параметры фильтрации
    user_id_filter = request.args.get('user_id', type=int)
    action_type = request.args.get('action_type', type=str)
    date_from = request.args.get('date_from', type=str)
    date_to = request.args.get('date_to', type=str)
    ip = request.args.get('ip', type=str)

    filters = []
    if user_id_filter:
        filters.append(ActionLog.user_id == user_id_filter)
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

    query = ActionLog.query
    if filters:
        query = query.filter(and_(*filters))
    query = query.order_by(ActionLog.timestamp.desc())

    logs = query.all()
    logs_data = [log.to_dict() for log in logs]

    # Создание ZIP в памяти
    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('logs.json', json.dumps(logs_data, ensure_ascii=False, indent=2))

    memory_file.seek(0)
    filename = f"export_gu2_{datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')}.zip"

    log_action_async(
        request=request,
        user_id=user_id,
        action_type="export_log",
        description=f"Экспорт логов - {datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')}",
        mdata=safe_json({
            "file": filename,
            "filters": {
                "ip": ip,
                "date_from": date_from,
                "date_to": date_to,
                "action_type": action_type,
                "user_id": user_id_filter,
            }
        }),
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
    if user_id is None:
        return jsonify({"error": "Access denied"}), 403

    user = db.session.get(User, user_id)
    if not user or not user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    return render_template("logs.html")




@app.route("/mobile")
def mobile():
    if not session.get('user_id'):
        return redirect('/auth')
    return render_template("pass.html")


@app.route("/mobile/details")
def mobile_details():
    return render_template("pass_mobile_detail.html")

@app.route('/api/documents/upload', methods=['POST'])
def upload_document():
    # Проверяем, что пользователь авторизован
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    # Извлекаем данные из запроса
    profile_id = data.get('profile_id')
    scan_data = data.get('scan_data')
    if not profile_id or not scan_data:
        return jsonify({'error': 'Missing profile_id or scan_data'}), 400
    # Проверяем, что профиль принадлежит пользователю
    profile = Profile.query.filter_by(id=profile_id, user_id=user_id).first()
    if not profile:
        return jsonify({'error': 'Profile not found or does not belong to the user'}), 404
    if len(scan_data) > 14 * 1024 * 1024:  # 14 МБ для запаса
        return jsonify({'error': 'File size exceeds the 10 MB limit.'}), 400
    # Создаем запись о скане документа
    new_scan = DocumentScan(
        profile_id=profile_id,
        scan_data=scan_data,
        uploaded_at=datetime.now(timezone.utc)
    )
    db.session.add(new_scan)
    db.session.commit()
    log_action_async(
        request=request,
        user_id=user_id,
        action_type="document_upload",
        description="Загрузка скана документа",
        mdata={"profile_id": profile_id, "scan_id": new_scan.id},
        detail_url=None,
    )
    return jsonify({
        'status': 'success',
        'scan_id': new_scan.id
    }), 201


@app.route('/api/documents/scans', methods=['GET'])
def get_document_scans():
    # Проверка авторизации пользователя
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    # Получение параметров запроса
    profile_id = request.args.get('profile_id')
    if not profile_id:
        return jsonify({'error': 'profile_id parameter is required'}), 400

    # Проверка принадлежности профиля пользователю
    profile = Profile.query.filter_by(id=profile_id, user_id=user_id).first()
    if not profile:
        return jsonify({'error': 'Profile not found or does not belong to user'}), 404

    # Получение сканов для профиля
    scans = DocumentScan.query.filter_by(profile_id=profile_id).all()

    return jsonify({
        'status': 'success',
        'scans': [{
            'id': scan.id,
            'uploaded_at': scan.uploaded_at.isoformat(),
            'scan_data': scan.scan_data
        } for scan in scans]
    })


@app.route('/api/tasks/<int:user_id>', methods=['GET'])
def get_available_tasks(user_id):
    # Все активные задания
    active_tasks = Task.query.filter_by(is_active=True).all()

    # ID выполненных заданий
    completed_task_ids = db.session.query(
        TaskCompletion.task_id
    ).filter_by(
        user_id=user_id
    ).all()

    # Превращаем [(1,), (2,)] в [1, 2]
    completed_ids = [task_id for (task_id,) in completed_task_ids]

    # Оставляем только невыполненные
    available_tasks = [
        {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "url": task.url,
            "url_id": task.url_id,
            "reward": task.reward,
            "completions": task.completions,
            "target_completions": task.target_completions
        }
        for task in active_tasks
        if task.id not in completed_ids
    ]

    return jsonify(available_tasks)

@app.route('/api/tasks/complete', methods=['POST'])
def complete_task():
    data = request.get_json()
    print(data)

    user_id = data.get("user_id")
    task_id = data.get("task_id")

    if not user_id or not task_id:
        return jsonify({"status": "error", "message": "Missing user_id or task_id"}), 400

    # Проверяем, есть ли задание
    task = Task.query.get(task_id)
    if not task:
        return jsonify({"status": "error", "message": "Task not found"}), 404

    # Проверяем, активно ли задание
    if not task.is_active:
        return jsonify({"status": "error", "message": "Task is not active"}), 400

    # Проверяем лимит выполнений
    if task.completions >= task.target_completions:
        return jsonify({"status": "error", "message": "Task completions limit reached"}), 400

    # Проверяем, выполнял ли уже пользователь
    existing = TaskCompletion.query.filter_by(task_id=task_id, user_id=user_id).first()
    if existing:
        return jsonify({"status": "error", "message": "Task already completed by this user"}), 400

    if user_id == task.advertiser_id:
        return jsonify({"status": "error", "message": "Advertisers cannot complete their own tasks."}), 400

    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404
    user.free_closes = user.free_closes + task.reward
    db.session.add(user)
    db.session.commit()
    # Создаем выполнение
    completion = TaskCompletion(
        task_id=task_id,
        user_id=user_id
    )
    db.session.add(completion)

    # Увеличиваем счетчик
    task.completions += 1

    # Если достигнут лимит, отключаем задание
    if task.completions >= task.target_completions:
        task.is_active = False

    db.session.commit()
    log_action_async(
        request=request,
        user_id=user.id,
        action_type="task_complete",
        description=f"Выполнение задания - {task.id}",
        mdata={"task_id": task_id, "user_id": user.id, "complete_id": completion.id}
    )


    return jsonify({"status": "success", "message": "Task completion recorded"})

# -------------------- BLACKLIST ADMIN --------------------
@app.route('/api/blacklist', methods=['GET', 'POST'])
def manage_blacklist():
    user_id = session.get('user_id')
    if user_id is None:
        return jsonify({"error": "Access denied"}), 403
    user = User.query.get(user_id)
    if user_id != 1:
        return jsonify({"error": "Access denied"}), 403
    if request.method == 'GET':
        ips = BlackListIP.query.all()
        return jsonify([ip.to_dict() for ip in ips])

    elif request.method == 'POST':
        data = request.get_json()

        if not data or 'ip' not in data:
            return jsonify({'message': 'IP address is required'}), 400

        if BlackListIP.query.filter_by(ip=data['ip']).first():
            return jsonify({'message': 'IP адрес уже заблокирован'}), 400
        user_ip = request.headers.get('X-Real-IP', request.remote_addr)
        if user_ip == data['ip']:
            return jsonify({'message': 'Данный IP невозможно заблокировать'}), 400

        new_ip = BlackListIP(
            ip=data['ip'],
            reason=data.get('reason'),
            source="Администратор",
        )

        db.session.add(new_ip)
        db.session.commit()

        return jsonify(new_ip.to_dict()), 201
    return None


@app.route('/api/blacklist/<int:ip_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_ip(ip_id):
    user_id = session.get('user_id')
    if user_id is None:
        return jsonify({"error": "Access denied"}), 403
    user = User.query.get(user_id)
    if user_id != 1:
        return jsonify({"error": "Access denied"}), 403
    ip = BlackListIP.query.get_or_404(ip_id)

    if request.method == 'GET':
        return jsonify(ip.to_dict())

    elif request.method == 'PUT':
        data = request.get_json()

        if not data:
            return jsonify({'message': 'No data provided'}), 400

        if 'ip' in data:
            # Проверяем, не существует ли уже такого IP
            existing_ip = BlackListIP.query.filter_by(ip=data['ip']).first()
            if existing_ip and existing_ip.id != ip.id:
                return jsonify({'message': 'IP address already exists in blacklist'}), 400
            ip.ip = data['ip']

        if 'reason' in data:
            ip.reason = data['reason']

        db.session.commit()
        return jsonify(ip.to_dict())

    elif request.method == 'DELETE':
        db.session.delete(ip)
        db.session.commit()
        return jsonify({'message': 'IP address removed from blacklist'})
    return None


@app.route('/admin/blacklist')
def blacklist():
    user_id = session.get('user_id')
    if user_id is None:
        return jsonify({"error": "Access denied"}), 403
    user = User.query.get(user_id)
    if user_id != 1:
        return jsonify({"error": "Access denied"}), 403
    return render_template("admin_blacklist.html")


# --------------------- admin payments -------------------------

@app.route('/api/payments', methods=['GET', 'POST'])
def manage_payments():
    user_id = session.get('user_id')
    if user_id is None:
        return jsonify({"error": "Access denied"}), 403

    user = db.session.get(User, user_id)
    if not user or not user.is_admin:
        return jsonify({"error": "Access denied"}), 403
    if request.method == 'GET':
        payments = Payment.query.order_by(desc(Payment.id)).all()
        return jsonify([payment.to_dict() for payment in payments])

    elif request.method == 'POST':
        data = request.get_json()

        if not data or 'amount' not in data:
            return jsonify({'message': 'Amount is required'}), 400

        try:
            payment_uuid = str(uuid.uuid4())

            # Определяем параметры платежа
            is_admin = data.get('is_admin', False)
            comment = data.get('comment', 'Платеж')
            # Создаем ссылку для оплаты в YooMoney
            quick = Quickpay(
                receiver=WALLET_NUMBER,
                quickpay_form="shop",
                targets="Sponsor this project",
                paymentType="SB",
                sum=100,
                label=payment_uuid,
                successURL="https://gosuslugi.com.ru/pay/" + payment_uuid,
            )
            print(quick.redirected_url)


            # Создаем запись в базе данных
            new_payment = Payment(
                user_id=0,
                amount=data['amount'],
                plan="admin",
                time=0,
                uuid=payment_uuid,
                status="pending"
            )

            db.session.add(new_payment)
            db.session.commit()

            return jsonify({
                'message': 'Payment created successfully',
                'payment': new_payment.to_dict(),
                'payment_url': quick.redirected_url
            }), 201

        except Exception as e:
            print(e)
            return jsonify({'message': f'Error creating payment: {str(e)}'}), 500
    return None


@app.route('/api/payments/<int:payment_id>', methods=['DELETE'])
def delete_payment(payment_id):
    user_id = session.get('user_id')
    if user_id is None:
        return jsonify({"error": "Access denied"}), 403

    user = db.session.get(User, user_id)
    if not user or not user.is_admin:
        return jsonify({"error": "Access denied"}), 403
    payment = Payment.query.get_or_404(payment_id)

    db.session.delete(payment)
    db.session.commit()

    return jsonify({'message': 'Payment deleted successfully'})


@app.route('/api/payments/<int:payment_id>/check', methods=['POST'])
def check_payment_status(payment_id):
    user_id = session.get('user_id')
    if user_id is None:
        return jsonify({"error": "Access denied"}), 403

    user = db.session.get(User, user_id)
    if not user or not user.is_admin:
        return jsonify({"error": "Access denied"}), 403
    payment = Payment.query.get_or_404(payment_id)

    if payment.status != 'pending':
        return jsonify({'message': 'Payment is already processed'}), 400

    try:
        # Проверяем историю операций в YooMoney
        history = client.operation_history(label=payment.uuid)

        for operation in history.operations:
            print(operation.label)
            if operation.status == 'success':
                payment.status = 'success'
                db.session.commit()
                return jsonify({
                    'message': 'Оплачено',
                    'payment': payment.to_dict()
                })
            else:
                return jsonify({'message': 'Не оплачено'}), 404
        return jsonify({'message': 'Не оплачено'}), 404

    except Exception as e:
        return jsonify({'message': f'Error checking payment status: {str(e)}'}), 500


@app.route('/api/payments/check-pending', methods=['POST'])
def check_pending_payments():
    user_id = session.get('user_id')
    if user_id is None:
        return jsonify({"error": "Access denied"}), 403

    user = db.session.get(User, user_id)
    if not user or not user.is_admin:
        return jsonify({"error": "Access denied"}), 403
    try:
        pending_payments = Payment.query.filter_by(status='pending').all()
        updated_count = 0
        history = client.operation_history()
        for operation in history.operations:
            if operation.status == 'success':
                u = operation.label
                print(u)
                paym = Payment.query.filter_by(uuid=u).first()
                if not paym or paym.status == "success":
                    continue
                updated_count+=1
                paym.status = "success"
                user = paym.user_id
                user = User.query.filter_by(id=user).first()

                if not user:
                    continue

                if paym.plan == "hides":
                    user.free_closes += int(paym.time)
                else:
                    current_time = int(time.time())
                    if user.subscription_expiration > current_time:
                        user.subscription_expiration += paym.time
                    else:
                        user.subscription_expiration = current_time + paym.time
                    user.subscription_type = paym.plan

                db.session.commit()

        return jsonify({
            'message': 'Pending payments checked',
            'checked': len(pending_payments),
            'updated': updated_count
        })
    except Exception as e:
        return jsonify({'message': f'Error checking payments: {str(e)}'}), 500


@app.route('/api/yoomoney/balance', methods=['GET'])
def get_balance():
    user_id = session.get('user_id')
    if user_id is None:
        return jsonify({"error": "Access denied"}), 403

    user = db.session.get(User, user_id)
    if not user or not user.is_admin:
        return jsonify({"error": "Access denied"}), 403
    try:
        # Получаем баланс кошелька
        user = client.account_info()
        balance = round(float(user.balance), 2)

        return jsonify({
            'balance': balance,
            'currency': 'RUB'
        })
    except Exception as e:
        return jsonify({'message': f'Error getting balance: {str(e)}'}), 500

@app.route('/admin/payments')
def admin_payments():
    user_id = session.get('user_id')
    if user_id is None:
        return jsonify({"error": "Access denied"}), 403

    user = db.session.get(User, user_id)
    if not user or not user.is_admin:
        return jsonify({"error": "Access denied"}), 403
    return render_template("admin_pay.html")

# Запуск приложения
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)