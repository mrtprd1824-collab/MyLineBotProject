from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

app = Flask(__name__)
app.config.from_object(Config)

# สร้างอ็อบเจกต์สำหรับจัดการฐานข้อมูลและ Login
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login = LoginManager(app)
# บอก LoginManager ว่าถ้าเจอคนไม่ได้ล็อกอิน ให้ส่งไปที่หน้า 'login'
login.login_view = 'login'

# นำเข้า routes และ models เพื่อให้แอปพลิเคชันรู้จัก
# (สำคัญ: ต้อง import ไว้ท้ายสุดเพื่อป้องกัน circular imports)
from app import routes, models