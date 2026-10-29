# DHAN App Landing & Download Website

A sleek, responsive landing page and download portal built specifically for the **DHAN** personal finance mobile app.

---

## 🌟 Key Features
- **Smart Device Detection**: Automatically identifies if visitor is on **Android**, **iOS (iPhone/iPad)**, or **Desktop/PC**, highlighting the appropriate download option.
- **Direct 1-Click Android APK Download**: Instantly downloads `dhan.apk` with built-in installation guide.
- **iOS Download Portal**: Supports Apple TestFlight invite links and Apple App Store redirection.
- **Dynamic QR Code**: Desktop visitors can scan the QR code with their mobile camera to open and download instantly on their phones.
- **Live App Showcase & Screen Switcher**: Displays screenshots of Net Balance, Smart Budgeting, and Wealth Reports.
- **Brand Themed**: Designed around DHAN's signature `#0B5D46` emerald green and dark luxury glassmorphism styling.

---

## 📁 Directory Structure
```
website/
├── index.html        # Main landing page (HTML5 + Tailwind CSS + Vanilla JS)
├── assets/           # App icons, mockups, and screenshots
│   ├── icon.png
│   ├── dhan-1.jpg
│   ├── dhan-3.jpg
│   └── dhan-4.jpg
└── downloads/        # Place compiled APKs here
    └── dhan.apk
```

---

## 🚀 How to Run & Preview Locally
You have two simple options:

### Option 1: Direct File Opening
Double-click `website/index.html` in your file explorer to open it in any web browser.

### Option 2: Local HTTP Server
Run from terminal in the root directory:
```bash
npx serve website
# or with Python
python -m http.server 3000 --directory website
```
Then visit `http://localhost:3000`.

---

## ⚙️ How to Customize Download Links
Open `website/index.html` and scroll to the `<script>` section near the bottom. Update `DHAN_CONFIG`:

```javascript
const DHAN_CONFIG = {
  version: "1.0.0",
  androidApkUrl: "downloads/dhan.apk",            // Or your Google Drive / GitHub Release direct link
  iosTestFlightUrl: "https://testflight.apple.com/join/YOUR_INVITE_CODE", // Your Apple TestFlight link
  iosAppStoreUrl: "https://apps.apple.com/app/idYOUR_APP_ID",             // Your official App Store link
  backendApiUrl: "https://dhan-api-jqfp.onrender.com"                     // Health-check endpoint
};
```

---

## 📦 How to Build the Real Android APK
Run this command from the project root:
```bash
npx eas-cli build -p android --profile preview
```
Once the build completes on EAS:
1. Download the generated `.apk` file.
2. Put it into `website/downloads/dhan.apk`.
3. (Also copy to `backend/fastapi_app/static/downloads/dhan.apk` if hosting on Render).

---

## 🌐 Free Deployment Options

### 1. Hosted with your existing Backend on Render (Already Configured!)
The FastAPI backend (`backend/fastapi_app/main.py`) now serves this website directly at `/`. When you push to your Git repository, Render builds and deploys your website automatically at:
`https://dhan-api-jqfp.onrender.com/`

### 2. Vercel or Netlify (Fast & Free CDN)
- **Vercel**: Import repository on [vercel.com](https://vercel.com), set root directory to `website`, click Deploy.
- **Netlify**: Drag and drop the `website` folder directly into [app.netlify.com/drop](https://app.netlify.com/drop).

### 3. GitHub Pages
Push `website/` to `gh-pages` branch or configure GitHub Pages in Repository Settings → Pages → Deploy from branch `/website`.

