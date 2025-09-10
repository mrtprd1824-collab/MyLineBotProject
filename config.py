import os

class Config:
    # สร้าง SECRET_KEY แบบสุ่ม เพื่อความปลอดภัยของ session
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-super-secret-key-that-is-hard-to-guess'
    
    # ตั้งค่าฐานข้อมูล (จะสร้างไฟล์ app.db ขึ้นมาในโฟลเดอร์หลัก)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ค่า LINE API (เราจะย้ายมาเก็บที่นี่ที่เดียว)
    LINE_CHANNEL_ACCESS_TOKEN = 'xfLcJRS8tj7XIGg8zKJBSyXT8zrxftGgxRJuKd3orK7xTy8X08s8N4F7RDhNrhmOyicgATkJNmJPcKXz1Yzu/8dQsH0ZYxIpGfanq6Yxv5MTLljMh+vEt3zwUCnae/bs9C+cVcfc/MAQyV97udtYtAdB04t89/1O/w1cDnyilFU='
    LINE_CHANNEL_SECRET = '9d4c6369a96dddbb4b3550795245dbbc'