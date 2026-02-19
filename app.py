import os
import base64
import datetime
from flask import Flask, render_template, send_from_directory, request
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1000 * 1000

# تنظیم مهم برای CORS - اجازه اتصال از هر دستگاهی
socketio = SocketIO(app, 
                   cors_allowed_origins="*",
                   max_http_buffer_size=50 * 1000 * 1000,
                   logger=True,  # برای دیباگ
                   engineio_logger=True)  # برای دیباگ

# ساختار داده‌ها
users = {}  # {socket_id: {'username': name, 'avatar': avatar, 'sid': socket_id}}
private_messages = {}  # {'user1_user2': [messages]}
rooms = {}  # {'user1_user2': room_name}

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@socketio.on('connect')
def handle_connect():
    print(f'🟢 دستگاه جدید متصل شد: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    print(f'🔴 دستگاه قطع شد: {request.sid}')
    if request.sid in users:
        user_data = users[request.sid]
        del users[request.sid]
        
        # به همه بگو این کاربر آفلاین شده
        online_users = [{'username': u['username'], 'sid': u['sid'], 'avatar': u.get('avatar', '')} 
                       for u in users.values()]
        emit('online_users', online_users, broadcast=True)
        emit('user_left', {'username': user_data['username'], 'sid': request.sid}, broadcast=True)

@socketio.on('set_username')
def handle_set_username(data):
    username = data['username']
    avatar = data.get('avatar', '')
    
    # ذخیره اطلاعات کاربر
    users[request.sid] = {
        'username': username,
        'avatar': avatar,
        'sid': request.sid
    }
    
    print(f'👤 کاربر ثبت نام کرد: {username} با آیدی {request.sid}')
    
    # به همه لیست به‌روز شده رو بفرست
    online_users = [{'username': u['username'], 'sid': u['sid'], 'avatar': u.get('avatar', '')} 
                   for u in users.values()]
    
    emit('online_users', online_users, broadcast=True)
    emit('user_joined', {'username': username, 'sid': request.sid}, broadcast=True)
    
    # به خود کاربر بگو ثبت نام کامل شد
    emit('registration_success', {'sid': request.sid, 'users': online_users}, to=request.sid)

@socketio.on('send_private_message')
def handle_private_message(data):
    sender = users.get(request.sid)
    if not sender:
        print(f'❌ فرستنده پیدا نشد: {request.sid}')
        return
    
    receiver_sid = data['receiver_sid']
    receiver = users.get(receiver_sid)
    
    if not receiver:
        print(f'❌ گیرنده پیدا نشد: {receiver_sid}')
        emit('error_message', {'text': 'کاربر آفلاین است'}, to=request.sid)
        return
    
    # ایجاد آیدی یکتا برای چت
    chat_id = '_'.join(sorted([request.sid, receiver_sid]))
    
    message_data = {
        'username': sender['username'],
        'message': data['message'],
        'time': data['time'],
        'type': 'text',
        'sender_sid': request.sid,
        'receiver_sid': receiver_sid,
        'chat_id': chat_id
    }
    
    #  ذخیره پیام ها 
    if chat_id not in private_messages:
        private_messages[chat_id] = []
    private_messages[chat_id].append(message_data)
    
    print(f'📨 پیام از {sender["username"]} به {receiver["username"]}: {data["message"]}')
    
    # ارسال به گیرنده (اگر آنلاین باشه)
    emit('new_private_message', message_data, to=receiver_sid)
    # ارسال به فرستنده (برای نمایش)
    emit('new_private_message', message_data, to=request.sid)

@socketio.on('send_private_file')
def handle_private_file(data):
    sender = users.get(request.sid)
    if not sender:
        return
    
    receiver_sid = data['receiver_sid']
    receiver = users.get(receiver_sid)
    
    if not receiver:
        emit('error_message', {'text': 'کاربر آفلاین است'}, to=request.sid)
        return
    
    try:
        chat_id = '_'.join(sorted([request.sid, receiver_sid]))
        file_name = data['fileName']
        file_data = data['fileData']
        file_type = data['fileType']
        file_size = data['fileSize']
        
        # حذف metadata از base64
        if ',' in file_data:
            file_data = file_data.split(',')[1]
        
        # دیکد کردن و ذخیره
        file_binary = base64.b64decode(file_data)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = f"{timestamp}_{file_name}"
        file_path = os.path.join(UPLOAD_FOLDER, safe_filename)
        
        with open(file_path, 'wb') as f:
            f.write(file_binary)
        
        # آدرس فایل
        file_url = f"/uploads/{safe_filename}"
        
        file_message = {
            'username': sender['username'],
            'fileName': file_name,
            'fileSize': file_size,
            'fileType': file_type,
            'fileUrl': file_url,
            'time': data['time'],
            'type': 'file',
            'sender_sid': request.sid,
            'receiver_sid': receiver_sid,
            'chat_id': chat_id
        }
        
        # ذخیره پیام
        if chat_id not in private_messages:
            private_messages[chat_id] = []
        private_messages[chat_id].append(file_message)
        
        print(f'📎 فایل از {sender["username"]} به {receiver["username"]}: {file_name}')
        
        # ارسال به گیرنده و فرستنده
        emit('new_private_file', file_message, to=receiver_sid)
        emit('new_private_file', file_message, to=request.sid)
        
    except Exception as e:
        print(f"❌ خطا در آپلود فایل: {str(e)}")
        emit('upload_error', {'error': str(e)}, to=request.sid)

@socketio.on('get_chat_history')
def handle_chat_history(data):
    chat_id = data['chat_id']
    print(f'📜 درخواست تاریخچه برای: {chat_id}')
    
    if chat_id in private_messages:
        emit('chat_history', {
            'chat_id': chat_id, 
            'messages': private_messages[chat_id]
        }, to=request.sid)
    else:
        emit('chat_history', {'chat_id': chat_id, 'messages': []}, to=request.sid)

@socketio.on('get_online_users')
def handle_get_online_users():
    """دریافت لیست کاربران آنلاین"""
    online_users = [{'username': u['username'], 'sid': u['sid'], 'avatar': u.get('avatar', '')} 
                   for u in users.values()]
    emit('online_users', online_users, to=request.sid)

if __name__ == '__main__':
    # اجرا روی همه آی‌پی‌ها برای اتصال از شبکه محلی
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)