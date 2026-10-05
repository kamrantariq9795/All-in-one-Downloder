# 🚀 All-in-One High Quality Video Downloader (No Watermark)

Ek powerful aur modern Video Downloader jo internet ke tamam popular platforms se baghair kisi watermark ke, aur highest quality (1080p, 2K, 4K ya MP3) mein video download karta hai.

---

## 🌟 Key Features (Khususiyaat)

1. **Baghair Watermark (100% Clean):**
   - **TikTok:** Videos direct baghair TikTok logo ya end-screen watermark ke download hoti hain.
   - **Instagram:** Reels, Posts aur Stories bina kisi watermark ke original HD quality mein.
   - **Facebook:** Public Reels aur HD videos.
   - **Twitter / X & Pinterest:** Direct raw clean MP4 streams.

2. **Supreme Quality & FFmpeg Audio Merging:**
   - **YouTube:** 4K Ultra HD (2160p), 2K Quad HD (1440p), Full HD (1080p 60fps), 720p HD.
   - Separate high-bitrate video + audio automatically merge hote hain bina kisi quality loss ke.
   - **Audio Mode:** Kisi bhi video ko direct 320kbps MP3 audio mein convert karne ki sahulat.

3. **Ultra-Modern Cyber/Glassmorphism Web UI:**
   - Beautiful Dark Theme with real-time platform auto-detection.
   - One-Click **Paste from Clipboard** button.
   - Video thumbnail, creator name, duration preview.
   - Real-time download progress bar (Speed MB/s, Percentage, ETA).
   - Direct browser download + Windows File Explorer folder open feature.
   - Built-in video player & download history library.

---

## 🛠️ Supported Platforms

- ✅ **TikTok** (Without Watermark / No Watermark)
- ✅ **YouTube** (Shorts & Long Videos in 1080p/2K/4K/MP3)
- ✅ **Instagram** (Reels, Posts)
- ✅ **Facebook** (Reels, Videos)
- ✅ **Twitter / X**
- ✅ **Pinterest**
- ✅ **Reddit** (Video + Audio Merged)
- ✅ **Snapchat, Threads, Vimeo, Dailymotion, etc.**

---

## 🚀 How to Run (Chalane Ka Tareeqa)

### Tareeqa 1: One-Click Launcher (Sabse Aasan)
Sirf **`Run_Downloader.bat`** file par double-click karein:
- Yeh server start karega aur aapke browser mein foran `http://localhost:5000` open kar dega.

### Tareeqa 2: Terminal / CMD se
1. Terminal / PowerShell open karein:
   ```bash
   python app.py
   ```
2. Browser mein open karein:
   ```
   http://localhost:5000
   ```

---

## 📁 File Structure

```
d:\All Downloder\
├── app.py                  # Flask Web Server & API
├── downloader.py           # yt-dlp, TikWM & FFmpeg Engine
├── Run_Downloader.bat      # One-click Windows starter
├── requirements.txt        # Libraries list
├── downloads/              # Downloaded videos yahan save hoti hain
├── templates/
│   └── index.html          # Frontend UI
└── static/
    ├── css/style.css       # Styling & Effects
    └── js/app.js           # Client-side Logic & Live Progress
```

---

## ⚡ Important Notes
- Videos aapke computer mein `d:\All Downloder\downloads` folder mein save hoti hain aur browser mein bhi foran download ho jati hain.
- Aap web interface mein "Downloads Folder" button par click kar ke direct Windows File Explorer mein folder dekh sakte hain.
