# นำเข้าไลบรารีที่จำเป็น
# เพิ่ม redirect และ url_for สำหรับการเปลี่ยนหน้าเว็บ
from flask import Flask, request, abort, render_template, redirect, url_for
import sqlite3
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    # เพิ่ม PushMessageRequest สำหรับการส่งข้อความหาลูกค้า
    TextMessage, PushMessageRequest
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

# สร้าง Flask app
app = Flask(__name__)

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

# ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
# --- ส่วนที่เพิ่มเข้ามาใหม่: ฟังก์ชันสำหรับตอบกลับ ---
@app.route('/send_reply', methods=['POST'])
def send_reply():
    # ดึงข้อมูลจากฟอร์มที่หน้าเว็บส่งมา
    user_id = request.form.get('user_id')
    reply_message = request.form.get('reply_message')

    # ตรวจสอบว่ามีข้อมูลครบถ้วนหรือไม่
    if not user_id or not reply_message:
        return "Missing user_id or reply_message", 400

    try:
        # --- 1. ส่งข้อความไปหาลูกค้าผ่าน LINE API ---
        print(f"กำลังส่งข้อความ '{reply_message}' ไปยัง {user_id}")
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[TextMessage(text=reply_message)]
                )
            )
        print("ส่งข้อความสำเร็จ!")

        # --- 2. บันทึกข้อความของแอดมินลงฐานข้อมูล ---
        conn = sqlite3.connect('chat.db')
        cursor = conn.cursor()
        # เราจะใส่ [Admin] นำหน้าเพื่อแยกแยะว่าเป็นข้อความจากแอดมิน
        admin_message_text = f"[Admin]: {reply_message}"
        cursor.execute("INSERT INTO messages (user_id, message_text) VALUES (?, ?)", 
                       (user_id, admin_message_text))
        conn.commit()
        conn.close()
        print("บันทึกข้อความของแอดมินเรียบร้อยแล้ว")

    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการส่งข้อความ: {e}")

    # --- 3. กลับไปที่หน้า Admin อีกครั้ง ---
    # redirect(url_for('admin_page')) คือการสั่งให้เบราว์เซอร์รีเฟรชไปที่หน้าแอดมิน
    return redirect(url_for('admin_page'))

# ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

# endpoint สำหรับรับข้อมูลจาก LINE (Webhook) - เหมือนเดิม
@app.route("/callback", methods=['POST'])
def callback():
    # ... (ส่วนนี้เหมือนเดิมทั้งหมด ไม่ต้องแก้ไข) ...
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# ฟังก์ชันสำหรับบันทึกข้อความลงฐานข้อมูล - เหมือนเดิม
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    # ... (ส่วนนี้เหมือนเดิมทั้งหมด ไม่ต้องแก้ไข) ...
    user_id = event.source.user_id
    message_text = event.message.text
    print(f"ได้รับข้อความจาก {user_id}: {message_text}")
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

# เริ่มรัน Flask app - เหมือนเดิม
if __name__ == "__main__":
    app.run(port=5000)