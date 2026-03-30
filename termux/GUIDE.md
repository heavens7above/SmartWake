# Termux Worker Setup Guide

Deploy SmartWake onto your Android phone with a single command — no USB cable, no ADB, no manual file editing necessary.

---

## Quick Setup (The One-Liner)

**1. Install Termux from F-Droid** (do **not** use Google Play Store — it's outdated):
> https://f-droid.org/en/packages/com.termux/

Also install the companion app **Termux:API**:
> https://f-droid.org/en/packages/com.termux.api/

**2. Open Termux on your phone and run:**

```bash
curl -sL https://smartwake.up.railway.app/install | bash
```

<!-- CODEX-FIX: Clarify that only the host in the sample command changes because the install route already injects the rest of the config. -->
> Replace only the domain in the sample command with your actual Railway deployment URL.

That single command will automatically:
- Update Termux package repositories
- Install Python and the Termux-API drivers
- Install `requests` and `schedule` Python packages
- Download `logger.py`, `alarm.py`, and `start.sh` into `~/smartwake/`
- Inject your server's URL into the scripts — **no manual editing needed**

---

## Grant Sensor & Storage Permissions

During setup, a popup will appear asking for storage permission — **tap Allow**.

For some Android versions, you may also need to grant:
- `Physical Activity` or `Body Sensors` — via Android Settings → Apps → Termux → Permissions

---

## One-Time Device Prep

Place your chosen MP3 alarm file in your phone's internal storage root and name it:

```
/sdcard/alarm.mp3
```

---

## Start Monitoring

After setup completes, begin the SmartWake monitoring loop:

```bash
cd ~/smartwake && bash start.sh
```

This will:
- Bind a **wake lock** so Android doesn't kill the process when you lock your screen
- Run `logger.py` in the background — posts a telemetry vector every 5 minutes
- Run `alarm.py` in the background — polls the server for scheduled alarm events

Leave the Termux notification in your tray and go to bed! 🌙

---

## Updating the Phone Client

Updating is just as easy — re-run the same install command to pull the latest scripts from the server:

```bash
curl -sL https://smartwake.up.railway.app/install | bash
```

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `curl: not found` | Run `pkg install curl` first |
| Sensor reads returning `0.0` | Check Body Sensors permission in Android Settings → Apps → Termux |
| `alarm.mp3 not found` | Ensure the file is at exactly `/sdcard/alarm.mp3` |
| `connection refused` on logger | Verify your Railway server is live and URL is correct |
