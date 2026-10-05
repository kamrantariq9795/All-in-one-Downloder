import os
import sys
import threading
import socket
import webview
from app import app
import downloader

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def find_free_port(start_port=5000):
    """Find an available port starting from start_port."""
    port = start_port
    while port < 65535:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
        port += 1
    return 5000


def run_flask(port):
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True, use_reloader=False)


def main():
    port = find_free_port(5000)
    server_thread = threading.Thread(target=run_flask, args=(port,), daemon=True)
    server_thread.start()

    window_url = f"http://127.0.0.1:{port}"
    window = webview.create_window(
        title="OmniDownloader PRO - 4K & No Watermark",
        url=window_url,
        width=1120,
        height=820,
        min_size=(480, 680),
        background_color="#070913"
    )

    webview.start(debug=False)


if __name__ == "__main__":
    main()

