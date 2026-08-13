import os

class Config:
    # Override these with environment variables in production —
    # never commit real secrets to git.
    SECRET_KEY = os.environ.get(
        'SECRET_KEY', 'dev-only-secret-key-change-me')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'mysql+pymysql://root:star24@localhost/school_photo_db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024
