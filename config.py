import os

class Config:
    SECRET_KEY = 'adun-school-archive-project2026'
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:star24@localhost/school_photo_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER ='static/uploads'
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024
    