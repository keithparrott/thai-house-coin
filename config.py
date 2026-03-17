import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True


class DevConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', f'sqlite:///{os.path.join(basedir, "instance", "thc.db")}'
    )


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SERVER_NAME = 'localhost'


class ProdConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', '')

    def __init__(self):
        # Render uses postgres:// but SQLAlchemy needs postgresql://
        if self.SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
            self.SQLALCHEMY_DATABASE_URI = self.SQLALCHEMY_DATABASE_URI.replace(
                'postgres://', 'postgresql://', 1
            )


config = {
    'development': DevConfig,
    'testing': TestConfig,
    'production': ProdConfig,
    'default': DevConfig,
}
