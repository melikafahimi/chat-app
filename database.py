# database.py
import sqlite3
import datetime
import os

DB_NAME = 'chat_database.db'

def init_database():
    """ایجاد جداول دیتابیس اگه وجود نداشته باشن"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # جدول کاربران
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            socket_id TEXT UNIQUE,
            avatar TEXT,
            last_seen TIMESTAMP
        )
    ''')
    
    # جدول پیام‌های خصوصی
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS private_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            sender_username TEXT NOT NULL,
            message TEXT,
            file_name TEXT,
            file_size INTEGER,
            file_type TEXT,
            file_url TEXT,
            time TEXT NOT NULL,
            type TEXT NOT NULL,
            sender_sid TEXT,
            receiver_sid TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ دیتابیس راه‌اندازی شد")

def save_message(chat_id, message_data):
    """ذخیره پیام در دیتابیس"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    if message_data['type'] == 'text':
        cursor.execute('''
            INSERT INTO private_messages 
            (chat_id, sender_username, message, time, type, sender_sid, receiver_sid)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            chat_id,
            message_data['username'],
            message_data['message'],
            message_data['time'],
            'text',
            message_data.get('sender_sid', ''),
            message_data.get('receiver_sid', '')
        ))
    else:  # فایل
        cursor.execute('''
            INSERT INTO private_messages 
            (chat_id, sender_username, file_name, file_size, file_type, file_url, time, type, sender_sid, receiver_sid)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            chat_id,
            message_data['username'],
            message_data['fileName'],
            message_data['fileSize'],
            message_data['fileType'],
            message_data['fileUrl'],
            message_data['time'],
            'file',
            message_data.get('sender_sid', ''),
            message_data.get('receiver_sid', '')
        ))
    
    conn.commit()
    conn.close()

def get_chat_history(chat_id, limit=100):
    """گرفتن تاریخچه چت با آیدی مشخص"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM private_messages 
        WHERE chat_id = ? 
        ORDER BY created_at ASC
        LIMIT ?
    ''', (chat_id, limit))
    
    rows = cursor.fetchall()
    conn.close()
    
    messages = []
    for row in rows:
        if row[6] == 'text':  # type
            messages.append({
                'username': row[2],
                'message': row[3],
                'time': row[7],
                'type': 'text',
                'sender_sid': row[9],
                'receiver_sid': row[10]
            })
        else:
            messages.append({
                'username': row[2],
                'fileName': row[4],
                'fileSize': row[5],
                'fileType': row[6],
                'fileUrl': row[7],
                'time': row[8],
                'type': 'file',
                'sender_sid': row[9],
                'receiver_sid': row[10]
            })
    
    return messages

def update_user_socket(username, socket_id, avatar=''):
    """به‌روزرسانی یا اضافه کردن کاربر"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO users (username, socket_id, avatar, last_seen)
        VALUES (?, ?, ?, ?)
    ''', (username, socket_id, avatar, datetime.datetime.now()))
    
    conn.commit()
    conn.close()

def remove_user(socket_id):
    """حذف کاربر هنگام قطع اتصال"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM users WHERE socket_id = ?', (socket_id,))
    
    conn.commit()
    conn.close()

def get_all_users():
    """گرفتن لیست همه کاربران آنلاین"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('SELECT username, socket_id, avatar FROM users')
    rows = cursor.fetchall()
    conn.close()
    
    users = []
    for row in rows:
        users.append({
            'username': row[0],
            'sid': row[1],
            'avatar': row[2] or ''
        })
    
    return users

# اجرای راه‌اندازی دیتابیس وقتی فایل اجرا میشه
init_database()