# 🚀 OmniDownloader PRO - Flutter Mobile APK Project

Yeh mukammal **Flutter Android App** project hai jo OmniDownloader ke backend ke sath connect ho kar mobile par high quality, watermark-free videos download karta hai aur direct mobile ke **Downloads** folder mein save karta hai.

---

## 📁 Project Structure

```
d:\All Downloder\flutter_app\
├── pubspec.yaml                 # Dependencies (Dio, HTTP, Permissions)
├── lib/
│   ├── main.dart                # Material 3 Dark UI entrypoint
│   └── screens/
│       └── home_screen.dart     # Video Fetcher, Thumbnail preview & Downloader UI
```

---

## 🛠️ APK Kaise Banayein (How to Build APK)

### Step 1: Flutter Setup (Agar pehle se install nahi hai)
1. Official website se Flutter SDK download karein: `https://flutter.dev/docs/get-started/install/windows`
2. CMD / Terminal mein check karein:
   ```bash
   flutter doctor
   ```

### Step 2: Dependencies Install Karein
`flutter_app` folder ke andar terminal open karein aur yeh command chalayein:
```bash
cd "d:\All Downloder\flutter_app"
flutter pub get
```

### Step 3: APK Build Karein (Production Release)
Release APK generate karne ke liye yeh command chalayein:
```bash
flutter build apk --release
```

- Kuch hi lamhon mein aapki APK file is location par ban kar tayar ho jayegi:
  ```
  flutter_app\build\app\outputs\flutter-apk\app-release.apk
  ```

---

## 📲 Mobile par Install & Use Karne Ka Tareeqa

1. `app-release.apk` file ko apne mobile par transfer karein (WhatsApp, USB Cable ya Google Drive se).
2. Mobile par tap kar ke **Install** karein.
3. App open karein:
   - Top-right par **Settings icon (⚙️)** dabayein aur apne PC ka IP set karein (jaise: `http://192.168.0.101:5000`).
   - Koi bhi TikTok, Reels ya YouTube link paste karein.
   - **Download Video** dabayein — video bina watermark ke direct mobile storage mein save ho jayegi!
