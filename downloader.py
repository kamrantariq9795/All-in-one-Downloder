import os
import sys
import re
import time
import uuid
import shutil
import logging
import threading
import requests
import yt_dlp

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Base directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Find FFmpeg binary
FFMPEG_PATH = None
try:
    import imageio_ffmpeg
    FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
    logger.info(f"Using imageio-ffmpeg at: {FFMPEG_PATH}")
except Exception as e:
    logger.warning(f"imageio_ffmpeg not found: {e}")
    FFMPEG_PATH = shutil.which("ffmpeg")
    if FFMPEG_PATH:
        logger.info(f"Using system ffmpeg at: {FFMPEG_PATH}")
    else:
        logger.warning("No ffmpeg detected. High-res video merging might be limited.")

# Global state for tracking download tasks
tasks = {}
tasks_lock = threading.Lock()


def detect_platform(url: str) -> str:
    """Detect social media platform from link."""
    url_lower = url.lower()
    if "tiktok.com" in url_lower:
        return "tiktok"
    elif "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    elif "instagram.com" in url_lower:
        return "instagram"
    elif "facebook.com" in url_lower or "fb.watch" in url_lower or "fb.com" in url_lower:
        return "facebook"
    elif "twitter.com" in url_lower or "x.com" in url_lower:
        return "twitter"
    elif "pinterest.com" in url_lower or "pin.it" in url_lower:
        return "pinterest"
    elif "reddit.com" in url_lower or "v.redd.it" in url_lower:
        return "reddit"
    elif "threads.net" in url_lower:
        return "threads"
    elif "snapchat.com" in url_lower:
        return "snapchat"
    elif "vimeo.com" in url_lower:
        return "vimeo"
    else:
        return "generic"


def get_base_ydl_opts():
    """Common yt-dlp options with anti-bot evasion headers."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "ignoreerrors": False,
        "logtostderr": False,
        "noplaylist": True,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    }
    if FFMPEG_PATH:
        opts["ffmpeg_location"] = FFMPEG_PATH
    return opts


def get_tiktok_info_tikwm(url: str):
    """Fetch TikTok video without watermark using TikWM API."""
    try:
        api_url = "https://www.tikwm.com/api/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        resp = requests.post(api_url, data={"url": url, "count": 12, "cursor": 0, "web": 1, "hd": 1}, headers=headers, timeout=10)
        data = resp.json()
        if data.get("code") == 0 and "data" in data:
            d = data["data"]
            # hdplay or play is clean without watermark
            no_wm_url = d.get("hdplay") or d.get("play")
            if no_wm_url and not no_wm_url.startswith("http"):
                no_wm_url = "https://www.tikwm.com" + no_wm_url

            audio_url = d.get("music")
            if audio_url and not audio_url.startswith("http"):
                audio_url = "https://www.tikwm.com" + audio_url

            cover = d.get("cover")
            if cover and not cover.startswith("http"):
                cover = "https://www.tikwm.com" + cover

            return {
                "success": True,
                "platform": "tiktok",
                "title": d.get("title") or "TikTok Video Without Watermark",
                "uploader": d.get("author", {}).get("nickname") or d.get("author", {}).get("unique_id") or "TikTok Creator",
                "thumbnail": cover or d.get("origin_cover"),
                "duration": d.get("duration", 0),
                "url": url,
                "no_wm_download_url": no_wm_url,
                "audio_url": audio_url,
                "has_no_watermark": True,
                "quality_options": [
                    {"label": "HD (No Watermark)", "value": "best", "type": "video", "ext": "mp4"},
                    {"label": "Audio Only (MP3)", "value": "mp3", "type": "audio", "ext": "mp3"}
                ]
            }
    except Exception as e:
        logger.warning(f"TikWM fetch failed: {e}")
    return None


def fetch_video_info(url: str):
    """Fetch video metadata and available qualities for any platform."""
    platform = detect_platform(url)

    # For TikTok, first try TikWM for clean no-watermark stream info
    if platform == "tiktok":
        tikwm_data = get_tiktok_info_tikwm(url)
        if tikwm_data:
            return tikwm_data

    # Use yt-dlp for all platforms
    ydl_opts = get_base_ydl_opts()
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                raise Exception("Unable to extract video information.")

            title = info.get("title") or "Video Download"
            thumbnail = info.get("thumbnail") or ""
            uploader = info.get("uploader") or info.get("channel") or info.get("creator") or platform.capitalize()
            duration = info.get("duration") or 0

            # Gather available resolutions
            formats = info.get("formats", [])
            heights = set()
            for f in formats:
                h = f.get("height")
                if h and isinstance(h, int) and h >= 240:
                    heights.add(h)

            sorted_heights = sorted(list(heights), reverse=True)
            quality_options = []

            # Quality presets
            preset_labels = {
                2160: "4K Ultra HD (2160p)",
                1440: "2K Quad HD (1440p)",
                1080: "Full HD (1080p) [Best]",
                720: "HD (720p)",
                480: "Standard (480p)",
                360: "Low (360p)"
            }

            if sorted_heights:
                # Add Best
                quality_options.append({"label": f"Highest Quality ({sorted_heights[0]}p)", "value": "best", "type": "video", "ext": "mp4"})
                for h in sorted_heights:
                    if h in [2160, 1440, 1080, 720, 480]:
                        quality_options.append({"label": preset_labels.get(h, f"{h}p"), "value": str(h), "type": "video", "ext": "mp4"})
            else:
                quality_options.append({"label": "Best Quality Video", "value": "best", "type": "video", "ext": "mp4"})

            # Always offer MP3 audio option
            quality_options.append({"label": "Audio Only (MP3 HQ)", "value": "mp3", "type": "audio", "ext": "mp3"})

            return {
                "success": True,
                "platform": platform,
                "title": title,
                "uploader": uploader,
                "thumbnail": thumbnail,
                "duration": duration,
                "url": url,
                "has_no_watermark": (platform in ["tiktok", "instagram", "facebook", "twitter", "pinterest", "reddit"]),
                "quality_options": quality_options
            }
    except Exception as e:
        logger.error(f"Error fetching info: {e}")
        return {"success": False, "error": str(e)}


def sanitize_filename(name: str) -> str:
    """Safe filename for all operating systems."""
    cleaned = re.sub(r'[\\/*?:"<>|]', "", name)
    cleaned = cleaned.strip()
    return cleaned[:80] if cleaned else "video"


def download_file_direct(url: str, output_path: str, task_id: str):
    """Direct HTTP stream download with progress calculation."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        }
        with requests.get(url, headers=headers, stream=True, timeout=30) as r:
            r.raise_for_status()
            total_size = int(r.headers.get("content-length", 0))
            downloaded = 0
            start_time = time.time()

            with open(output_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 128):
                    if not chunk:
                        continue
                    f.write(chunk)
                    downloaded += len(chunk)
                    elapsed = time.time() - start_time
                    speed = downloaded / elapsed if elapsed > 0 else 0
                    percent = (downloaded / total_size * 100) if total_size > 0 else 0

                    with tasks_lock:
                        tasks[task_id]["progress"] = round(percent, 1)
                        tasks[task_id]["speed"] = f"{speed / (1024 * 1024):.2f} MB/s" if speed > 0 else "0 MB/s"
                        tasks[task_id]["downloaded"] = f"{downloaded / (1024 * 1024):.1f} MB"
                        tasks[task_id]["total"] = f"{total_size / (1024 * 1024):.1f} MB" if total_size > 0 else "Unknown"

            with tasks_lock:
                tasks[task_id]["status"] = "finished"
                tasks[task_id]["progress"] = 100
                tasks[task_id]["file_path"] = output_path
                tasks[task_id]["filename"] = os.path.basename(output_path)
    except Exception as e:
        logger.error(f"Direct download error: {e}")
        with tasks_lock:
            tasks[task_id]["status"] = "error"
            tasks[task_id]["error"] = str(e)


def run_ytdlp_download(url: str, quality: str, is_audio: bool, task_id: str, custom_title: str = None):
    """yt-dlp powered download with progress tracking and ffmpeg integration."""
    def progress_hook(d):
        with tasks_lock:
            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes") or 0
                speed = d.get("speed") or 0
                eta = d.get("eta") or 0

                percent = (downloaded / total * 100) if total > 0 else 0
                speed_str = f"{(speed / (1024 * 1024)):.2f} MB/s" if speed else "Calculating..."
                eta_str = f"{int(eta)}s" if eta else "..."

                tasks[task_id]["progress"] = round(percent, 1)
                tasks[task_id]["speed"] = speed_str
                tasks[task_id]["eta"] = eta_str
                tasks[task_id]["downloaded"] = f"{downloaded / (1024 * 1024):.1f} MB"
                tasks[task_id]["total"] = f"{total / (1024 * 1024):.1f} MB" if total else "..."
                tasks[task_id]["status"] = "downloading"
            elif d.get("status") == "finished":
                tasks[task_id]["status"] = "processing"
                tasks[task_id]["progress"] = 99
                tasks[task_id]["message"] = "Merging audio & video (High Quality)..."

    ydl_opts = get_base_ydl_opts()
    ydl_opts["progress_hooks"] = [progress_hook]

    # Output template
    title_part = sanitize_filename(custom_title) if custom_title else "%(title).80B"
    unique_suffix = task_id[:8]
    output_template = os.path.join(DOWNLOAD_DIR, f"{title_part}_{unique_suffix}.%(ext)s")
    ydl_opts["outtmpl"] = output_template

    if is_audio:
        ydl_opts["format"] = "bestaudio/best"
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "320",
        }]
    else:
        # High quality video merging
        if quality == "best":
            if FFMPEG_PATH:
                ydl_opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
                ydl_opts["merge_output_format"] = "mp4"
            else:
                ydl_opts["format"] = "best[ext=mp4]/best"
        else:
            try:
                h = int(quality)
                if FFMPEG_PATH:
                    ydl_opts["format"] = f"bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={h}]+bestaudio/best[height<={h}]/best"
                    ydl_opts["merge_output_format"] = "mp4"
                else:
                    ydl_opts["format"] = f"best[height<={h}]/best"
            except ValueError:
                ydl_opts["format"] = "bestvideo+bestaudio/best"
                if FFMPEG_PATH:
                    ydl_opts["merge_output_format"] = "mp4"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            res = ydl.extract_info(url, download=True)
            # Find the generated file
            final_filename = ydl.prepare_filename(res)
            if is_audio:
                base, _ = os.path.splitext(final_filename)
                final_filename = base + ".mp3"

            if not os.path.exists(final_filename):
                # Search by task_id in folder
                for f in os.listdir(DOWNLOAD_DIR):
                    if unique_suffix in f:
                        final_filename = os.path.join(DOWNLOAD_DIR, f)
                        break

            with tasks_lock:
                tasks[task_id]["status"] = "finished"
                tasks[task_id]["progress"] = 100
                tasks[task_id]["file_path"] = final_filename
                tasks[task_id]["filename"] = os.path.basename(final_filename)
                tasks[task_id]["file_size"] = f"{os.path.getsize(final_filename) / (1024 * 1024):.2f} MB" if os.path.exists(final_filename) else "Unknown"
    except Exception as e:
        logger.error(f"yt-dlp download failed: {e}")
        with tasks_lock:
            tasks[task_id]["status"] = "error"
            tasks[task_id]["error"] = str(e)


def start_download_task(url: str, quality: str = "best", is_audio: bool = False, custom_title: str = None) -> str:
    """Start an asynchronous download job."""
    task_id = str(uuid.uuid4())
    with tasks_lock:
        tasks[task_id] = {
            "id": task_id,
            "url": url,
            "status": "starting",
            "progress": 0,
            "speed": "0 MB/s",
            "eta": "...",
            "downloaded": "0 MB",
            "total": "...",
            "file_path": None,
            "filename": None,
            "error": None,
            "created_at": time.time(),
        }

    platform = detect_platform(url)

    def worker():
        # Special TikTok fast-track without watermark via TikWM
        if platform == "tiktok" and not is_audio:
            tikwm_info = get_tiktok_info_tikwm(url)
            if tikwm_info and tikwm_info.get("no_wm_download_url"):
                clean_url = tikwm_info["no_wm_download_url"]
                safe_title = sanitize_filename(tikwm_info.get("title") or "tiktok_nowm")
                out_path = os.path.join(DOWNLOAD_DIR, f"{safe_title}_{task_id[:8]}.mp4")
                download_file_direct(clean_url, out_path, task_id)
                return

        # Default robust yt-dlp downloader
        run_ytdlp_download(url, quality, is_audio, task_id, custom_title)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return task_id


def get_task_status(task_id: str):
    """Retrieve current task state."""
    with tasks_lock:
        return tasks.get(task_id)


def get_download_history():
    """List downloaded files in the folder."""
    files = []
    if not os.path.exists(DOWNLOAD_DIR):
        return files

    for f in os.listdir(DOWNLOAD_DIR):
        p = os.path.join(DOWNLOAD_DIR, f)
        if os.path.isfile(p):
            stat = os.stat(p)
            files.append({
                "filename": f,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
                "mtime": stat.st_mtime
            })
    files.sort(key=lambda x: x["mtime"], reverse=True)
    return files
