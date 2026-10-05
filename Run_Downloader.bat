@echo off
title All-in-One High Quality Video Downloader
color 0b

echo ================================================================
echo           ALL-IN-ONE VIDEO DOWNLOADER (NO WATERMARK)
echo ================================================================
echo.
echo [*] Starting server...
echo [*] Supported: TikTok (No WM), YouTube (4K/1080p), Instagram, FB, Twitter...
echo.

:: Open browser after 2 seconds in background
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:5000"

:: Start Python Flask Server
python app.py

pause
