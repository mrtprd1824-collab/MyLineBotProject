from app import app, db
from app.models import User

# ฟังก์ชันนี้จะทำให้เราสามารถเรียกดูตัวแปรใน PowerShell ได้ง่ายขึ้น
# เวลาที่เราจะทดลองคำสั่งต่างๆ
@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User}

if __name__ == "__main__":
    app.run(debug=True) # เพิ่ม debug=True เพื่อให้ง่ายต่อการพัฒนา