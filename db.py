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
    free_closes = db.Column(BIGINT, default=0)

    # Связь с профилем
    profile = db.relationship('Profile', backref='user', uselist=False)


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


class Promocode(db.Model):
    __tablename__ = 'promocodes'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(255), nullable=False)
    promo_type = db.Column(db.String(255), nullable=False) #free_closes, plus, premium
    value = db.Column(db.Integer, nullable=False)
    max_uses = db.Column(db.Integer, nullable=False)
    current_uses = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, default=True)


class UserPromocode(db.Model):
    __tablename__ = 'user_promocodes'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False)
    promocode_id = db.Column(db.Integer, nullable=False)

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

