from flask import render_template, flash, redirect, url_for, request, abort, jsonify, current_app, Blueprint
from sqlalchemy import func
from app import db, models
from app.forms import LoginForm, RegistrationForm, LineAccountForm
from flask_login import current_user, login_user, logout_user, login_required

# --- ส่วน import ของ LINE ---
from linebot.v3 import WebhookParser # <-- เปลี่ยนมาใช้ Parser โดยตรง
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, TextMessage, PushMessageRequest
from linebot.v3.webhooks import MessageEvent, TextMessageContent

# สร้าง Blueprint ชื่อ 'main'
bp = Blueprint('main', __name__)

# --- Routes (ส่วนนี้ไม่มีการเปลี่ยนแปลง) ---

@bp.route('/')
@bp.route('/index')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.chat_page'))
    return redirect(url_for('main.login'))

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.chat_page'))
    form = LoginForm()
    if form.validate_on_submit():
        user = models.User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('main.login'))
        login_user(user, remember=form.remember_me.data)
        return redirect(url_for('main.chat_page'))
    return render_template('login.html', title='Sign In', form=form)

@bp.route('/chat')
@login_required
def chat_page():
    conversations = db.session.query(
        models.Message.user_id,
        func.max(models.Message.timestamp).label('last_timestamp'),
        func.substr(models.Message.message_text, 1, 30).label('last_message'),
        models.LineProfile.display_name,
        models.LineProfile.picture_url
    ).join(
        models.LineProfile, models.Message.user_id == models.LineProfile.user_id, isouter=True
    ).group_by(models.Message.user_id).order_by(func.max(models.Message.timestamp).desc()).all()
    
    return render_template('chat.html', conversations=conversations, title="ห้องแชททั้งหมด")

@bp.route('/api/conversations')
@login_required
def conversations_api():
    conversations = db.session.query(
        models.Message.user_id,
        func.max(models.Message.timestamp).label('last_timestamp'),
        func.substr(models.Message.message_text, 1, 30).label('last_message'),
        models.LineProfile.display_name,
        models.LineProfile.picture_url
    ).join(
        models.LineProfile, models.Message.user_id == models.LineProfile.user_id, isouter=True
    ).group_by(models.Message.user_id).order_by(func.max(models.Message.timestamp).desc()).all()
    conv_data = [{'user_id': c.user_id, 'last_timestamp': c.last_timestamp.strftime('%H:%M'), 'last_message': c.last_message, 'display_name': c.display_name or c.user_id, 'picture_url': c.picture_url or 'https://via.placeholder.com/50'} for c in conversations]
    return jsonify(conv_data)

@bp.route('/api/messages/<user_id>')
@login_required
def get_messages(user_id):
    messages = models.Message.query.filter_by(user_id=user_id).order_by(models.Message.timestamp.asc()).all()
    messages_data = [{'user_id': msg.user_id, 'message_text': msg.message_text, 'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')} for msg in messages]
    return jsonify(messages_data)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/manage_users', methods=['GET', 'POST'])
@login_required
def manage_users():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = models.User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you have registered a new user!')
        return redirect(url_for('main.manage_users'))
    all_users = models.User.query.all()
    return render_template('manage_users.html', title='Manage Users', form=form, users=all_users)
    
@bp.route('/manage_line_accounts', methods=['GET', 'POST'])
@login_required
def manage_line_accounts():
    form = LineAccountForm()
    if form.validate_on_submit():
        new_account = models.LineAccount(account_name=form.account_name.data, channel_id=form.channel_id.data, channel_secret=form.channel_secret.data, channel_access_token=form.channel_access_token.data)
        db.session.add(new_account)
        db.session.commit()
        flash('เพิ่มบัญชี LINE OA ใหม่เรียบร้อยแล้ว!')
        return redirect(url_for('main.manage_line_accounts'))
    all_accounts = models.LineAccount.query.all()
    return render_template('manage_line_accounts.html', title='Manage LINE OAs', form=form, accounts=all_accounts)

# --- Webhook (เวอร์ชันแก้ไขใหม่ทั้งหมด) ---
@bp.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    body_json = request.get_json()
    
    try:
        destination_id = body_json.get('destination')
        if not destination_id: return 'OK'

        line_account = models.LineAccount.query.filter_by(channel_id=destination_id).first()
        if not line_account:
            print(f"Unknown destination: {destination_id}")
            return 'OK'

        parser = WebhookParser(line_account.channel_secret)
        events = parser.parse(body, signature)

        for event in events:
            if isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
                handle_message_logic(event, line_account)

    except InvalidSignatureError:
        print("Invalid signature. Please check your channel secret.")
        abort(400)
    except Exception as e:
        print(f"An error occurred in callback: {e}")
        abort(500)
            
    return 'OK'

def handle_message_logic(event, line_account):
    user_id = event.source.user_id
    message_text = event.message.text
    
    profile = models.LineProfile.query.get(user_id)
    if not profile:
        try:
            configuration = Configuration(access_token=line_account.channel_access_token)
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                user_profile = line_bot_api.get_profile(user_id)
                new_profile = models.LineProfile(user_id=user_profile.user_id, display_name=user_profile.display_name, picture_url=user_profile.picture_url)
                db.session.add(new_profile)
        except Exception as e:
            print(f"Error getting profile for {user_id}: {e}")
    
    new_message = models.Message(
        user_id=user_id, 
        message_text=message_text,
        line_account_id=line_account.id
    )
    db.session.add(new_message)
    db.session.commit()
    print(f"SUCCESS: Saved message from {user_id} for Line Account: {line_account.account_name}")


@bp.route('/send_reply', methods=['POST'])
@login_required
def send_reply():
    user_id = request.form.get('user_id')
    reply_message_text = request.form.get('reply_message')
    if not user_id or not reply_message_text:
        return jsonify({'status': 'error', 'message': 'Missing data'}), 400

    try:
        last_msg = models.Message.query.filter_by(user_id=user_id).order_by(models.Message.timestamp.desc()).first()
        if not last_msg or not last_msg.line_account:
            raise Exception("Cannot find which LINE OA to reply with.")

        line_account = last_msg.line_account
        configuration = Configuration(access_token=line_account.channel_access_token)
        
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.push_message(PushMessageRequest(to=user_id, messages=[TextMessage(text=reply_message_text)]))

        admin_message_text = f"[Admin]: {reply_message_text}"
        new_admin_message = models.Message(
            user_id=user_id, 
            message_text=admin_message_text,
            line_account_id=line_account.id
        )
        db.session.add(new_admin_message)
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error sending message: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500