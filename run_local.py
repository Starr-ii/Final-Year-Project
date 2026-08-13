"""Local demo launcher: uses SQLite instead of MySQL and seeds an admin user.

Does not modify the original app code. Run with: python run_local.py
"""
import os

from config import Config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
Config.SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'local_dev.db')

from app import create_app, db, bcrypt
from app.models import User

app = create_app()

with app.app_context():
    if not User.query.filter_by(email='admin@local.test').first():
        admin = User(
            full_name='Local Admin',
            email='admin@local.test',
            password=bcrypt.generate_password_hash('admin123').decode('utf-8'),
            role='admin',
        )
        db.session.add(admin)
        db.session.commit()
        print('Seeded admin user: admin@local.test / admin123')

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, port=5000)
