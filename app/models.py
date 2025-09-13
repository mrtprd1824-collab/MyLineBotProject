from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy import MetaData
from flask_sqlalchemy import SQLAlchemy
from app import login_manager, db

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(128), nullable=True)
    role = db.Column(db.String(20), default="staff")
    line_user_id = db.Column(db.String(64), unique=True, nullable=True)
    picture_url = db.Column(db.String(255), nullable=True)

    # เบอร์โทรและโน้ต
    phone = db.Column(db.String(20), nullable=True)
    note = db.Column(db.Text, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"

class LineAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    channel_id = db.Column(db.String(100), nullable=False)
    channel_secret = db.Column(db.String(100), nullable=False)
    channel_access_token = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f"<LineAccount {self.name}>"

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<Group {self.name}>"

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)  # ✅ เพิ่ม index
    message_type = db.Column(db.String(20), nullable=False, default="text")
    media_url = db.Column(db.String(255), nullable=True)
    sticker_id = db.Column(db.String(50), nullable=True)
    package_id = db.Column(db.String(50), nullable=True)
    is_read = db.Column(db.Boolean, nullable=False, default=False, server_default=db.text('0'))

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True, index=True)          # ✅ เพิ่ม index
    recipient_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True, index=True)    # ✅ เพิ่ม index
    line_account_id = db.Column(db.Integer, db.ForeignKey("line_account.id"), nullable=True, index=True)  # ✅ เพิ่ม index

    author = db.relationship("User", foreign_keys=[user_id], backref=db.backref('sent_messages', lazy='joined'))
    recipient = db.relationship("User", foreign_keys=[recipient_id], backref=db.backref('received_messages', lazy='joined'))
    line_account = db.relationship("LineAccount", backref="messages")

    def __repr__(self):
        return f"<Message {self.id} {self.message_type}>"


class QuickReply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, server_default='')
    text = db.Column(db.String(1000), nullable=False)
    line_account_id = db.Column(db.Integer, db.ForeignKey("line_account.id"), nullable=True)

    line_account = db.relationship("LineAccount", backref="quick_replies")

    def __repr__(self):
        return f"<QuickReply {self.name}>"

