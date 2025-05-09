from email.policy import default

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    user_id = db.Column(db.BigInteger, nullable=False)
    username = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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

class AuthUrl(db.Model):
    __tablename__ = 'auth_urls'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    username = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)