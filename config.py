from sqlalchemy.pool import NullPool
import os

# basedir ตอนนี้จะชี้ไปที่ root ของโปรเจกต์ (MyLineBotProject)
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "you-will-never-guess")
    
    # แก้ไข URI ให้ชี้ไปที่ไฟล์ฐานข้อมูลที่ถูกต้องภายในโฟลเดอร์ instance
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(basedir, 'instance', 'app.db')}"
    )
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ✅ เพิ่มบรรทัดนี้เพื่อแก้ปัญหา eventlet + SQLite lock
    SQLALCHEMY_ENGINE_OPTIONS = {
        "poolclass": NullPool
    }
    
    # แก้ไข UPLOAD_FOLDER ให้ชี้ไปที่โฟลเดอร์ uploads ที่ถูกต้อง
    UPLOAD_FOLDER = os.path.join(basedir, 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    # REMEMBER to update the fallback URL when you restart ngrok.
    # --- VVVV ใส่ URL ใหม่ของคุณที่นี่ VVVV ---
    BASE_URL = os.environ.get("BASE_URL", "https://cc46a88fee89.ngrok-free.app") 


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
