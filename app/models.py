from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import JSON as JSONType

from app import db  # db is created in app/__init__.py

class Participant(db.Model):
    __tablename__ = 'participant'
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    condition = db.Column(db.String(16), nullable=False)  # 'control' or 'ai'
    worker_id = db.Column(db.String(128))
    assignment_id = db.Column(db.String(128))
    hit_id = db.Column(db.String(128))
    completion_code = db.Column(db.String(32), index=True)

class Trial(db.Model):
    __tablename__ = 'trial'
    id = db.Column(db.Integer, primary_key=True)
    payload = db.Column(JSONType, nullable=False)  # stores dilemma_text, gt, ai fields
    split = db.Column(db.String(32), default='all', index=True)

class Assignment(db.Model):
    __tablename__ = 'assignment'
    id = db.Column(db.Integer, primary_key=True)
    participant_id = db.Column(db.Integer, db.ForeignKey('participant.id'), index=True, nullable=False)
    trial_id = db.Column(db.Integer, db.ForeignKey('trial.id'), index=True, nullable=False)
    order_idx = db.Column(db.Integer, default=0)

class Response(db.Model):
    __tablename__ = 'response'
    id = db.Column(db.Integer, primary_key=True)
    participant_id = db.Column(db.Integer, db.ForeignKey('participant.id'), index=True, nullable=False)
    trial_id = db.Column(db.Integer, db.ForeignKey('trial.id'), index=True, nullable=False)
    answer = db.Column(JSONType)     # { "value": 1..5 }
    correct = db.Column(db.Boolean)  # keep null; we’ll analyze offline vs GT
    rt_ms = db.Column(db.Integer)
    revealed_ai = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AIEvent(db.Model):
    __tablename__ = 'ai_event'
    id = db.Column(db.Integer, primary_key=True)
    participant_id = db.Column(db.Integer, db.ForeignKey('participant.id'), index=True)
    trial_id = db.Column(db.Integer, db.ForeignKey('trial.id'), index=True)
    event_type = db.Column(db.String(64))  # 'ai_shown', 'prompt', 'output', 'survey', etc.
    payload = db.Column(JSONType)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
