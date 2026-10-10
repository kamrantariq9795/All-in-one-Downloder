# 📱 Android Mobile App & APK Guide

OmniDownloader ko mobile par do tareeqon se app ki tarah chalaya ja sakta hai:

---

## ⚡ Method 1: Instant PWA Install (Sabse Aasan & Best Tareeqa)

Kisi bhi compiling ya APK file ke jhanjhat ke baghair direct install karein:

1. Apne PC par downloader start karein (`Run_Downloader.bat` ya `desktop_app.py`).
2. Apne mobile browser (Google Chrome, Brave ya Samsung Internet) mein yeh address open karein:
   ```
   http://<Aapke-PC-Ka-IP>:5000
   ```
   *(Jaise: `http://192.168.0.101:5000`)*
3. Screen par **"Install Mobile App"** ya **"Get App"** ka button samne aayega, us par tap karein.
4. Ya Chrome menu (3 dots) par click kar ke **"Add to Home screen" / "Install App"** select karein.
5. Mobile ki home screen par **OmniDownloader** ka native app icon ban jayega jo bilkul kisi APK app ki tarah fullscreen open hota hai!

---

## 🚀 Standalone Ready APK (Already Built)

A production-ready standalone APK has already been compiled for **`https://allinonedownloder.vercel.app`**:
- **APK Location**: [`OmniDownloader.apk`](file:///c:/Users/KAMRAN__TARIQ/Downloads/Compressed/All-in-one-Downloder-main/All-in-one-Downloder-main/OmniDownloader.apk) (Root directory)
- **AAB / Signing Bundle**: Located in [`android_apk_build/`](file:///c:/Users/KAMRAN__TARIQ/Downloads/Compressed/All-in-one-Downloder-main/All-in-one-Downloder-main/android_apk_build)
- Simply transfer `OmniDownloader.apk` to your Android device via USB, WhatsApp, or Google Drive, tap to install, and run!

---

## 🛠️ Method 2: Android Studio se Standalone APK Build Karna

Agar aapko Android Studio mein khud custom changes kar ke build karna hai:

1. **Android Studio** open karein.
2. **Open Project** par click karein aur yeh folder select karein:
   `android/`
3. [`MainActivity.java`](file:///c:/Users/KAMRAN__TARIQ/Downloads/Compressed/All-in-one-Downloder-main/All-in-one-Downloder-main/android/app/src/main/java/com/omnidownloader/app/MainActivity.java) already configured hai:
   ```java
   private static final String APP_URL = "https://allinonedownloder.vercel.app";
   ```
4. Menu mein jayein: **Build > Build Bundle(s) / APK(s) > Build APK(s)**.
5. Android Studio kuch hi lamhon mein aapki nayi `.apk` file bana dega!
