from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    username = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Связь с профилем
    profile = db.relationship('Profile', backref='user', uselist=False)


class Profile(db.Model):
    __tablename__ = 'profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    photo = db.Column(db.Text, nullable=True)
    last_name = db.Column(db.String(255), nullable=True)
    first_name = db.Column(db.String(255), nullable=True)
    middle_name = db.Column(db.String(255), nullable=True)
    birth_date = db.Column(db.Date, nullable=True)
    birth_place = db.Column(db.String(255), nullable=True)
    passport_number = db.Column(db.String(255), nullable=True)
    passport_issued = db.Column(db.String(255), nullable=True)
    passport_code = db.Column(db.String(255), nullable=True)
    passport_date = db.Column(db.Date, nullable=True)
    registration_address = db.Column(db.Text, nullable=True)
    living_address = db.Column(db.Text, nullable=True)
    snils_number = db.Column(db.String(255), nullable=True)
    inn_number = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
