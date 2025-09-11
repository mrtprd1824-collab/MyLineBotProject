from app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), index=True, default='staff')
    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)
    def __repr__(self): return f'<User {self.username}>'

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(64), index=True)
    message_text = db.Column(db.String(1024))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    line_account_id = db.Column(db.Integer, db.ForeignKey('line_account.id'))
    def __repr__(self): return f'<Message {self.message_text}>'

class LineProfile(db.Model):
    user_id = db.Column(db.String(64), primary_key=True)
    display_name = db.Column(db.String(128), index=True)
    picture_url = db.Column(db.String(256))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    def __repr__(self): return f'<LineProfile {self.display_name}>'
            
class LineAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_name = db.Column(db.String(128), index=True, unique=True)
    channel_id = db.Column(db.String(64), index=True, unique=True)
    channel_secret = db.Column(db.String(128))
    channel_access_token = db.Column(db.String(256))
    messages = db.relationship('Message', backref='line_account', lazy='dynamic')
    def __repr__(self): return f'<LineAccount {self.account_name}>'