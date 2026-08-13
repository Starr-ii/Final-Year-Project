import os

import click
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_wtf import CSRFProtect
from config import Config


db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'),
        static_folder=os.path.join(os.path.dirname(__file__), '..', 'static'))

    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = 'main.login'

    from app.routes import main
    app.register_blueprint(main)

    with app.app_context():
        from app import models
        db.create_all()

    register_cli(app)

    return app


def register_cli(app):
    @app.cli.command('create-admin')
    @click.option('--name', prompt='Full name')
    @click.option('--email', prompt='Email')
    @click.option('--password', prompt=True, hide_input=True,
                  confirmation_prompt=True)
    def create_admin(name, email, password):
        """Create an administrator account."""
        from app.models import User
        email = email.strip().lower()
        if User.query.filter_by(email=email).first():
            click.echo('A user with that email already exists.')
            return
        db.session.add(User(
            full_name=name.strip(),
            email=email,
            password=bcrypt.generate_password_hash(password).decode('utf-8'),
            role='admin',
        ))
        db.session.commit()
        click.echo(f'Admin account created for {email}.')

from app.models import User

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
