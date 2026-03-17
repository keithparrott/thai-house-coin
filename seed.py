"""Seed the database with an admin user."""
import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app
from app.extensions import db
from app.models.user import User

app = create_app(os.environ.get('FLASK_ENV', 'development'))

with app.app_context():
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            display_name='Admin',
            role='admin',
            must_change_password=True
        )
        admin.set_password('changeme')
        db.session.add(admin)
        db.session.commit()
        print('Admin user created. Username: admin / Password: changeme')
    else:
        print('Admin user already exists.')
