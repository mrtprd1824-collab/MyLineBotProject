import os
import datetime
import re
from functools import wraps
from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, current_app, send_from_directory,
    render_template_string, jsonify
)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import or_, and_, distinct
from app import db, socketio
from app.models import User, LineAccount, Group, Message, QuickReply
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, StickerMessage, ImageMessage,
    TextSendMessage, ImageSendMessage, StickerSendMessage
)

bp = Blueprint("main", __name__)

# ===================== HTML Templates for SocketIO =====================
USER_LIST_ITEM_HTML = """
<a href="{{ url_for('main.chat_all', user_id=data.user_info.id) }}"
   class="list-group-item list-group-item-action {% if selected_user and selected_user.id == data.user_info.id %}active{% endif %}"
   style="{% if data.unread_count > 0 %}background-color:#e6ffe6 !important;{% endif %}"
   id="user-list-{{ data.user_info.id }}">
  <div class="d-flex w-100 align-items-center">
    {% if data.user_info.picture_url %}
      <img src="{{ data.user_info.picture_url }}" alt="{{ data.user_info.username }}" class="avatar avatar-sidebar">
    {% else %}
      <div class="avatar avatar-sidebar avatar-placeholder"><i class="bi bi-person-fill"></i></div>
    {% endif %}
    <div class="user-list-info ms-2">
      <div class="user-list-header">
        <div class="fw-semibold text-truncate">{{ data.user_info.username }}</div>
        {% if data.last_message %}<div class="small text-muted flex-shrink-0 ps-2">{{ data.last_message.timestamp.strftime('%H:%M') }}</div>{% endif %}
      </div>
      <div class="user-list-body">
        <div class="small text-muted text-truncate">
          {% if data.last_message %}
            {% if data.last_message.message_type == 'text' %}
              {{ data.last_message.text }}
            {% elif data.last_message.message_type == 'image' %}
              <i class="bi bi-image-fill"></i> รูปภาพ
            {% elif data.last_message.message_type == 'sticker' %}
              <i class="bi bi-sticky-fill"></i> สติ๊กเกอร์
            {% endif %}
          {% else %}
            <i>No messages yet</i>
          {% endif %}
        </div>
        {% if data.unread_count > 0 %}<span class="badge bg-danger rounded-pill ms-auto" id="unread-count-{{ data.user_info.id }}">{{ data.unread_count }}</span>{% endif %}
      </div>
    </div>
  </div>
</a>
"""

MESSAGE_BUBBLE_HTML = """
<div class="mb-3 d-flex flex-column {% if msg.user_id == current_user.id %}msg-right{% else %}msg-left{% endif %}">
    {% if msg.message_type == 'text' %}
        <div class="{% if msg.user_id == current_user.id %}bubble-right{% else %}bubble-left{% endif %}">
        {{ msg.text | safe }}
        </div>
    {% elif msg.message_type == 'image' %}
        <img src="{{ url_for('static', filename='uploads/' + msg.media_url) }}" class="chat-image" data-bs-toggle="modal" data-bs-target="#imageModal" onclick="document.getElementById('modalImage').src = this.src">
    {% elif msg.message_type == 'sticker' %}
        <img src="https://stickershop.line-scdn.net/stickershop/v1/sticker/{{ msg.sticker_id }}/android/sticker.png" class="chat-sticker">
    {% elif msg.message_type == 'system' %}
        <div class="bubble-left bg-warning text-dark" style="font-size:0.85em;">{{ msg.text }}</div>
        <img src="https://stickershop.line-scdn.net/stickershop/v1/sticker/{{ msg.sticker_id }}/android/sticker.png" class="chat-sticker">
    {% endif %}
    <div class="msg-meta">{{ msg.timestamp.strftime('%Y-%m-%d %H:%M') }}</div>
</div>
"""

# ===================== Role-based Access Decorators =====================
def owner_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'owner':
            flash("This function is for the Owner only.", "danger")
            return redirect(url_for('main.manage_users'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['admin', 'owner']:
            flash("Admins or Owner only.", "danger")
            return redirect(url_for('main.chat_all'))
        return f(*args, **kwargs)
    return decorated_function

# ===================== Authentication & Profile =====================
@bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.chat_all"))
    return redirect(url_for("main.login"))

@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.chat_all'))
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash("Login successful", "success")
            return redirect(url_for("main.chat_all"))
        else:
            flash("Invalid username or password", "danger")
    return render_template("login.html")

@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out", "info")
    return redirect(url_for("main.login"))

@bp.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        if not current_user.check_password(current_password):
            flash("Current password is incorrect.", "danger")
        elif new_password != confirm_password:
            flash("New passwords do not match.", "danger")
        else:
            current_user.set_password(new_password)
            db.session.commit()
            flash("Your password has been updated successfully.", "success")
            return redirect(url_for("main.chat_all"))

    return render_template("change_password.html")

# ===================== Manage Users =====================
@bp.route("/manage_users", methods=["GET", "POST"])
@login_required
@admin_required
def manage_users():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]
        email = request.form.get("email")

        if current_user.role == 'admin' and role == 'admin':
            flash("Admins can only create Staff users.", "danger")
            return redirect(url_for('main.manage_users'))

        if User.query.filter_by(username=username).first():
            flash("Username already exists", "warning")
        else:
            user = User(username=username, role=role, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("User added successfully", "success")
        return redirect(url_for("main.manage_users"))

    if current_user.role == 'owner':
        users = User.query.filter(User.role.in_(['admin', 'staff'])).order_by(User.id).all()
    else:
        users = User.query.filter(User.role == 'staff').order_by(User.id).all()
    return render_template("manage_users.html", users=users)

@bp.route("/delete_user/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):
    user_to_delete = User.query.get_or_404(user_id)
    if user_to_delete.id == current_user.id:
        flash("You cannot delete yourself.", "danger")
        return redirect(url_for('main.manage_users'))
    if user_to_delete.role == 'owner':
        flash("The Owner account cannot be deleted.", "danger")
        return redirect(url_for('main.manage_users'))
    if current_user.role == 'admin' and user_to_delete.role == 'admin':
        flash("Admins cannot delete other Admins.", "danger")
        return redirect(url_for('main.manage_users'))

    db.session.delete(user_to_delete)
    db.session.commit()
    flash(f"User '{user_to_delete.username}' has been deleted.", "success")
    return redirect(url_for("main.manage_users"))

@bp.route("/reset_password/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def reset_password_for_user(user_id):
    user_to_update = User.query.get_or_404(user_id)
    new_password = request.form.get("new_password")

    if current_user.role == 'admin' and user_to_update.role != 'staff':
        flash("Admins can only reset passwords for Staff members.", "danger")
        return redirect(url_for('main.manage_users'))

    if not new_password or len(new_password) < 4:
        flash("New password must be at least 4 characters long.", "warning")
        return redirect(url_for('main.manage_users'))

    user_to_update.set_password(new_password)
    db.session.commit()
    flash(f"Password for '{user_to_update.username}' has been reset.", "success")
    return redirect(url_for("main.manage_users"))

@bp.route("/edit_user_role/<int:user_id>", methods=["POST"])
@login_required
@owner_required
def edit_user_role(user_id):
    user_to_edit = User.query.get_or_404(user_id)
    new_role = request.form.get("role")
    if new_role not in ['admin', 'staff']:
        flash("Invalid role selected.", "danger")
        return redirect(url_for('main.manage_users'))
    if user_to_edit.role == 'owner':
        flash("The Owner's role cannot be changed.", "danger")
        return redirect(url_for('main.manage_users'))
    user_to_edit.role = new_role
    db.session.commit()
    flash(f"Role for '{user_to_edit.username}' updated to '{new_role}'.", "success")
    return redirect(url_for("main.manage_users"))

@bp.route("/manage_line_accounts", methods=["GET", "POST"])
@login_required
@admin_required
def manage_line_accounts():
    if request.method == "POST":
        name = request.form["name"]
        channel_id = request.form["channel_id"]
        channel_secret = request.form["channel_secret"]
        channel_access_token = request.form["channel_access_token"]
        acc = LineAccount(name=name, channel_id=channel_id, channel_secret=channel_secret, channel_access_token=channel_access_token)
        db.session.add(acc)
        db.session.commit()
        flash("Line account added successfully", "success")
        return redirect(url_for("main.manage_line_accounts"))
    line_accounts = LineAccount.query.all()
    base_url = current_app.config.get("BASE_URL", "http://127.0.0.1:5000")
    return render_template("manage_line_accounts.html", line_accounts=line_accounts, base_url=base_url)

@bp.route("/delete_line_account/<int:acc_id>", methods=["POST"])
@login_required
@admin_required
def delete_line_account(acc_id):
    acc = LineAccount.query.get_or_404(acc_id)
    db.session.delete(acc)
    db.session.commit()
    flash("Line account deleted", "info")
    return redirect(url_for("main.manage_line_accounts"))

# ===================== Manage Groups =====================
@bp.route("/manage_groups", methods=["GET", "POST"])
@login_required
@admin_required
def manage_groups():
    if request.method == "POST":
        name = request.form.get("group_name")
        if name:
            group = Group(name=name)
            db.session.add(group)
            db.session.commit()
            flash("Group added", "success")
        return redirect(url_for("main.manage_groups"))
    groups = Group.query.all()
    return render_template("manage_groups.html", groups=groups)

@bp.route("/delete_group/<int:group_id>", methods=["POST"])
@login_required
@admin_required
def delete_group(group_id):
    group = Group.query.get_or_404(group_id)
    db.session.delete(group)
    db.session.commit()
    flash("Group deleted", "info")
    return redirect(url_for("main.manage_groups"))

# ===================== Manage Quick Replies =====================
@bp.route("/manage_quick_replies", methods=["GET", "POST"])
@login_required
@admin_required
def manage_quick_replies():
    scope_id = request.args.get('scope', 'global')
    if request.method == "POST":
        name = request.form.get("name")
        text = request.form.get("text")
        if not name or not text:
            flash("Name and Text are required.", "warning")
        else:
            line_account_id = None if scope_id == 'global' else int(scope_id)
            new_qr = QuickReply(name=name, text=text, line_account_id=line_account_id)
            db.session.add(new_qr)
            db.session.commit()
            flash("Quick Reply added successfully.", "success")
        return redirect(url_for('main.manage_quick_replies', scope=scope_id))
    line_accounts = LineAccount.query.order_by(LineAccount.name).all()
    selected_scope_name = "Global"
    if scope_id == 'global':
        quick_replies = QuickReply.query.filter_by(line_account_id=None).order_by(QuickReply.name).all()
    else:
        selected_oa = LineAccount.query.get(scope_id)
        if selected_oa:
            quick_replies = QuickReply.query.filter_by(line_account_id=int(scope_id)).order_by(QuickReply.name).all()
            selected_scope_name = selected_oa.name
        else:
            flash("Invalid LINE OA selected.", "danger")
            return redirect(url_for('main.manage_quick_replies'))
    return render_template("manage_quick_replies.html", line_accounts=line_accounts, quick_replies=quick_replies, selected_scope_id=scope_id, selected_scope_name=selected_scope_name)

@bp.route("/edit_quick_reply/<int:qr_id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_quick_reply(qr_id):
    qr = QuickReply.query.get_or_404(qr_id)
    if request.method == "POST":
        qr.name = request.form.get("name")
        qr.text = request.form.get("text")
        db.session.commit()
        flash("Quick Reply updated successfully.", "success")
        scope = qr.line_account_id or 'global'
        return redirect(url_for('main.manage_quick_replies', scope=scope))
    return render_template("edit_quick_reply.html", qr=qr)

@bp.route("/delete_quick_reply/<int:qr_id>", methods=["POST"])
@login_required
@admin_required
def delete_quick_reply(qr_id):
    qr = QuickReply.query.get_or_404(qr_id)
    scope_to_redirect = qr.line_account_id or 'global'
    db.session.delete(qr)
    db.session.commit()
    flash("Quick reply deleted.", "info")
    return redirect(url_for('main.manage_quick_replies', scope=scope_to_redirect))

@bp.route("/api/quick_replies")
@login_required
def api_quick_replies():
    query_str = request.args.get('q', '')
    line_account_id_str = request.args.get('line_account_id')
    if not query_str: return jsonify([])
    base_query = QuickReply.query.filter(QuickReply.name.contains(query_str))
    if line_account_id_str:
        final_query = base_query.filter(or_(QuickReply.line_account_id.is_(None), QuickReply.line_account_id == int(line_account_id_str)))
    else:
        final_query = base_query.filter(QuickReply.line_account_id.is_(None))
    all_replies = final_query.all()
    results = [{'id': qr.id, 'name': qr.name, 'text': qr.text} for qr in all_replies]
    return jsonify(results)

# ===================== Chat =====================
@bp.route("/chat_all", methods=["GET"])
@bp.route("/chat_all/<int:user_id>", methods=["GET", "POST"])
@login_required
def chat_all(user_id=None):
    selected_user = User.query.get(user_id) if user_id else None

    # Step 1: Handle POST request first (sending a message)
    if request.method == "POST" and selected_user:
        text = request.form.get("message", "").strip()
        line_account_to_use = LineAccount.query.first()
        if not line_account_to_use:
            flash("No configured LINE Account to send message from.", "danger")
            return redirect(url_for("main.chat_all", user_id=user_id))
        
        saved_msg = None
        try:
            line_bot_api = LineBotApi(line_account_to_use.channel_access_token)
            image_match = re.search(r'\[\[IMAGE:([^\s]+)\]\]', text)
            sticker_match = re.search(r'\[\[STICKER:(\d+),(\d+)\]\]', text)

            if image_match:
                image_path = image_match.group(1)
                filename = os.path.basename(image_path)
                base_url = current_app.config.get("BASE_URL")
                if base_url and '127.0.0.1' not in base_url and 'localhost' not in base_url:
                    full_image_url = f"{base_url.rstrip('/')}{image_path}"
                    line_bot_api.push_message(selected_user.line_user_id, ImageSendMessage(original_content_url=full_image_url, preview_image_url=full_image_url))
                else:
                    flash("รูปภาพถูกบันทึกในแชทแอดมินแล้ว แต่ไม่ได้ส่งหาลูกค้าใน LINE เนื่องจากไม่ได้ตั้งค่า BASE_URL ให้เป็น Public", "warning")
                saved_msg = Message(text=text, message_type="image", media_url=filename, user_id=current_user.id, recipient_id=selected_user.id, is_read=True, line_account_id=line_account_to_use.id)

            elif sticker_match:
                package_id, sticker_id = sticker_match.groups()
                line_bot_api.push_message(selected_user.line_user_id, StickerSendMessage(package_id=package_id, sticker_id=sticker_id))
                saved_msg = Message(message_type="sticker", package_id=package_id, sticker_id=sticker_id, user_id=current_user.id, recipient_id=selected_user.id, is_read=True, line_account_id=line_account_to_use.id)
                
            elif text:
                line_bot_api.push_message(selected_user.line_user_id, TextSendMessage(text=text))
                saved_msg = Message(text=text, message_type="text", user_id=current_user.id, recipient_id=selected_user.id, is_read=True, line_account_id=line_account_to_use.id)
            
            if saved_msg:
                db.session.add(saved_msg)
                db.session.commit()
                all_staff = User.query.filter(User.role.in_(['admin', 'staff', 'owner'])).all()
                for staff_member in all_staff:
                    unread_count = Message.query.filter_by(user_id=selected_user.id, recipient_id=staff_member.id, is_read=False).count()
                    user_data = {'user_info': selected_user, 'last_message': saved_msg, 'unread_count': unread_count}
                    user_list_item_html = render_template_string(USER_LIST_ITEM_HTML, data=user_data)
                    message_bubble_html = render_template_string(MESSAGE_BUBBLE_HTML, msg=saved_msg, current_user=current_user)
                    socketio.emit('update_chat', {'user_id': selected_user.id, 'recipient_id': staff_member.id, 'user_list_item_html': user_list_item_html, 'message_bubble_html': message_bubble_html})
        except Exception as e:
            flash(f"Failed to send message: {str(e)}", "danger")
        return redirect(url_for("main.chat_all", user_id=user_id))

    # Step 2: Mark messages as read if a user is selected
    if selected_user:
        Message.query.filter_by(user_id=selected_user.id, recipient_id=current_user.id, is_read=False).update({'is_read': True})
        db.session.commit()

    # Step 3: Fetch the list of all customer users ('guest' role)
    guest_users = User.query.filter_by(role='guest').all()

    # Step 4: Prepare data for the template
    users_data = []
    for user in guest_users:
        last_message = Message.query.filter(
            or_(Message.user_id == user.id, Message.recipient_id == user.id)
        ).order_by(Message.timestamp.desc()).first()
        
        unread_count = Message.query.filter_by(user_id=user.id, recipient_id=current_user.id, is_read=False).count()
        
        users_data.append({
            'user_info': user, 
            'last_message': last_message, 
            'unread_count': unread_count
        })

    users_data.sort(key=lambda x: x['last_message'].timestamp if x['last_message'] else datetime.datetime.min, reverse=True)

    # Step 5: Get messages for the selected chat window
    messages = []
    line_account_context_id = None
    if selected_user:
        messages = Message.query.filter(
            or_(
                and_(Message.user_id == selected_user.id, Message.recipient_id == current_user.id),
                and_(Message.user_id == current_user.id, Message.recipient_id == selected_user.id)
            )
        ).order_by(Message.timestamp.asc()).all()
        last_customer_message = Message.query.filter_by(user_id=selected_user.id).order_by(Message.timestamp.desc()).first()
        if last_customer_message:
            line_account_context_id = last_customer_message.line_account_id

    # Step 6: Render the final template
    return render_template(
        "chat.html", 
        users_data=users_data, 
        selected_user=selected_user, 
        messages=messages, 
        line_account_context_id=line_account_context_id
    )

@bp.route("/upload_image", methods=["POST"])
@login_required
def upload_image():
    if 'image' not in request.files: 
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['image']
    if file.filename == '': 
        return jsonify({'error': 'No selected file'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        filename = f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

        os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)

        try:
            file.save(filepath)
        except Exception as e:
            return jsonify({'error': f'Failed to save file: {str(e)}'}), 500
        image_path = url_for('static', filename=f'uploads/{filename}')
        return jsonify({'success': True, 'image_url': image_path})

# ===================== Webhook =====================
@bp.route("/webhook/<int:line_account_id>", methods=["POST"])
def webhook(line_account_id):
    acc = LineAccount.query.get_or_404(line_account_id)
    handler = WebhookHandler(acc.channel_secret)
    def process_and_save_message(event, msg_type, **kwargs):
        line_bot_api = LineBotApi(acc.channel_access_token)
        profile = line_bot_api.get_profile(event.source.user_id)
        user = get_or_create_line_user(profile, event.source.user_id)
        
        # Check if user creation was successful
        if not user:
            print(f"ERROR: Could not get or create user for line_user_id: {event.source.user_id}")
            return

        all_staff = User.query.filter(User.role.in_(['admin', 'staff', 'owner'])).all()
        if not all_staff: return

        for staff_member in all_staff:
            msg_data = {'message_type': msg_type, 'user_id': user.id, 'recipient_id': staff_member.id, 'line_account_id': acc.id, 'timestamp': datetime.datetime.utcfromtimestamp(event.timestamp / 1000), 'is_read': False}
            msg_data.update(kwargs)
            msg = Message(**msg_data)
            db.session.add(msg)
        
        # A single commit for all operations in this request (user creation/update and message saving)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"ERROR during webhook db.session.commit(): {e}")
            return
            
        # Refetch the message from the database to ensure it has an ID for the template
        # Note: This is simplified; a better way might be to use session flushing, but this is clear and safe.
        last_message_for_socket = Message.query.filter_by(user_id=user.id).order_by(Message.timestamp.desc()).first()

        for staff_member in all_staff:
            unread_count = Message.query.filter_by(user_id=user.id, recipient_id=staff_member.id, is_read=False).count()
            user_data = {'user_info': user, 'last_message': last_message_for_socket, 'unread_count': unread_count}
            user_list_item_html = render_template_string(USER_LIST_ITEM_HTML, data=user_data)
            message_bubble_html = render_template_string(MESSAGE_BUBBLE_HTML, msg=last_message_for_socket, current_user=current_user)
            socketio.emit('update_chat', {'user_id': user.id, 'recipient_id': staff_member.id, 'user_list_item_html': user_list_item_html, 'message_bubble_html': message_bubble_html})

    @handler.add(MessageEvent, message=TextMessage)
    def handle_text_message(event):
        process_and_save_message(event, 'text', text=event.message.text)
    @handler.add(MessageEvent, message=StickerMessage)
    def handle_sticker_message(event):
        process_and_save_message(event, 'sticker', sticker_id=event.message.sticker_id, package_id=event.message.package_id)
    @handler.add(MessageEvent, message=ImageMessage)
    def handle_image_message(event):
        line_bot_api = LineBotApi(acc.channel_access_token)
        message_content = line_bot_api.get_message_content(event.message.id)
        filename = f"{event.message.id}.jpg"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        with open(filepath, 'wb') as fd:
            for chunk in message_content.iter_content():
                fd.write(chunk)
        process_and_save_message(event, 'image', media_url=filename)

    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return "Invalid signature", 400
    return "OK"

def get_or_create_line_user(profile, line_user_id):
    # This function now only adds users to the session, it does not commit.
    # The commit is handled by the calling function (process_and_save_message).
    user = User.query.filter_by(line_user_id=line_user_id).first()
    
    if user:
        # User exists, check for profile updates
        if user.username != profile.display_name or user.picture_url != profile.picture_url:
            # Check if the new display name is already taken by ANOTHER user
            existing_user = User.query.filter(User.username == profile.display_name, User.id != user.id).first()
            if not existing_user:
                user.username = profile.display_name
            user.picture_url = profile.picture_url
        return user
    else:
        # New user, create a unique username
        new_username = profile.display_name
        if User.query.filter_by(username=new_username).first():
            # Append a short unique identifier to prevent collision
            new_username = f"{new_username}_{line_user_id[-5:]}"

        user = User(
            username=new_username,
            line_user_id=line_user_id,
            picture_url=profile.picture_url,
            role="guest"
        )
        db.session.add(user)
        return user



def add_system_log(user_id, action_text):
    try:
        from datetime import datetime
        system_msg = Message(
            text=action_text,
            message_type="system",
            user_id=current_user.id,
            recipient_id=user_id,
            line_account_id=None,
            is_read=True,
            timestamp=datetime.utcnow()
        )
        db.session.add(system_msg)
        db.session.commit()

        # ===== Realtime update via Socket.IO =====
        from flask import render_template_string
        user = User.query.get(user_id)
        if user:
            user_data = {'user_info': user, 'last_message': system_msg, 'unread_count': 0}
            user_list_item_html = render_template_string(USER_LIST_ITEM_HTML, data=user_data)
            message_bubble_html = render_template_string(MESSAGE_BUBBLE_HTML, msg=system_msg, current_user=current_user)
            all_staff = User.query.filter(User.role.in_(['admin','staff','owner'])).all()
            for staff_member in all_staff:
                socketio.emit('update_chat', {
                    'user_id': user.id,
                    'recipient_id': staff_member.id,
                    'user_list_item_html': user_list_item_html,
                    'message_bubble_html': message_bubble_html
                })
    except Exception as e:
        db.session.rollback()
        print(f"Error saving system log: {e}")

@bp.route("/edit_username/<int:user_id>", methods=["POST"])
@login_required
def edit_username(user_id):
    user = User.query.get_or_404(user_id)
    payload = request.get_json(silent=True) or {}
    new_username = (payload.get("username") or "").strip()
    if not new_username:
        return jsonify({"success": False, "error": "ชื่อห้ามว่าง"}), 400
    if len(new_username) > 100:
        return jsonify({"success": False, "error": "ชื่อยาวเกินไป"}), 400
    try:
        user.username = new_username
        db.session.commit()
        add_system_log(user_id, f"{current_user.username} แก้ไขชื่อเป็น '{new_username}'")
        return jsonify({"success": True, "username": new_username})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/edit_phone/<int:user_id>", methods=["POST"])
@login_required
def edit_phone(user_id):
    user = User.query.get_or_404(user_id)
    payload = request.get_json(silent=True) or {}
    new_phone = (payload.get("phone") or "").strip()
    try:
        user.phone = new_phone
        db.session.commit()
        add_system_log(user_id, f"{current_user.username} แก้ไขเบอร์โทรเป็น '{new_phone}'")
        return jsonify({"success": True, "phone": new_phone})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@bp.route("/edit_note/<int:user_id>", methods=["POST"])
@login_required
def edit_note(user_id):
    user = User.query.get_or_404(user_id)
    payload = request.get_json(silent=True) or {}
    new_note = (payload.get("note") or "").strip()
    try:
        user.note = new_note
        db.session.commit()
        add_system_log(user_id, f"{current_user.username} แก้ไขโน้ต: {new_note}")
        return jsonify({"success": True, "note": new_note})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
