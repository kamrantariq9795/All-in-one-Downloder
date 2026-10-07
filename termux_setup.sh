#!/bin/bash
echo "====================================================="
echo "   Setting up OmniDownloader Mobile Server on Android"
echo "====================================================="

# 1. Setup storage permission so downloads save to phone
echo "[*] Storage permission maang raha hai, 'Allow' dabayein..."
termux-setup-storage

# 2. Install Python and FFmpeg on mobile
echo "[*] Python aur FFmpeg install ho raha hai..."
pkg update -y
pkg install python ffmpeg git -y

# 3. Install Python dependencies
echo "[*] yt-dlp aur Flask install ho raha hai..."
pip install --upgrade pip
pip install yt-dlp flask flask-cors requests imageio-ffmpeg

echo ""
echo "====================================================="
echo "   SETUP COMPLETE! Starting Mobile Server..."
echo "====================================================="
echo " [*] Mobile browser kholein aur type karein:"
echo "     http://localhost:5000"
echo " [*] Videos aapke phone ke Download folder mein aayengi!"
echo "====================================================="

# 4. Run server on Android
python app.py
