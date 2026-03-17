import os

from flask import Flask
from sqlalchemy import event
from sqlalchemy.engine import Engine

from config import config


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')

    app = Flask(__name__)

    cfg = config[config_name]
    if isinstance(cfg, type):
        app.config.from_object(cfg())
    else:
        app.config.from_object(cfg)

    # SQLite WAL mode for better concurrency
    uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if 'sqlite' in uri:
        @event.listens_for(Engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    from app.extensions import db, login_manager, csrf

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Force password change before any request
    from flask_login import current_user
    from flask import redirect, url_for, request

    @app.before_request
    def check_password_change():
        if current_user.is_authenticated and current_user.must_change_password:
            allowed = {'auth.change_password', 'auth.logout', 'static'}
            if request.endpoint not in allowed:
                return redirect(url_for('auth.change_password'))

    from app.routes import register_blueprints
    register_blueprints(app)

    with app.app_context():
        db.create_all()

    return app
