# SmartWake

<p align="center">
  <a href="https://github.com/heavens7above/SmartWake/releases/download/v1.0.0/app-release.apk">
    <img src="https://img.shields.io/badge/⬇_Download_APK-v1.0.0-7B5CFF?style=for-the-badge&logo=android&logoColor=white" alt="Download APK"/>
  </a>
  &nbsp;
  <img src="https://img.shields.io/badge/Android-7.0%2B-00C9A7?style=for-the-badge&logo=android&logoColor=white" alt="Android 7.0+"/>
  &nbsp;
  <img src="https://img.shields.io/badge/Flutter-3.x-00D4FF?style=for-the-badge&logo=flutter&logoColor=white" alt="Flutter"/>
</p>

SmartWake is a strict, production-ready ML-powered smart alarm engine designed to autonomously detect your exact physiological sleep onset through native mobile background telemetry, then calculate biologically optimal (REM-free) wake cycles utilizing backwards-stepping algorithms!

## 📲 Android App — Quick Install

> **Latest release:** [v1.0.0](https://github.com/heavens7above/SmartWake/releases/tag/v1.0.0)

1. [**Download SmartWake-v1.0.0.apk**](https://github.com/heavens7above/SmartWake/releases/download/v1.0.0/app-release.apk)
2. On your Android device, go to **Settings → Security → Install unknown apps** and allow your browser/Files app
3. Open the downloaded APK and tap **Install**
4. Launch SmartWake, grant notification + battery optimisation permissions, and tap **Start Monitoring**

Requires **Android 7.0+ (API 24)**. Pair with a running SmartWake server for full ML inference.

---

## Key Features

- **Zero-Trust Cloud Inference**: A centralized Python FastAPI analytics engine hosted behind robust Header-Level API authentication dependencies. It actively intercepts JSON payloads evaluating incoming Termux accelerometer trajectories against a pre-compiled `GradientBoostingClassifier`.
- **Untethered Android Polling**: Persistent native OS workers bypassing strict Android Doze cycles. Utilizing `termux-api` they poll battery, movement, and notification data blindly transmitting to the web architecture before activating localized mp3 alarms!
- **One-Line Termux Bootstrap**: A hosted `/install` script downloads the current `logger.py`, `alarm.py`, and `start.sh` payloads directly onto the phone without any ADB step.

## Documentation

For deep-dives into executing the `sqlite3` layout patterns or setting up your localized Termux configurations seamlessly onto hardware, head towards the `docs/` hierarchy:

- [System Architecture Breakdown](./docs/ARCHITECTURE.md)
- [Railway & Termux User Guide](./docs/GUIDE.md)

## Quick Start (Server + Termux)

1. Set `API_KEY` in `server/.env` and keep the same value in the Flutter app settings or via `--dart-define=SMARTWAKE_API_KEY=...`.
2. Push the repo to Railway. `railway.json` starts `gunicorn` with Uvicorn workers from the `server/` directory.
3. Train your model with [`train/Train.ipynb`](https://colab.research.google.com/drive/1srubKtguThzFZl7F3N0CdeaHipO196ia?usp=sharing). The local runtime path is `server/src/model/sleep_model.pkl`, and the server-root runtime path is `src/model/sleep_model.pkl`.
4. On your Android device, run `curl -sL https://your-domain/install | bash`. If you changed `API_KEY`, export `SMARTWAKE_API_KEY=...` before starting the workers.
5. Start the phone workers with `cd ~/smartwake && bash start.sh`.
