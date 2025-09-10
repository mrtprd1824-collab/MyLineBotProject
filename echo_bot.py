# นำเข้าไลบรารีที่จำเป็น
from flask import Flask, request, abort, render_template, redirect, url_for
import sqlite3
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    TextMessage, PushMessageRequest
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

# สร้าง Flask app
app = Flask(__name__)

# ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
# --- ส่วนที่เพิ่มเข้ามาใหม่: ฟังก์ชันสำหรับสร้างตารางในฐานข้อมูล ---
def init_database():
    """ฟังก์ชันนี้จะตรวจสอบและสร้างตาราง messages ถ้ายังไม่มี"""
    conn = sqlite3.connect('chat.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            message_text TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    print("Database initialized.")
# ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

# ตั้งค่า Configuration ของ LINE Bot
configuration = Configuration(access_token='xfLcJRS8tj7XIGg8zKJBSyXT8zrxftGgxRJuKd3orK7xTy8X08s8N4F7RDhNrhmOyicgATkJNmJPcKXz1Yzu/8dQsH0ZYxIpGfanq6Yxv5MTLljMh+vEt3zwUCnae/bs9C+cVcfc/MAQyV97udtYtAdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('9d4c6369a96dddbb4b3550795245dbbc')


# --- หน้าเว็บสำหรับ Admin (เหมือนเดิม) ---
@app.route("/admin")
def admin_page():
    conn = sqlite3.connect('chat.db')
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM messages ORDER BY timestamp DESC")
    messages = cursor.fetchall()
    conn.close()
    return render_template('admin.html', messages=messages)

# --- ฟังก์ชันสำหรับตอบกลับ (เหมือนเดิม) ---
@app.route('/send_reply', methods=['POST'])
def send_reply():
    user_id = request.form.get('user_id')
    reply_message = request.form.get('reply_message')
    if not user_id or not reply_message:
        return "Missing user_id or reply_message", 400
    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.push_message(
                PushMessageRequest(to=user_id, messages=[TextMessage(text=reply_message)])
            )
        conn = sqlite3.connect('chat.db')
        cursor = conn.cursor()
        admin_message_text = f"[Admin]: {reply_message}"
        cursor.execute("INSERT INTO messages (user_id, message_text) VALUES (?, ?)", 
                       (user_id, admin_message_text))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการส่งข้อความ: {e}")
    return redirect(url_for('admin_page'))

# --- Webhook และฟังก์ชัน handle_message (เหมือนเดิม) ---
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
    user_id = event.source.user_id
    message_text = event.message.text
    try:
        conn = sqlite3.connect('chat.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO messages (user_id, message_text) VALUES (?, ?)", 
                       (user_id, message_text))
        conn.commit()
    except sqlite3.Error as e:
        print(f"เกิดข้อผิดพลาดเกี่ยวกับฐานข้อมูล: {e}")
    finally:
        if conn:
            conn.close()

# --- ส่วนเริ่มรันเซิร์ฟเวอร์ ---
if __name__ != '__main__':
    # เมื่อรันบน Gunicorn (บน Render) ให้สร้างฐานข้อมูลก่อน
    init_database()

if __name__ == "__main__":
    # เมื่อรันบนเครื่องเราเอง ก็ให้สร้างฐานข้อมูลก่อน
    init_database()
    app.run(port=5000)