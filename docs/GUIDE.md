# SmartWake User Guide

Follow these steps precisely to set up and deploy the SmartWake Smart Alarm system end-to-end.

## Phase 1: Train The Model
You must assemble your personalized sleep model matching the exact specifications expected by the Server's feature vector mapping.
1. Log into Google Colab.
2. Upload the `train/Train.ipynb` notebook.
3. Supply your `kaggle.json` into Google Drive for the Fitbit dataset auth step.
4. Run all cells chronologically. Do not change any feature calculation methods. 
5. The notebook will download `sleep_model.pkl`.
<!-- CODEX-FIX: Correct the model directory so deployment instructions match the path searched by the server. -->
6. Copy `sleep_model.pkl` to the `server/src/model/` folder in your workspace so the server can load it into memory.

## Phase 2: Deploy To Railway
The Cloud API handles processing Termux device arrays seamlessly.
1. Run `git init` within the `server/` root. Add all files and commit.
2. Push your localized repository towards an active GitHub Project.
3. Inside your Railway Dashboard, spin up a new service targeting your GitHub Repo.
4. Railway will consume the `railway.json` file configuring the NIXPACKS build system accurately recognizing the python specifications, and spinning `uvicorn` out across `$PORT`.
5. Under your Railway variables panel explicitly set:
   *   `DB_PATH=smartwake.db`
<!-- CODEX-FIX: Correct the configured model path so Railway points at the committed model directory. -->
   *   `MODEL_PATH=src/model/sleep_model.pkl`
6. Identify your Railway Public Route (e.g. `https://smartwake-production.up.railway.app`). Validate success by navigating towards `/health`.

## Phase 3: Prepare Android Phone
You must utilize an Android phone loaded with F-Droid's Termux app. (Play Store versions are restricted!).
1. Download Termux and Termux:API exactly out of F-Droid.
2. Open Termux on the phone and run the critical setup lines:
    ```bash
    pkg update && pkg upgrade
    pkg install python termux-api
    pip install requests schedule
    ```
3. Grant permissions by running `termux-setup-storage`. Accept the pop-up requests.
4. Transfer the contents of the `termux/` folder (which includes `logger.py`, `alarm.py`, `start.sh`) into Termux native storage limits. 
5. Inside `termux/logger.py` and `termux/alarm.py`, locate the `SERVER_URL` parameter and update it specifically with your new generalized Railway URL.

## Phase 4: Activation
Execute the system securely.
1. On your phone inside the deployed folder run: `bash start.sh`
2. Keep the app open (or pull down notification shade verifying the Wake lock is holding CPU alive).
3. First-run will build a `device_id.txt` file automatically.
4. Optionally hit the `/dashboard` route pointing the `?device_id=` param towards the newly created UUID checking if logs populate reliably. 

Your intelligent alarm is now active!
