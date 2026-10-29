# Dhan Downloads Folder

Place your compiled Android `.apk` file here named:
`dhan.apk`

When a visitor clicks "Download for Android (APK)" on the website, this file will automatically download.

### How to build the APK with EAS:
Run in project root:
```bash
npx eas-cli build -p android --profile preview
```

Once the build finishes:
1. Download the `.apk` file from the EAS build dashboard / link.
2. Rename it to `dhan.apk` and paste it into this `website/downloads/` folder.
3. Alternatively, open `website/index.html` and update `androidApkUrl` in `DHAN_CONFIG` directly with your EAS public download link or Google Drive link.
