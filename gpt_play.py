#!/usr/bin/env python3
"""
HTTP API for GPT to play DIV via browser automation.

All Playwright access is funneled through one worker thread. This avoids the
thread-safety issues that cause intermittent 500s when input and screenshots
race each other.
"""

import base64
import queue
import subprocess
import sys
import threading
import time

_SP = r"C:\Users\alun0\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\site-packages"
if _SP not in sys.path:
    sys.path.insert(0, _SP)

from flask import Flask, Response, jsonify, request
from playwright.sync_api import sync_playwright

WEB_DIR = r"D:\DIV\WEB"
WEB_PORT = 8080
API_PORT = 5050
BOOT_WAIT = 7.0
KEY_SETTLE_SEC = 0.05
KEY_CHAIN_GAP_SEC = 0.04
RESET_SETTLE_SEC = 0.12
TASK_TIMEOUT_SEC = 10.0
READY_TIMEOUT_SEC = 30.0
SCREENSHOT_HZ = 5.0
SCREENSHOT_INTERVAL_SEC = 1.0 / SCREENSHOT_HZ

app = Flask(__name__)
_events = []
_event_id = 0
_event_lock = threading.Lock()
_running = True

_frame_bytes = b""
_frame_b64 = ""
_frame_seq = 0
_frame_ts = 0.0
_frame_lock = threading.Lock()

_task_queue = queue.Queue()
_ready = threading.Event()
_worker_error = None
_input_lock = threading.Lock()
_input_seq = 0
_applied_input_seq = 0


class _Task:
    def __init__(self, fn):
        self.fn = fn
        self.done = threading.Event()
        self.result = None
        self.error = None


def _push_event(kind: str, payload: str) -> None:
    global _event_id
    with _event_lock:
        _event_id += 1
        _events.append(
            {
                "id": _event_id,
                "t": round(time.time(), 3),
                "kind": kind,
                "payload": payload,
            }
        )
        if len(_events) > 1000:
            del _events[:400]


def _snapshot_frame_bytes() -> bytes:
    with _frame_lock:
        return _frame_bytes


def _snapshot_frame_meta() -> tuple[str, int, float]:
    with _frame_lock:
        return _frame_b64, _frame_seq, _frame_ts


def _store_frame_bytes(data: bytes) -> None:
    global _frame_bytes, _frame_b64, _frame_seq, _frame_ts
    with _frame_lock:
        _frame_bytes = data
        _frame_b64 = base64.b64encode(data).decode("ascii")
        _frame_seq += 1
        _frame_ts = time.time()


def _capture_png(page) -> bytes:
    canvas = page.locator("canvas").first
    try:
        return canvas.screenshot(type="png")
    except Exception:
        return page.screenshot(type="png")


def _capture_jpeg(page, quality: int = 60) -> bytes:
    canvas = page.locator("canvas").first
    try:
        return canvas.screenshot(type="jpeg", quality=quality)
    except Exception:
        return page.screenshot(type="jpeg", quality=quality)


def _submit(fn, timeout: float = TASK_TIMEOUT_SEC):
    global _worker_error
    if _worker_error is not None:
        raise RuntimeError(f"browser worker failed: {_worker_error}")
    task = _Task(fn)
    _task_queue.put(task)
    if not task.done.wait(timeout):
        raise TimeoutError("browser task timed out")
    if task.error is not None:
        raise task.error
    return task.result


def _enqueue(fn):
    global _worker_error
    if _worker_error is not None:
        raise RuntimeError(f"browser worker failed: {_worker_error}")
    task = _Task(fn)
    _task_queue.put(task)
    return task


def _next_input_seq() -> int:
    global _input_seq
    with _input_lock:
        _input_seq += 1
        return _input_seq


def _mark_applied_input(seq: int) -> None:
    global _applied_input_seq
    with _input_lock:
        if seq > _applied_input_seq:
            _applied_input_seq = seq


def _input_status() -> tuple[int, int]:
    with _input_lock:
        return _input_seq, _applied_input_seq


def _start_web_server() -> None:
    script = f"""
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
class H(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        super().end_headers()
    def log_message(self, *args): pass
os.chdir(r"{WEB_DIR}")
HTTPServer(("localhost", {WEB_PORT}), H).serve_forever()
"""
    subprocess.Popen([sys.executable, "-c", script])
    time.sleep(1.0)


def _browser_worker() -> None:
    global _worker_error
    page = None
    browser = None
    pw = None
    try:
        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(viewport={"width": 1280, "height": 720})
        page = ctx.new_page()
        page.goto(f"http://localhost:{WEB_PORT}/DIV.html", timeout=15000)
        time.sleep(BOOT_WAIT)
        _store_frame_bytes(_capture_png(page))
        _ready.set()

        while _running:
            try:
                task = _task_queue.get(timeout=SCREENSHOT_INTERVAL_SEC)
            except queue.Empty:
                _store_frame_bytes(_capture_png(page))
                continue

            try:
                task.result = task.fn(page)
            except Exception as exc:
                task.error = exc
            finally:
                task.done.set()
    except Exception as exc:
        _worker_error = exc
        print(f"[gpt_play] browser worker failed: {exc!r}", file=sys.stderr, flush=True)
        _ready.set()
    finally:
        try:
            if browser is not None:
                browser.close()
        except Exception:
            pass
        try:
            if pw is not None:
                pw.stop()
        except Exception:
            pass


def _ensure_ready() -> None:
    if not _ready.wait(READY_TIMEOUT_SEC):
        raise RuntimeError("browser worker did not become ready")
    if _worker_error is not None:
        raise RuntimeError(f"browser worker failed: {_worker_error}")


@app.route("/screenshot")
def screenshot():
    _ensure_ready()
    b64, seq, ts = _snapshot_frame_meta()
    return jsonify({"image": b64, "frame_seq": seq, "frame_ts": ts})


@app.route("/frame.png")
def frame_png():
    _ensure_ready()
    data = _snapshot_frame_bytes()
    resp = Response(data, mimetype="image/png")
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp


@app.route("/frame.jpg")
def frame_jpg():
    _ensure_ready()
    data = _submit(lambda page: _capture_jpeg(page, quality=55), timeout=TASK_TIMEOUT_SEC)
    resp = Response(data, mimetype="image/jpeg")
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp


@app.route("/observe")
def observe():
    _ensure_ready()
    meta = _submit(
        lambda page: {
            "url": page.url,
            "title": page.title(),
            "dom": page.evaluate(
                """() => {
                    const canvas = document.querySelector('canvas');
                    return {
                        has_focus: document.hasFocus(),
                        visibility: document.visibilityState,
                        canvas_width: canvas ? canvas.width : 0,
                        canvas_height: canvas ? canvas.height : 0,
                        observe: window.__div_observe || null
                    };
                }"""
            ),
        }
    )
    _, seq, ts = _snapshot_frame_meta()
    with _event_lock:
        last_event_id = _event_id
    queued_input_seq, applied_input_seq = _input_status()
    dom = meta["dom"]
    observe_payload = dom.pop("observe", None)
    return jsonify(
        {
            "url": meta["url"],
            "title": meta["title"],
            "frame_seq": seq,
            "frame_ts": ts,
            "last_event_id": last_event_id,
            "queued_input_seq": queued_input_seq,
            "applied_input_seq": applied_input_seq,
            **dom,
            "observe": observe_payload,
        }
    )


@app.route("/key", methods=["POST"])
def key():
    _ensure_ready()
    k = (request.json or {}).get("key", "")
    if not k:
        return jsonify({"error": "missing key"}), 400
    input_seq = _next_input_seq()

    def _do(page):
        page.keyboard.press(k)
        _mark_applied_input(input_seq)
        return True

    _enqueue(_do)
    _push_event("key", k)
    return jsonify({"ok": True, "key": k, "input_seq": input_seq})


@app.route("/keys", methods=["POST"])
def keys():
    _ensure_ready()
    ks = (request.json or {}).get("keys", [])
    input_seq = _next_input_seq()

    def _do(page):
        for k in ks:
            page.keyboard.press(k)
            time.sleep(KEY_CHAIN_GAP_SEC)
        _mark_applied_input(input_seq)
        return True

    _enqueue(_do)
    for k in ks:
        _push_event("key", k)
    return jsonify({"ok": True, "count": len(ks), "input_seq": input_seq})


@app.route("/reset")
def reset():
    _ensure_ready()
    input_seq = _next_input_seq()

    def _do(page):
        page.keyboard.press("r")
        _mark_applied_input(input_seq)
        return True

    _enqueue(_do)
    _push_event("key", "r")
    return jsonify({"ok": True, "input_seq": input_seq})


@app.route("/state")
def state():
    _ensure_ready()
    meta = _submit(lambda page: {"url": page.url, "title": page.title()})
    return jsonify(meta)


@app.route("/events")
def events():
    since_id = request.args.get("since_id", default=0, type=int)
    if since_id < 0:
        since_id = 0
    with _event_lock:
        out = [e for e in _events if int(e["id"]) > since_id]
        last_id = _event_id
    return jsonify({"events": out, "last_id": last_id})


@app.route("/live")
def live():
    html_text = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>DIV Live Monitor</title>
  <style>
    body {{ margin: 0; background: #0b0d18; color: #d6d8df; font: 14px/1.4 Consolas, monospace; }}
    .wrap {{ display: grid; grid-template-columns: 1fr 340px; gap: 12px; padding: 12px; }}
    .panel {{ background: #121726; border: 1px solid #2a334d; border-radius: 8px; overflow: hidden; }}
    .head {{ padding: 8px 10px; border-bottom: 1px solid #2a334d; color: #8fb3ff; }}
    #shot {{ width: 100%; height: auto; display: block; image-rendering: auto; }}
    #log {{ height: calc(100vh - 76px); overflow: auto; padding: 8px 10px; white-space: pre-wrap; }}
    .row {{ padding: 2px 0; border-bottom: 1px dotted rgba(255,255,255,0.08); }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="panel">
      <div class="head">Live Frame (cached PNG)</div>
      <img id="shot" src="/frame.png" alt="live frame">
    </div>
    <div class="panel">
      <div class="head">Input Log</div>
      <div id="log"></div>
    </div>
  </div>
  <script>
    const shot = document.getElementById('shot');
    const log = document.getElementById('log');
    let lastId = 0;
    const frameMs = 120;
    function tickFrame() {{
      shot.src = '/frame.png?ts=' + Date.now();
    }}
    async function tickEvents() {{
      try {{
        const r = await fetch('/events?since_id=' + lastId, {{ cache: 'no-store' }});
        const j = await r.json();
        if (Array.isArray(j.events)) {{
          for (const e of j.events) {{
            const el = document.createElement('div');
            el.className = 'row';
            const d = new Date(e.t * 1000);
            const hh = String(d.getHours()).padStart(2, '0');
            const mm = String(d.getMinutes()).padStart(2, '0');
            const ss = String(d.getSeconds()).padStart(2, '0');
            const ms = String(d.getMilliseconds()).padStart(3, '0');
            el.textContent = `[${{hh}}:${{mm}}:${{ss}}.${{ms}}] ${{e.kind}}: ${{e.payload}}`;
            log.appendChild(el);
            log.scrollTop = log.scrollHeight;
          }}
        }}
        lastId = Math.max(lastId, j.last_id || lastId);
      }} catch (_) {{}}
    }}
    tickFrame();
    setInterval(tickFrame, frameMs);
    setInterval(tickEvents, 120);
  </script>
</body>
</html>"""
    return Response(html_text, mimetype="text/html; charset=utf-8")


def main() -> None:
    global _running
    print("Starting web server...")
    _start_web_server()
    print("Launching browser worker...")
    threading.Thread(target=_browser_worker, name="browser-worker", daemon=True).start()
    _ensure_ready()

    print(f"\nAPI running at http://localhost:{API_PORT}")
    print("  GET  /live")
    print("  GET  /screenshot")
    print("  GET  /frame.png")
    print("  GET  /frame.jpg")
    print("  GET  /observe")
    print(f"  screenshot cache: {SCREENSHOT_HZ:.0f} FPS")
    print('  POST /key       {"key": "ArrowRight"}')
    print('  POST /keys      {"keys": ["ArrowRight", "v"]}')
    print("  GET  /reset")
    print("  GET  /state\n")

    try:
        app.run(host="0.0.0.0", port=API_PORT, threaded=True)
    finally:
        _running = False


if __name__ == "__main__":
    main()
