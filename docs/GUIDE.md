# SmartWake User Guide

Follow these steps precisely to set up and deploy the SmartWake Smart Alarm system end-to-end.

## Phase 1: Train The Model
You must assemble your personalized sleep model matching the exact specifications expected by the Server's feature vector mapping.
1. Log into Google Colab.
2. Upload the `train/Train.ipynb` notebook.
3. Supply your `kaggle.json` into Google Drive for the Fitbit dataset auth step.
4. Run all cells chronologically. Do not change any feature calculation methods. 
5. The notebook will download `sleep_model.pkl`.
6. Local runtime path: copy `sleep_model.pkl` to `server/src/model/sleep_model.pkl`. Inside the deployed `server/` service, the matching runtime path is `src/model/sleep_model.pkl`.

## Phase 2: Deploy To Railway
The Cloud API handles processing Termux device arrays seamlessly.
1. Run `git init` within the `server/` root. Add all files and commit.
2. Push your localized repository towards an active GitHub Project.
3. Inside your Railway Dashboard, spin up a new service targeting your GitHub Repo.
4. Railway will consume `railway.json` and start `gunicorn main:app` with Uvicorn workers on `$PORT`.
5. Under your Railway variables panel explicitly set:
   *   `API_KEY=your-shared-secret`
   *   `DB_PATH=smartwake.db`
   *   `MODEL_PATH=src/model/sleep_model.pkl`
   *   `BASE_URL=https://your-public-domain.up.railway.app` *(recommended for consistent `/install` responses behind Railway proxies)*
6. Identify your Railway Public Route (e.g. `https://smartwake-production.up.railway.app`). Validate success by navigating towards `/health`.

## Phase 3: Prepare Android Phone
You must utilize an Android phone loaded with F-Droid's Termux app. (Play Store versions are restricted!).
1. Download Termux and Termux:API exactly out of F-Droid.
2. Open Termux on the phone and bootstrap the workers:
    ```bash
    curl -sL https://your-domain/install | bash
    ```
3. If your server uses a custom `API_KEY`, export it before starting the workers:
    ```bash
    export SMARTWAKE_API_KEY=your-shared-secret
    ```
4. Place your wake sound at `/sdcard/alarm.mp3`.
5. Start the workers:
    ```bash
    cd ~/smartwake && bash start.sh
    ```

## Phase 4: Activation
Execute the system securely.
1. `start.sh` acquires a wake lock, checks `/health`, then starts `logger.py` and `alarm.py`.
2. Keep the Termux notification alive while you sleep so Android does not stop the workers.
3. First-run will build a `device_id.txt` file automatically.
4. Optionally open `/dashboard?device_id=...` and `/alarm-status?device_id=...` to confirm logs and alarm state are updating.

Your intelligent alarm is now active!
