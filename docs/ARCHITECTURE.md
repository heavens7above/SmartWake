# SmartWake Architecture

Welcome to the SmartWake Sleep Intelligence Architecture Overview. This system is structured into three distinct layers functioning synchronously to predict sleep onset and calculate biologically optimal alarm schedules.

## 1. Cloud Intelligence Engine (FastAPI Server)

The `server/` directory runs the centralized intelligence platform powering all device clients. Hosted on Railway via NIXPACKS, the server exposesREST endpoints evaluating every incoming device ping against our deployed machine-learning matrix.

### Moduled Architecture (`server/src/modules/`):
The intelligence codebase operates beneath a highly compressed modular layout entirely driven utilizing exactly 4 files:
<!-- CODEX-FIX: Update the documented ingestion route to the live endpoint exposed by the server. -->
- **`sleep.py`**: The ingestion `/logs/raw.log` API endpoint. Scikit-learn singletons evaluating dictionaries against `sleep_model.pkl`. The 9-dimension Zero-Crossing array math mechanics, and the consecutive Onset-Tracking state machine all neatly tied natively in one wrapper.
- **`alarms.py`**: Calculates backwards constraints jumping 90-minute REM cycles. The dynamic `/wake-time` endpoints link backward scheduling physiological thresholds natively parsing SQLite bindings.
- **`dashboards.py`**: Read-only `/dashboard` visual mapping and the specific `/rating` API schemas decoupled perfectly into their own UI-rendering logic chunks.
- **`shared.py`**: Globals extending the environment map. Core explicit `sqlite3` execution chains, all static base Pydantic schemas protecting route dependencies, and pure cyclic mathematics encapsulating hour boundaries!

### Database Structure (SQLite)
The application relies strictly on Python's built in driver `sqlite3` without complex ORM layers for minimal overhead.
*   **`logs`**: Appends the 5-minute payload pings mapping exact motion arrays alongside battery conditions and the output evaluation of `sleep_prob`.
*   **`sleep_sessions`**: Single overarching nightly entity for a `device_id`. Generates on Sleep Onset confirmation and stores the resulting calculated Wake times.
*   **`device_registry`**: Unique mapping index pairing a UUID to the user's hard upper-bound temporal wake constraints.

---

## 2. Phone Telemetry Workers (Termux Android)

The client environment avoids complex JVM Android Studio dependencies by driving simple backgrounded polling scripts directly atop the OS utilizing `termux-api`.

<!-- CODEX-FIX: Update the worker description so the documented telemetry route matches the actual logger implementation. -->
- **`logger.py`**: A non-blocking thread utilizing `schedule.every(5).minutes`. Polls native Android sensors sequentially (Accelerometer, Battery broadcast receivers, active Notification tray count). POSTs the resultant payload array blindly to our `/logs/raw.log` socket over HTTPs.
- **`alarm.py`**: Checks `/alarm-status?device_id=...` periodically. Upon crossing the scheduled threshold, utilizes Termux's media player, vibration module, and Heads-Up notification API to trigger the wakeup locally without requiring Cloud-To-Device push notifications.
- **`start.sh`**: Binds a CPU Wake Lock keeping Termux alive over Android Doze restrictions, then multiplexes both pythons scripts over background threads simultaneously.

---

## 3. Data Science Training (Google Colab)

A self-contained notebook (`train/Train.ipynb`) capable of generating the `sleep_model.pkl`.
- Mounts Kaggle pipelines retrieving the `Fitabase` minute-by-minute sleep evaluation sets.
- Emulates the phone's 5-minute ping interval by performing `.resample('5T')` groupings.
- Accurately tracks `zero_crossing_rate` aggregations over mean-centered magnitudes emulating motion thresholds. 
- Utilizes Cyclical encoding mapping Hour and Minute identifiers into spatial `sin` / `cos` arrays guarding against the 23:59 -> 00:00 numeric gap.
- Solves categorical imbalance of 'Asleep' vs 'Awake' minute ratios utilizing a Gradient Boosting Trees algorithm paired closely with Class Weights logic.
