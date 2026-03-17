from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(128), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(16), nullable=False, default='user')
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    must_change_password = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    @property
    def is_admin(self):
        return self.role == 'admin'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'
