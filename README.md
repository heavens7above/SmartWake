# SmartWake

<p align="center">
  <a href="https://github.com/heavens7above/SmartWake/releases/download/v1.0.0/SmartWake-v1.0.0.apk">
    <img src="https://img.shields.io/badge/⬇_Download_APK-v1.0.0-7B5CFF?style=for-the-badge&logo=android&logoColor=white" alt="Download APK"/>
  </a>
  &nbsp;
  <img src="https://img.shields.io/badge/Android-5.0%2B-00C9A7?style=for-the-badge&logo=android&logoColor=white" alt="Android 5.0+"/>
  &nbsp;
  <img src="https://img.shields.io/badge/Flutter-3.x-00D4FF?style=for-the-badge&logo=flutter&logoColor=white" alt="Flutter"/>
</p>

SmartWake is a strict, production-ready ML-powered smart alarm engine designed to autonomously detect your exact physiological sleep onset through native mobile background telemetry, then calculate biologically optimal (REM-free) wake cycles utilizing backwards-stepping algorithms!

## 📲 Android App — Quick Install

> **Latest release:** [v1.0.0](https://github.com/heavens7above/SmartWake/releases/tag/v1.0.0)

1. [**Download SmartWake-v1.0.0.apk**](https://github.com/heavens7above/SmartWake/releases/download/v1.0.0/SmartWake-v1.0.0.apk)
2. On your Android device, go to **Settings → Security → Install unknown apps** and allow your browser/Files app
3. Open the downloaded APK and tap **Install**
4. Launch SmartWake, grant notification + battery optimisation permissions, and tap **Start Monitoring**

Requires **Android 5.0+ (API 21)**. Pair with a running SmartWake server for full ML inference.

---

## Key Features
- **Zero-Trust Cloud Inference**: A centralized Python FastAPI analytics engine hosted behind robust Header-Level API authentication dependencies. It actively intercepts JSON payloads evaluating incoming Termux accelerometer trajectories against a pre-compiled `GradientBoostingClassifier`.
- **Untethered Android Polling**: Persistent native OS workers bypassing strict Android Doze cycles. Utilizing `termux-api` they poll battery, movement, and notification data blindly transmitting to the web architecture before activating localized mp3 alarms!
- **Wireless ADB Auto-Injection**: A single robust `deploy_adb.sh` shell script leveraging native Android Debug Bridge features unlocking user screens natively, establishing file paths, and actively "typing" the initial Termux launch sequences!

## Documentation
For deep-dives into executing the `sqlite3` layout patterns or setting up your localized Termux configurations seamlessly onto hardware, head towards the `docs/` hierarchy:
- [System Architecture Breakdown](./docs/ARCHITECTURE.md)
- [Railway & Termux User Guide](./docs/GUIDE.md)

## Quick Start (Server + Termux)
1. Edit the API token string alongside `server/.env`.
2. Push your localized repository into GitHub binding it onto Railway. Nixpacks will utilize `railway.json` spinning internal Python instances perfectly!
3. Evaluate your own sleep patterns compiling `train/Train.ipynb` and deploy the output binary file towards `server/src/ml/sleep_model.pkl`.
4. Spin up Termux natively on your Android device and execute `bash termux/deploy_adb.sh` over your workstation resolving all app deployment mechanics dynamically!
