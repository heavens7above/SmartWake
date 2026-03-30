# SmartWake 

SmartWake is a strict, production-ready ML-powered smart alarm engine designed to autonomously detect your exact physiological sleep onset through native mobile background telemetry, then calculate biologically optimal (REM-free) wake cycles utilizing backwards-stepping algorithms!

## Key Features
- **Zero-Trust Cloud Inference**: A centralized Python FastAPI analytics engine hosted behind robust Header-Level API authentication dependencies. It actively intercepts JSON payloads evaluating incoming Termux accelerometer trajectories against a pre-compiled `GradientBoostingClassifier`.
- **Untethered Android Polling**: Persistent native OS workers bypassing strict Android Doze cycles. Utilizing `termux-api` they poll battery, movement, and notification data blindly transmitting to the web architecture before activating localized mp3 alarms!
- **Wireless ADB Auto-Injection**: A single robust `deploy_adb.sh` shell script leveraging native Android Debug Bridge features unlocking user screens natively, establishing file paths, and actively "typing" the initial Termux launch sequences!

## Documentation
For deep-dives into executing the `sqlite3` layout patterns or setting up your localized Termux configurations seamlessly onto hardware, head towards the `docs/` hierarchy:
- [System Architecture Breakdown](./docs/ARCHITECTURE.md)
- [Railway & Termux User Guide](./docs/GUIDE.md)

## Quick Start
1. Edit the API token string alongside `server/.env`.
2. Push your localized repository into GitHub binding it onto Railway. Nixpacks will utilize `railway.json` spinning internal Python instances perfectly!
3. Evaluate your own sleep patterns compiling `train/Train.ipynb` and deploy the output binary file towards `server/src/ml/sleep_model.pkl`.
4. Spin up Termux natively on your Android device and execute `bash termux/deploy_adb.sh` over your workstation resolving all app deployment mechanics dynamically!
