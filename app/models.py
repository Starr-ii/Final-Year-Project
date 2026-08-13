from app import db
from flask_login import UserMixin
from datetime import datetime, timezone

def utcnow():
    return datetime.now(timezone.utc)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='student')
    date_registered = db.Column(db.DateTime, default=utcnow)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_name = db.Column(db.String(150), nullable=False)
    event_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text, nullable=True)
    photos = db.relationship('Photo', backref='event',
                             cascade='all, delete-orphan')

class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    upload_date = db.Column(db.DateTime, default=utcnow)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'),
                         nullable=False)
    faces_detected = db.Column(db.Integer, default=0)
    face_tags = db.relationship('FaceTag', backref='photo',
                                cascade='all, delete-orphan')

class FaceTag(db.Model):
    __tablename__ = 'face_tag'
    id = db.Column(db.Integer, primary_key=True)
    photo_id = db.Column(db.Integer, db.ForeignKey('photo.id'),
                         nullable=False)
    person_name = db.Column(db.String(100), nullable=True)
    x = db.Column(db.Integer, nullable=True)
    y = db.Column(db.Integer, nullable=True)
    width = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Integer, nullable=True)