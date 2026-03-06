#!/usr/bin/env python3
"""
gpt_play.py — HTTP API for GPT to play DIV via browser automation.

Usage:
    python gpt_play.py

Endpoints:
    GET  /screenshot          → { "image": "<base64 PNG>" }
    POST /key  {"key": "..."}  → { "ok": true }
    GET  /reset               → presses R then Enter to restart
    GET  /state               → { "url": "...", "title": "..." }

Key names (Playwright / browser key names):
    ArrowUp ArrowDown ArrowLeft ArrowRight
    v  t  x  Space  Tab  KeyR  KeyZ  KeyM  Escape  Enter  F1
"""

import sys, os, base64, io, subprocess, time, threading

# Resolve site-packages for non-PATH installs
_SP = r"C:\Users\alun0\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\site-packages"
if _SP not in sys.path:
    sys.path.insert(0, _SP)

from flask import Flask, jsonify, request
from playwright.sync_api import sync_playwright

WEB_DIR  = r"D:\DIV\WEB"
WEB_PORT = 8080
API_PORT = 5050
BOOT_WAIT = 7  # seconds for Godot to load

app = Flask(__name__)
_page = None   # Playwright page (set after launch)
_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Web server (serves WEB_DIR with COOP/COEP headers)
# ---------------------------------------------------------------------------

def _start_web_server():
    script = f"""
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
class H(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cross-Origin-Opener-Policy","same-origin")
        self.send_header("Cross-Origin-Embedder-Policy","require-corp")
        super().end_headers()
    def log_message(self, *a): pass
os.chdir(r"{WEB_DIR}")
HTTPServer(("localhost", {WEB_PORT}), H).serve_forever()
"""
    subprocess.Popen([sys.executable, "-c", script])
    time.sleep(1)


# ---------------------------------------------------------------------------
# Flask routes
# ---------------------------------------------------------------------------

@app.route("/screenshot")
def screenshot():
    with _lock:
        data = _page.screenshot()
    b64 = base64.b64encode(data).decode()
    return jsonify({"image": b64})


@app.route("/key", methods=["POST"])
def key():
    k = (request.json or {}).get("key", "")
    if not k:
        return jsonify({"error": "missing key"}), 400
    with _lock:
        _page.keyboard.press(k)
    time.sleep(0.15)
    return jsonify({"ok": True, "key": k})


@app.route("/keys", methods=["POST"])
def keys():
    """Send multiple keys in sequence: { "keys": ["ArrowRight", "ArrowRight", "v"] }"""
    ks = (request.json or {}).get("keys", [])
    for k in ks:
        with _lock:
            _page.keyboard.press(k)
        time.sleep(0.15)
    return jsonify({"ok": True, "count": len(ks)})


@app.route("/reset")
def reset():
    with _lock:
        _page.keyboard.press("r")
    time.sleep(0.3)
    return jsonify({"ok": True})


@app.route("/state")
def state():
    return jsonify({"url": _page.url, "title": _page.title()})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    global _page

    print("Starting web server …")
    _start_web_server()

    print("Launching Chromium …")
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = browser.new_context(viewport={"width": 1280, "height": 720})
    _page = ctx.new_page()
    _page.goto(f"http://localhost:{WEB_PORT}/DIV.html", timeout=15000)

    print(f"Waiting {BOOT_WAIT}s for Godot to boot …")
    time.sleep(BOOT_WAIT)
    print("Game ready.")

    print(f"\nAPI running at http://localhost:{API_PORT}")
    print("  GET  /screenshot")
    print("  POST /key       {\"key\": \"ArrowRight\"}")
    print("  POST /keys      {\"keys\": [\"ArrowRight\", \"v\"]}")
    print("  GET  /reset")
    print("  GET  /state\n")

    app.run(host="0.0.0.0", port=API_PORT, threaded=False)


if __name__ == "__main__":
    main()
