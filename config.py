import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-me')

    _uri = os.environ.get('DATABASE_URL')
    if _uri:
        # Render/Heroku still sometimes hand out postgres://; SQLAlchemy wants postgresql://
        _uri = _uri.replace("postgres://", "postgresql://", 1)
        # Render Postgres needs SSL
        if "sslmode" not in _uri:
            _uri += ("&" if "?" in _uri else "?") + "sslmode=require"
        SQLALCHEMY_DATABASE_URI = _uri
    else:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(basedir, 'app.db')}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
