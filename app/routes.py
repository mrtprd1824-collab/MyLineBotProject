from flask import render_template, flash, redirect, url_for, request, abort
from app import app, db
from app.forms import LoginForm
from app.models import User, Message # << เพิ่ม Message model
from flask_login import current_user, login_user, logout_user, login_required

# --- ส่วนตั้งค่าการเชื่อมต่อกับ LINE ---
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    TextMessage, PushMessageRequest
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

# ดึงค่า Access Token และ Secret จากไฟล์ config.py
configuration = Configuration(access_token=app.config['LINE_CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(app.config['LINE_CHANNEL_SECRET'])
# --- สิ้นสุดส่วนตั้งค่า LINE ---


# หน้าแรกของเว็บ
@app.route('/')
@app.route('/index')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('chat_page'))
    return redirect(url_for('login'))

# หน้าล็อกอิน
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('chat_page'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        return redirect(url_for('chat_page'))
        
    return render_template('login.html', title='Sign In', form=form)

# หน้าแชท (หน้า admin เดิมที่อัปเกรดแล้ว)
@app.route('/chat')
@login_required 
def chat_page():
    # ดึงข้อมูล Message ทั้งหมดจากฐานข้อมูล โดยเรียงจากใหม่สุดไปเก่าสุด
    messages = Message.query.order_by(Message.timestamp.desc()).all()
    return render_template('chat.html', messages=messages)

# ฟังก์ชันสำหรับ Logout
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

# --- ส่วน Webhook สำหรับรับข้อความจาก LINE ---
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    # บันทึกข้อความที่ได้รับจากลูกค้าลง DB
    user_id = event.source.user_id
    message_text = event.message.text
    
    new_message = Message(user_id=user_id, message_text=message_text)
    db.session.add(new_message)
    db.session.commit()
    print(f"Saved message from {user_id}: {message_text}")

# --- ส่วนสำหรับตอบกลับข้อความจากหน้าเว็บ Admin ---
@app.route('/send_reply', methods=['POST'])
@login_required
def send_reply():
    user_id = request.form.get('user_id')
    reply_message_text = request.form.get('reply_message')

    if not user_id or not reply_message_text:
        return "Missing data", 400

    try:
        # 1. ส่งข้อความไปหาลูกค้าผ่าน LINE API
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[TextMessage(text=reply_message_text)]
                )
            )

        # 2. บันทึกข้อความของแอดมินลงฐานข้อมูล
        admin_message_text = f"[Admin]: {reply_message_text}"
        new_admin_message = Message(user_id=user_id, message_text=admin_message_text)
        db.session.add(new_admin_message)
        db.session.commit()

    except Exception as e:
        print(f"Error sending message: {e}")

    return redirect(url_for('chat_page'))