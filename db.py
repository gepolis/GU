import math
import time
from email.policy import default

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import BIGINT
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    user_id = db.Column(BIGINT, nullable=False)
    username = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    subscription_type = db.Column(db.String(255), default="N")
    subscription_expiration = db.Column(BIGINT, default=0)
    free_closes = db.Column(BIGINT, default=3)

    # Связь с профилем
    profile = db.relationship('Profile', backref='user', uselist=False)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'is_admin': self.is_admin,
            'created_at': self.created_at,
            'is_active': self.is_active,
            'subscription_type': self.subscription_type,
            'subscription_expiration': self.subscription_expiration,
            'free_closes': self.free_closes
        }


class Profile(db.Model):
    __tablename__ = 'profiles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    photo = db.Column(db.Text, nullable=True)
    last_name = db.Column(db.String(255), nullable=True)
    first_name = db.Column(db.String(255), nullable=True)
    middle_name = db.Column(db.String(255), nullable=True)
    birth_date = db.Column(db.Text, nullable=True)
    birth_place = db.Column(db.String(255), nullable=True)
    passport_number = db.Column(db.String(255), nullable=True)
    passport_issued = db.Column(db.String(255), nullable=True)
    passport_code = db.Column(db.String(255), nullable=True)
    passport_date = db.Column(db.Text, nullable=True)
    registration_address = db.Column(db.Text, nullable=True)
    living_address = db.Column(db.Text, nullable=True)
    snils_number = db.Column(db.String(255), nullable=True)
    inn_number = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_primary = db.Column(db.Boolean, default=False)
    gender = db.Column(db.String(255), default="Мужской")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'showPhoto': User.query.filter(User.id == self.user_id).first().subscription_type != "N",
            'photoInput': self.photo,
            'lastName': self.last_name,
            'firstName': self.first_name,
            'middleName': self.middle_name,
            'birthDate': self.birth_date if self.birth_date else None,
            'birthPlace': self.birth_place,
            'passportNumber': self.passport_number,
            'passportIssued': self.passport_issued,
            'passportCode': self.passport_code,
            'passportDate': self.passport_date if self.passport_date else None,
            'registrationAddress': self.registration_address,
            'livingAddress': self.living_address,
            'snilsNumber': self.snils_number,
            'innNumber': self.inn_number,
            'created_at': self.created_at.isoformat(),
            'is_primary': self.is_primary,
            'gender': self.gender
        }
    def to_small_dict(self):
        return {
        'id': self.id,
        'name': self.name
        }

class AuthUrl(db.Model):
    __tablename__ = 'auth_urls'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.Integer, nullable=False)
    user_id = db.Column(BIGINT, nullable=False)
    username = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(BIGINT, nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    plan = db.Column(db.String(255), nullable=False)
    time = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(255), nullable=False)
    uuid = db.Column(db.String(255), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'amount': self.amount,
            'plan': self.plan,
            'time': self.time,
            'status': self.status,
            'uuid': self.uuid
        }


class Promocode(db.Model):
    __tablename__ = 'promocodes'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(255), nullable=False)
    promo_type = db.Column(db.String(255), nullable=False) #free_closes, plus, premium, discount
    value = db.Column(db.Integer, nullable=False)
    max_uses = db.Column(db.Integer, nullable=False)
    current_uses = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    user_id = db.Column(BIGINT, nullable=True, default=None)
    discount_multi_use = db.Column(db.Boolean, nullable=False, default=False)



    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'promo_type': self.promo_type,
            'value': self.value,
            'max_uses': self.max_uses,
            'current_uses': self.current_uses,
            'is_active': self.is_active
        }


class UserPromocode(db.Model):
    __tablename__ = 'user_promocodes'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False)
    promocode_id = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'promocode_id': self.promocode_id
        }

class ConsentLog(db.Model):
    __tablename__ = 'consent_logs'

    id = db.Column(db.Integer, primary_key=True)

    # ID пользователя, если он авторизован
    user_id = db.Column(db.Integer, nullable=True, index=True)

    # Подтверждение согласий
    agreed_to_terms = db.Column(db.Boolean, default=True)      # Пользовательское соглашение

    ip = db.Column(db.String(45), nullable=False)
    user_agent = db.Column(db.String(256), nullable=False)
    browser = db.Column(db.String(256), nullable=False)
    system = db.Column(db.String(256), nullable=False)
    device = db.Column(db.String(256), nullable=False)

    comment_action = db.Column(db.String(256), nullable=True)

    # Время согласия
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<ConsentLog id={self.id} ip={self.ip_address} time={self.timestamp}>"

class FakeMessageClose(db.Model):
    __tablename__ = 'fake_message_closes'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False)
    ip = db.Column(db.String(45), nullable=False)
    user_agent = db.Column(db.String(256), nullable=False)
    browser = db.Column(db.String(256), nullable=False)
    system = db.Column(db.String(256), nullable=False)
    device = db.Column(db.String(256), nullable=False)
    closed_at = db.Column(db.Integer, default=time.time(), nullable=False)
    closed_to = db.Column(db.Integer, default=time.time()+(60*60*24),nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'ip': self.ip,
            'user_agent': self.user_agent,
            'browser': self.browser,
            'system': self.system,
            'device': self.device,
            'closed_at': self.closed_at,
            'closed_to': self.closed_to
        }

class DocumentScan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, nullable=False)
    scan_data = db.Column(db.Text, nullable=False)  # Data URL скана
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'profile_id': self.profile_id,
            'scan_data': self.scan_data,
            'uploaded_at': self.uploaded_at,
            'is_deleted': self.is_deleted
        }

class ActionLog(db.Model):
    __tablename__ = 'action_logs'

    id = db.Column(db.Integer, primary_key=True)

    # Кто сделал
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True, nullable=True)
    session_id = db.Column(db.String(128), nullable=True)  # можно брать из cookie/session

    # Что сделал
    action_type = db.Column(db.String(64), nullable=False)
    description = db.Column(db.Text, nullable=True)
    mdata = db.Column(db.JSON, nullable=True)
    detail_url = db.Column(db.String(512), nullable=True)

    # Откуда
    ip = db.Column(db.String(45), nullable=False)
    location_country = db.Column(db.String(128), nullable=True)
    location_city = db.Column(db.String(128), nullable=True)
    location_region = db.Column(db.String(128), nullable=True)
    location_lat = db.Column(db.Float, nullable=True)
    location_lon = db.Column(db.Float, nullable=True)
    location_provider = db.Column(db.String(128), nullable=True)

    # С чего
    user_agent = db.Column(db.String(512), nullable=False)
    browser = db.Column(db.String(128), nullable=False)
    os = db.Column(db.String(128), nullable=False)
    device_type = db.Column(db.String(64), nullable=False)     # Mobile, Tablet, PC, Bot, Unknown
    device_brand = db.Column(db.String(64), nullable=True)     # Apple, Samsung, etc.
    device_model = db.Column(db.String(64), nullable=True)

    # Доп. контекст
    language = db.Column(db.String(64), nullable=True)
    screen_resolution = db.Column(db.String(64), nullable=True)
    referer = db.Column(db.String(512), nullable=True)
    origin = db.Column(db.String(512), nullable=True)

    # Когда
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "action_type": self.action_type,
            "description": self.description,
            "metadata": self.mdata,
            "detail_url": self.detail_url,
            "ip": self.ip,
            "location": {
                "country": self.location_country,
                "region": self.location_region,
                "city": self.location_city,
                "lat": self.location_lat,
                "lon": self.location_lon,
                "provider": self.location_provider
            },
            "device": {
                "browser": self.browser,
                "os": self.os,
                "type": self.device_type,
                "brand": self.device_brand,
                "model": self.device_model,
                "user_agent": self.user_agent
            },
            "context": {
                "language": self.language,
                "screen_resolution": self.screen_resolution,
                "referer": self.referer,
                "origin": self.origin
            },
            "timestamp": self.timestamp.isoformat()
        }


class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    advertiser_id = db.Column(BIGINT, nullable=False)  # ID рекламодателя
    title = db.Column(db.String(255), nullable=False)      # Название задания
    description = db.Column(db.Text, nullable=True)        # Описание задания
    url = db.Column(db.String(500), nullable=False)        # Ссылка
    url_id = db.Column(BIGINT, nullable=False) # id тг канала для проверки
    reward = db.Column(db.Integer, nullable=False, default=1)  # Сколько скрытий выдаётся
    target_completions = db.Column(db.Integer, nullable=False, default=10)  # Сколько выполнений нужно
    completions = db.Column(db.Integer, nullable=False, default=0)          # Сколько уже выполнено
    is_active = db.Column(db.Boolean, default=True)        # Активно ли задание
    created_at = db.Column(db.DateTime, default=datetime.utcnow)            # Когда создано
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # Когда обновлено

    def __repr__(self):
        return f"<Task {self.title} ({self.completions}/{self.target_completions})>"

class TaskCompletion(db.Model):
    __tablename__ = 'task_completions'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    user_id = db.Column(BIGINT, nullable=False)  # ID пользователя в твоём боте
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Связь с заданием (можешь удобно обращаться completion.task)
    task = db.relationship('Task', backref=db.backref('completions_list', lazy=True))

    def __repr__(self):
        return f"<TaskCompletion user_id={self.user_id} task_id={self.task_id}>"

class BlackListIP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(45), unique=True, nullable=False)
    reason = db.Column(db.String(255), nullable=True)
    source = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<BlackListIP {self.ip}>"

    def to_dict(self):
        return {
            'id': self.id,
            'ip': self.ip,
            'reason': self.reason,
            'source': self.source,
        }