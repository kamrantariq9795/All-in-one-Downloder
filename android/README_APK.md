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

## 🛠️ Method 2: Android Studio se Standalone APK Build Karna

Agar aapko direct `.apk` file generate karni hai:

1. **Android Studio** open karein.
2. **Open Project** par click karein aur yeh folder select karein:
   `D:\All Downloder\android`
3. [MainActivity.java](file:///d:/All%20Downloder/android/app/src/main/java/com/omnidownloader/app/MainActivity.java) mein `APP_URL` ko apne computer ke local IP par set karein (jaise: `http://192.168.0.101:5000`).
4. Menu mein jayein: **Build > Build Bundle(s) / APK(s) > Build APK(s)**
5. Android Studio kuch hi lamhon mein aapki **`OmniDownloader.apk`** file bana dega!
