from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# these imports MUST be after db is created so Alembic can autogenerate
from app import models, routes  # <- keep both

# Register custom CLI commands (import after models are defined)
from app.cli import import_ai_confidence
app.cli.add_command(import_ai_confidence)
