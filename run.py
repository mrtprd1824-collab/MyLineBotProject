import eventlet
eventlet.monkey_patch()

from app import create_app, socketio
from app.models import User, Message, LineAccount, Group, QuickReply
from flask import send_from_directory
import os

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        "db": db,
        "User": User,
        "Message": Message,
        "LineAccount": LineAccount,
        "Group": Group,
        "QuickReply": QuickReply,
    }

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)

@app.route('/OneSignalSDKWorker.js')
def onesignal_worker():
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'app'), 'OneSignalSDKWorker.js')

@app.route('/OneSignalSDKUpdaterWorker.js')
def onesignal_updater():
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'app'), 'OneSignalSDKUpdaterWorker.js')

