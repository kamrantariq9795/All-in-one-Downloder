import os
import sys
import re
import time
import uuid
import shutil
import logging
import threading
import urllib.parse
import requests
import yt_dlp

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Base directories (auto-detects Android mobile public storage & serverless /tmp)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IS_SERVERLESS = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))

if os.path.exists("/sdcard/Download"):
    DOWNLOAD_DIR = "/sdcard/Download"
elif IS_SERVERLESS or not os.access(BASE_DIR, os.W_OK):
    DOWNLOAD_DIR = "/tmp/downloads"
else:
    DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")

try:
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
except Exception:
    DOWNLOAD_DIR = "/tmp/downloads"
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

SAVENOW_API_KEY = "dfcb6d76f2f6a9894gjkege8a4ab232222"
SAVENOW_HOSTS = ["https://p.savenow.to", "https://loader.to"]


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


def extract_youtube_id(url: str) -> str:
    """Extract 11-character YouTube video ID from any YouTube URL."""
    patterns = [
        r"(?:v=|\/videos\/|embed\/|youtu\.be\/|\/v\/|\/e\/|watch\?v=|&v=|\/shorts\/|\/live\/)([a-zA-Z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return ""


def get_base_ydl_opts():
    """Common yt-dlp options with anti-bot evasion headers and multi-client configs."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "ignoreerrors": False,
        "logtostderr": False,
        "noplaylist": True,
        "geo_bypass": True,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "extractor_args": {
            "youtube": {
                "player_client": ["ios", "android", "mweb", "web"],
            }
        },
    }
    cookies_path = os.path.join(BASE_DIR, "cookies.txt")
    if os.path.exists(cookies_path):
        opts["cookiefile"] = cookies_path
    elif os.environ.get("YOUTUBE_COOKIES"):
        tmp_cookie = os.path.join(DOWNLOAD_DIR, "yt_cookies.txt")
        try:
            with open(tmp_cookie, "w", encoding="utf-8") as cf:
                cf.write(os.environ["YOUTUBE_COOKIES"])
            opts["cookiefile"] = tmp_cookie
        except Exception:
            pass
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


def get_youtube_info_fallback(url: str):
    """Fetch YouTube video info using oEmbed / Noembed / Savenow API when yt-dlp hits bot protection."""
    vid = extract_youtube_id(url)
    clean_url = f"https://www.youtube.com/watch?v={vid}" if vid else url
    title = None
    uploader = "YouTube Creator"
    thumbnail = f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg" if vid else ""

    # 1. Try YouTube official oEmbed
    try:
        oembed_url = f"https://www.youtube.com/oembed?url={urllib.parse.quote(clean_url)}&format=json"
        r = requests.get(oembed_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
        if r.status_code == 200:
            data = r.json()
            title = data.get("title")
            uploader = data.get("author_name") or uploader
            thumbnail = data.get("thumbnail_url") or thumbnail
    except Exception as e:
        logger.warning(f"YouTube oEmbed failed: {e}")

    # 2. Fallback to noembed.com
    if not title:
        try:
            noembed_url = f"https://noembed.com/embed?url={urllib.parse.quote(clean_url)}"
            r = requests.get(noembed_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code == 200:
                data = r.json()
                title = data.get("title")
                uploader = data.get("author_name") or uploader
                thumbnail = data.get("thumbnail_url") or thumbnail
        except Exception as e:
            logger.warning(f"Noembed failed: {e}")

    # 3. Fallback to Savenow metadata
    if not title:
        for host in SAVENOW_HOSTS:
            try:
                api_url = f"{host}/ajax/download.php?format=720&url={urllib.parse.quote(clean_url)}&api={SAVENOW_API_KEY}"
                r = requests.get(api_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
                if r.status_code == 200:
                    data = r.json()
                    if data.get("success"):
                        title = data.get("title") or data.get("info", {}).get("title")
                        thumbnail = data.get("info", {}).get("image") or data.get("thumbnail_url") or thumbnail
                        break
            except Exception:
                pass

    if not title and not vid:
        return None

    return {
        "success": True,
        "platform": "youtube",
        "title": title or f"YouTube Video ({vid})",
        "uploader": uploader,
        "thumbnail": thumbnail,
        "duration": 0,
        "url": clean_url,
        "has_no_watermark": True,
        "quality_options": [
            {"label": "Highest Quality (1080p)", "value": "best", "type": "video", "ext": "mp4"},
            {"label": "Full HD (1080p) [Best]", "value": "1080", "type": "video", "ext": "mp4"},
            {"label": "HD (720p)", "value": "720", "type": "video", "ext": "mp4"},
            {"label": "Standard (480p)", "value": "480", "type": "video", "ext": "mp4"},
            {"label": "Low (360p)", "value": "360", "type": "video", "ext": "mp4"},
            {"label": "Audio Only (MP3 HQ)", "value": "mp3", "type": "audio", "ext": "mp3"},
        ],
    }


def fetch_video_info(url: str):
    """Fetch video metadata and available qualities for any platform."""
    platform = detect_platform(url)

    # For TikTok, first try TikWM for clean no-watermark stream info
    if platform == "tiktok":
        tikwm_data = get_tiktok_info_tikwm(url)
        if tikwm_data:
            return tikwm_data

    # On serverless (Vercel), YouTube datacenter IPs are blocked by yt-dlp without cookies;
    # use fast oEmbed/cloud extractor directly unless cookies.txt is configured.
    has_cookies = os.path.exists(os.path.join(BASE_DIR, "cookies.txt")) or bool(os.environ.get("YOUTUBE_COOKIES"))
    if platform == "youtube" and IS_SERVERLESS and not has_cookies:
        yt_fallback = get_youtube_info_fallback(url)
        if yt_fallback:
            return yt_fallback

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

            preset_labels = {
                2160: "4K Ultra HD (2160p)",
                1440: "2K Quad HD (1440p)",
                1080: "Full HD (1080p) [Best]",
                720: "HD (720p)",
                480: "Standard (480p)",
                360: "Low (360p)"
            }

            if sorted_heights:
                quality_options.append({"label": f"Highest Quality ({sorted_heights[0]}p)", "value": "best", "type": "video", "ext": "mp4"})
                for h in sorted_heights:
                    if h in [2160, 1440, 1080, 720, 480]:
                        quality_options.append({"label": preset_labels.get(h, f"{h}p"), "value": str(h), "type": "video", "ext": "mp4"})
            else:
                quality_options.append({"label": "Best Quality Video", "value": "best", "type": "video", "ext": "mp4"})

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
        logger.warning(f"yt-dlp info extraction failed ({platform}): {e}")
        # Automatic fallback for YouTube & supported URLs when yt-dlp hits bot check
        yt_fallback = get_youtube_info_fallback(url)
        if yt_fallback:
            return yt_fallback
        return {"success": False, "error": str(e)}


def sanitize_filename(name: str) -> str:
    """Safe filename for all operating systems."""
    cleaned = re.sub(r'[\\/*?:"<>|]', "", name or "")
    cleaned = cleaned.strip()
    return cleaned[:80] if cleaned else "video"


def start_savenow_job(url: str, quality: str, is_audio: bool):
    """Initiate a cloud stream conversion job on Savenow/Loader API."""
    if is_audio or quality == "mp3":
        fmt = "mp3"
    elif quality in ["1080", "720", "480", "360", "2160", "1440"]:
        fmt = quality
    else:
        fmt = "720"

    vid = extract_youtube_id(url)
    clean_url = f"https://www.youtube.com/watch?v={vid}" if vid else url

    for host in SAVENOW_HOSTS:
        try:
            api_url = f"{host}/ajax/download.php?format={fmt}&url={urllib.parse.quote(clean_url)}&api={SAVENOW_API_KEY}"
            r = requests.get(api_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data.get("success") and data.get("id"):
                    return {
                        "id": data["id"],
                        "title": data.get("title") or data.get("info", {}).get("title") or "video",
                        "ext": "mp3" if fmt == "mp3" else "mp4",
                    }
        except Exception as e:
            logger.warning(f"Savenow init failed on {host}: {e}")
    return None


def poll_savenow_job(savenow_id: str, ext: str = "mp4", custom_title: str = "video"):
    """Check progress of a Savenow cloud job (stateless-compatible for Vercel)."""
    for host in SAVENOW_HOSTS:
        try:
            poll_url = f"{host}/ajax/progress.php?id={urllib.parse.quote(savenow_id)}"
            r = requests.get(poll_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
            if r.status_code == 200:
                pd = r.json()
                raw_prog = pd.get("progress") or 0
                pct = max(5.0, min(99.0, round(raw_prog / 10.0, 1)))
                title = pd.get("title") or pd.get("info", {}).get("title") or custom_title or "video"
                safe_title = sanitize_filename(title)
                filename = f"{safe_title}.{ext}"

                if pd.get("success") == 1 and pd.get("download_url"):
                    return {
                        "id": f"sn_{ext}_{savenow_id}",
                        "status": "finished",
                        "progress": 100,
                        "speed": "Cloud CDN",
                        "eta": "0s",
                        "downloaded": "100%",
                        "total": "100%",
                        "filename": filename,
                        "direct_url": pd["download_url"],
                        "error": None,
                    }
                elif pd.get("success") == -1 or (pd.get("text") and "error" in pd.get("text", "").lower()):
                    return {
                        "id": f"sn_{ext}_{savenow_id}",
                        "status": "error",
                        "progress": 0,
                        "error": pd.get("text") or "Cloud stream conversion failed.",
                    }
                else:
                    return {
                        "id": f"sn_{ext}_{savenow_id}",
                        "status": "downloading",
                        "progress": pct,
                        "speed": "Cloud Stream",
                        "eta": "Few seconds",
                        "downloaded": f"{int(pct)}%",
                        "total": "100%",
                        "filename": filename,
                        "error": None,
                    }
        except Exception as e:
            logger.warning(f"Savenow poll error on {host}: {e}")
    return None


def download_file_direct(url: str, output_path: str, task_id: str, direct_url: str = None):
    """Direct HTTP stream download with progress calculation."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
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
                    percent = (downloaded / total_size * 100) if total_size > 0 else 50

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
                if direct_url:
                    tasks[task_id]["direct_url"] = direct_url
    except Exception as e:
        logger.error(f"Direct download error: {e}")
        with tasks_lock:
            if direct_url:
                tasks[task_id]["status"] = "finished"
                tasks[task_id]["progress"] = 100
                tasks[task_id]["direct_url"] = direct_url
            else:
                tasks[task_id]["status"] = "error"
                tasks[task_id]["error"] = str(e)


def run_savenow_local_download(url: str, quality: str, is_audio: bool, task_id: str, custom_title: str = None):
    """Fallback downloader that polls Savenow and saves the file locally (plus provides direct_url)."""
    job = start_savenow_job(url, quality, is_audio)
    if not job:
        with tasks_lock:
            tasks[task_id]["status"] = "error"
            tasks[task_id]["error"] = "Unable to initialize fallback stream downloader."
        return

    savenow_id = job["id"]
    ext = job["ext"]
    title = custom_title or job["title"]

    for _ in range(60):
        state = poll_savenow_job(savenow_id, ext, title)
        if state:
            with tasks_lock:
                tasks[task_id]["progress"] = state.get("progress", 10)
                tasks[task_id]["speed"] = state.get("speed", "Cloud Stream")
                tasks[task_id]["eta"] = state.get("eta", "...")
                tasks[task_id]["downloaded"] = state.get("downloaded", "...")
                tasks[task_id]["total"] = state.get("total", "100%")

            if state["status"] == "finished" and state.get("direct_url"):
                dl_url = state["direct_url"]
                safe_title = sanitize_filename(title)
                out_path = os.path.join(DOWNLOAD_DIR, f"{safe_title}_{task_id[:8]}.{ext}")
                if IS_SERVERLESS:
                    with tasks_lock:
                        tasks[task_id]["status"] = "finished"
                        tasks[task_id]["progress"] = 100
                        tasks[task_id]["filename"] = f"{safe_title}.{ext}"
                        tasks[task_id]["direct_url"] = dl_url
                    return
                else:
                    download_file_direct(dl_url, out_path, task_id, direct_url=dl_url)
                    return
            elif state["status"] == "error":
                with tasks_lock:
                    tasks[task_id]["status"] = "error"
                    tasks[task_id]["error"] = state.get("error", "Stream conversion failed")
                return
        time.sleep(2)

    with tasks_lock:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["error"] = "Download timed out waiting for stream conversion."


def run_ytdlp_download(url: str, quality: str, is_audio: bool, task_id: str, custom_title: str = None):
    """yt-dlp powered download with progress tracking, ffmpeg integration, and cloud fallback."""
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

    title_part = sanitize_filename(custom_title) if custom_title else "%(title).80B"
    unique_suffix = task_id[:8]
    output_template = os.path.join(DOWNLOAD_DIR, f"{title_part}_{unique_suffix}.%(ext)s")
    ydl_opts["outtmpl"] = output_template

    if is_audio:
        ydl_opts["format"] = "bestaudio/best"
        if FFMPEG_PATH:
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }]
    else:
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
            final_filename = ydl.prepare_filename(res)
            if is_audio and FFMPEG_PATH:
                base, _ = os.path.splitext(final_filename)
                final_filename = base + ".mp3"

            if not os.path.exists(final_filename):
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
        logger.warning(f"yt-dlp download failed ({e}), switching to cloud stream fallback...")
        run_savenow_local_download(url, quality, is_audio, task_id, custom_title)


def start_download_task(url: str, quality: str = "best", is_audio: bool = False, custom_title: str = None) -> str:
    """Start an asynchronous or stateless cloud download job."""
    platform = detect_platform(url)

    # On Vercel/serverless, background threads get frozen after HTTP response returns.
    # For YouTube on serverless (or when no cookies are present), use stateless Savenow job IDs.
    has_cookies = os.path.exists(os.path.join(BASE_DIR, "cookies.txt")) or bool(os.environ.get("YOUTUBE_COOKIES"))
    if platform == "youtube" and IS_SERVERLESS and not has_cookies:
        job = start_savenow_job(url, quality, is_audio)
        if job:
            ext = job["ext"]
            savenow_id = job["id"]
            task_id = f"sn_{ext}_{savenow_id}"
            with tasks_lock:
                tasks[task_id] = {
                    "id": task_id,
                    "title": custom_title or job.get("title") or "video",
                    "ext": ext,
                    "savenow_id": savenow_id,
                }
            return task_id

    # For TikTok on serverless, return immediate finished task with direct stream URL
    if platform == "tiktok" and IS_SERVERLESS:
        tikwm_info = get_tiktok_info_tikwm(url)
        if tikwm_info:
            dl_url = tikwm_info.get("audio_url") if is_audio else tikwm_info.get("no_wm_download_url")
            if dl_url:
                ext = "mp3" if is_audio else "mp4"
                safe_title = sanitize_filename(custom_title or tikwm_info.get("title") or "tiktok_video")
                task_id = f"direct_{uuid.uuid4().hex[:8]}"
                with tasks_lock:
                    tasks[task_id] = {
                        "id": task_id,
                        "url": url,
                        "status": "finished",
                        "progress": 100,
                        "speed": "Direct CDN",
                        "eta": "0s",
                        "downloaded": "100%",
                        "total": "100%",
                        "file_path": None,
                        "filename": f"{safe_title}.{ext}",
                        "direct_url": dl_url,
                        "error": None,
                        "created_at": time.time(),
                    }
                return task_id

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
            "direct_url": None,
            "error": None,
            "created_at": time.time(),
        }

    def worker():
        if platform == "tiktok":
            tikwm_info = get_tiktok_info_tikwm(url)
            if tikwm_info:
                clean_url = tikwm_info.get("audio_url") if is_audio else tikwm_info.get("no_wm_download_url")
                if clean_url:
                    ext = "mp3" if is_audio else "mp4"
                    safe_title = sanitize_filename(custom_title or tikwm_info.get("title") or "tiktok_nowm")
                    out_path = os.path.join(DOWNLOAD_DIR, f"{safe_title}_{task_id[:8]}.{ext}")
                    download_file_direct(clean_url, out_path, task_id, direct_url=clean_url)
                    return

        run_ytdlp_download(url, quality, is_audio, task_id, custom_title)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return task_id


def get_task_status(task_id: str):
    """Retrieve current task state (supports both in-memory tasks and stateless sn_ cloud tasks)."""
    if task_id.startswith("sn_"):
        parts = task_id.split("_", 2)
        if len(parts) == 3:
            _, ext, savenow_id = parts
        else:
            ext = "mp4"
            savenow_id = task_id[3:]

        custom_title = "video"
        with tasks_lock:
            if task_id in tasks:
                custom_title = tasks[task_id].get("title") or "video"

        state = poll_savenow_job(savenow_id, ext=ext, custom_title=custom_title)
        if state:
            return state

    with tasks_lock:
        return tasks.get(task_id)


def get_download_history():
    """List downloaded files in the folder."""
    files = []
    if not os.path.exists(DOWNLOAD_DIR):
        return files

    for f in os.listdir(DOWNLOAD_DIR):
        if f.startswith(".") or f == "yt_cookies.txt":
            continue
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
