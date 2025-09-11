import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-super-secret-key-that-is-hard-to-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # !!! อย่าลืมใส่ค่าจริงของ LINE OA หลักของคุณที่นี่ !!!
    LINE_CHANNEL_ACCESS_TOKEN = 'YOUR_CHANNEL_ACCESS_TOKEN'
    LINE_CHANNEL_SECRET = 'YOUR_CHANNEL_SECRET'