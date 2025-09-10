import sqlite3

# เชื่อมต่อกับฐานข้อมูล (ถ้ายังไม่มีไฟล์นี้ มันจะสร้างให้เอง)
conn = sqlite3.connect('chat.db')

# สร้าง "พนักงาน" สำหรับส่งคำสั่ง
cursor = conn.cursor()

# ส่งคำสั่ง SQL เพื่อสร้างตู้เก็บเอกสารชื่อ 'messages'
# ตู้นี้จะมีช่องเก็บ ID, ID ผู้ใช้, ข้อความ, และเวลา
cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        message_text TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
''')

# ยืนยันการเปลี่ยนแปลงและปิดการเชื่อมต่อ
conn.commit()
conn.close()

print("ฐานข้อมูล 'chat.db' และตาราง 'messages' ถูกสร้างเรียบร้อยแล้ว!")