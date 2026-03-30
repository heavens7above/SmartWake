# 🌩️ Railway Production Deployment Guide

Your backend is structurally finalized and perfectly primed for live-fire hosting. This document outlines exactly how to configure the physical container blocks within [Railway.app](https://railway.app) to ensure persistence across your sleep configurations!

## Deployment Foundations
I have explicitly generated two foundational blueprints mapped inside the `server/` directory:
1. **`nixpacks.toml`**: The native Railway compiler mapping securing Python 3.11 bindings, bypassing generic pipelines to upgrade PIP logic securely.
2. **`Dockerfile`**: A raw container blueprint serving as an unyielding fallback option granting you pure control over memory environments (`PYTHONUNBUFFERED=1`).

Railway will automatically detect these bindings natively the moment you initialize the repository!

---

## 🛠 Step 1: Push & Build
1. Push your entire repository to GitHub. 
2. Open the Railway Dashboard, select **"New Project"**, and pick **"Deploy from GitHub repo"**. 
3. Choose your `SmartWake` repository.
4. **Context Directory:** Before executing the deployment, head into settings, find **Root Directory**, and forcefully change it to `/server`. Because the root contains `termux/` and `/train`, compiling from the exact `/server` directory prevents massive build timeouts! 

## ⚖️ Step 2: Global Environment Variables
Inside your Railway Container **Variables** tab, you must manually inject your Zero-Trust locks!
<!-- CODEX-FIX: Replace the committed example secret with a generated value because the server now requires an explicit environment key. -->
- `API_KEY` = `generate-a-random-secret-and-reuse-it-in-your-clients` *(Required. Set your own value and keep the same one in the app/Termux settings.)* 
- `PORT` = `8000` *(Usually auto-assigned by Railway, but enforcing it ensures absolute connectivity)*

## 🧱 Step 3: SQLite Persistent Volume
Railway operates onto **Ephemeral Drives** meaning every time you redeploy or the server goes to sleep, the physical files inside the container are vaporized. To prevent all your registered internal `sleep_sessions` from erasing:

1. Click on your active service container in Railway. 
2. Navigate to the **Storage** or **Volumes** parameter. 
3. Select **Add Volume**, and assign a **Mount Path** mapping exactly to `/app/db`. 
4. Head back to your **Variables** tab, and explicitly set:
   - `DB_PATH` = `/app/db/smartwake.db`

Now, anytime Uvicorn writes the SQLite transaction logs natively, they are dropped into a protected physical disk partition that survives server restarts! Your backend is now invincible!
