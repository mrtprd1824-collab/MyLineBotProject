import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_socketio import SocketIO
from sqlalchemy import MetaData
from config import config

# Naming convention for SQLite constraints
naming_convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

db = SQLAlchemy(metadata=MetaData(naming_convention=naming_convention))
migrate = Migrate()
login_manager = LoginManager()
socketio = SocketIO(async_mode='eventlet')

def create_app(config_name='default'):
    # ทำให้ง่ายขึ้น: instance_relative_config=True จะบอกให้ Flask
    # มองหาโฟลเดอร์ 'instance' ที่ root level โดยอัตโนมัติ
    app = Flask(__name__, instance_relative_config=True)
    
    # โหลด Config จาก object
    # Flask จะรู้ว่าต้องสร้าง instance folder ที่ไหนจาก flag ด้านบน
    app.config.from_object(config[config_name])
    
    # สร้างโฟลเดอร์ instance (ที่เก็บ database) หากยังไม่มี
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass 

    # สร้างโฟลเดอร์ UPLOAD_FOLDER หากยังไม่มี
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'])
    except OSError:
        pass

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    login_manager.init_app(app)
    socketio.init_app(app)

    login_manager.login_view = "main.login"

    # Import and register blueprints
    from . import routes
    app.register_blueprint(routes.bp)

    return app

