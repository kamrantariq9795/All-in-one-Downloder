import os
import sys
import subprocess
import requests
from flask import Flask, render_template, request, jsonify, send_file, Response
from flask_cors import CORS
import downloader

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

# Ensure downloads directory exists
os.makedirs(downloader.DOWNLOAD_DIR, exist_ok=True)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/info", methods=["POST"])
def get_info():
    data = request.get_json() or {}
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"success": False, "error": "Please provide a valid video URL."}), 400

    info = downloader.fetch_video_info(url)
    return jsonify(info)


@app.route("/api/thumbnail", methods=["GET"])
def proxy_thumbnail():
    """Proxy video thumbnail image to bypass referrer/hotlink restrictions."""
    img_url = request.args.get("url", "").strip()
    if not img_url:
        return "No URL provided", 400
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        }
        if "ytimg" in img_url or "youtube" in img_url:
            headers["Referer"] = "https://www.youtube.com/"
        elif "tiktok" in img_url:
            headers["Referer"] = "https://www.tiktok.com/"
        elif "instagram" in img_url or "cdninstagram" in img_url:
            headers["Referer"] = "https://www.instagram.com/"

        r = requests.get(img_url, headers=headers, timeout=10)
        content_type = r.headers.get("Content-Type", "image/jpeg")
        return (r.content, 200, {"Content-Type": content_type, "Cache-Control": "public, max-age=86400"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/download", methods=["POST"])
def start_download():
    data = request.get_json() or {}
    url = data.get("url", "").strip()
    quality = data.get("quality", "best")
    format_type = data.get("format", "video")  # 'video' or 'audio'
    custom_title = data.get("title", "")

    if not url:
        return jsonify({"success": False, "error": "URL is required"}), 400

    is_audio = (format_type == "audio" or quality == "mp3")
    task_id = downloader.start_download_task(
        url=url,
        quality=quality,
        is_audio=is_audio,
        custom_title=custom_title
    )
    return jsonify({"success": True, "task_id": task_id})


@app.route("/api/progress/<task_id>", methods=["GET"])
def check_progress(task_id):
    task = downloader.get_task_status(task_id)
    if not task:
        return jsonify({"success": False, "error": "Task not found"}), 404
    return jsonify({"success": True, "task": task})


@app.route("/api/file/<filename>", methods=["GET"])
def download_file(filename):
    safe_name = os.path.basename(filename)
    file_path = os.path.join(downloader.DOWNLOAD_DIR, safe_name)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    as_attachment = request.args.get("attachment", "true").lower() == "true"
    return send_file(file_path, as_attachment=as_attachment, download_name=safe_name)


@app.route("/api/history", methods=["GET"])
def get_history():
    files = downloader.get_download_history()
    return jsonify({"success": True, "files": files})


@app.route("/api/delete", methods=["POST"])
def delete_file():
    data = request.get_json() or {}
    filename = os.path.basename(data.get("filename", ""))
    if not filename:
        return jsonify({"success": False, "error": "Filename missing"}), 400

    file_path = os.path.join(downloader.DOWNLOAD_DIR, filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            return jsonify({"success": True, "message": "File deleted"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    return jsonify({"success": False, "error": "File not found"}), 404


@app.route("/api/open-folder", methods=["POST"])
def open_folder():
    """Open downloads directory in Windows File Explorer."""
    try:
        folder = os.path.abspath(downloader.DOWNLOAD_DIR)
        if sys.platform == "win32":
            os.startfile(folder)
        else:
            subprocess.Popen(["xdg-open", folder])
        return jsonify({"success": True, "path": folder})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print(" [*] ALL-IN-ONE VIDEO DOWNLOADER (NO WATERMARK) IS RUNNING!")
    print(" [*] Open on PC: http://localhost:5000")
    print(" [*] Open on Mobile: http://192.168.0.101:5000")
    print(" [*] Downloads folder: " + os.path.abspath(downloader.DOWNLOAD_DIR))
    print("=" * 60 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
