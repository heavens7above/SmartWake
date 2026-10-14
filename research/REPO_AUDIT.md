# SmartWake Repository Technical Audit (Phase 0)

**Audit Date:** 2026-10-14  
**Target Repository:** `heavens7above/SmartWake`  
**Auditor:** Autonomous Research Engineer  
**Branch:** `research/paper`  

---

## 1. Executive Summary

A comprehensive architectural and line-by-line code audit of the SmartWake repository was conducted to verify system claims, evaluate data flow integrity, inspect feature engineering and model pipelines, and determine the empirical boundary of what the codebase can support. 

The audit reveals significant divergence between the informal initial hypothesis ("a GradientBoostingClassifier decides when the user is in a light-sleep or wake-ready state") and the actual codebase implementation:
1. **Model Function:** The deployed `GradientBoostingClassifier` is a **Sleep Onset Detector** (binary: $y \in \{0, 1\}$ for awake vs. asleep), **not** an in-bed sleep stage or light-sleep classifier.
2. **Alarm Scheduling Logic:** Morning wake timing is calculated deterministically via an **ultradian 90-minute forward-stepping cycle algorithm** anchored to the confirmed sleep onset timestamp:
   $$\text{Wake Time} = t_{\text{onset}} + k \times 90\,\text{min}$$
   subject to the user's hard deadline constraint ($t_{\text{deadline}} - \text{Wake Time} \ge 15\,\text{min}$).
3. **Telemetry Polling Model:** The Termux Android client does **not** stream high-frequency raw continuous waveform telemetry; it executes a periodic discrete poll every 5 minutes (`schedule.every(5).minutes`), taking a single snapshot (`-n 1`) of triaxial acceleration, battery charging state, and notification count.
4. **Database Engine:** Despite legacy documentation referencing SQLite, the production server uses **PostgreSQL** via `psycopg2` with threaded connection pooling.
5. **Training Data and Label Source:** The model was trained in `train/Train.ipynb` using the open `arashnic/fitbit` dataset (Fitabase minute-level telemetry), where labels originate from a proprietary consumer wearable heuristic, **not** clinical polysomnography (PSG).

---

## 2. System Architecture & Component Mapping

SmartWake is structured into three primary tiers: client-side telemetry collection, cloud inference & decision orchestration, and offline machine learning training.

```
+-----------------------------------------------------------------------------------------+
|                                    1. CLIENT TIER                                       |
|                                                                                         |
|  [Android Device running Termux]                      [Flutter SmartWakeApp]            |
|  - logger.py: polls sensors every 5 min               - lib/screens/shell_screen.dart   |
|    * Accelerometer (-n 1 snapshot)                    - lib/services/monitor_service.dart|
|    * Battery status (level, charging)                 - lib/services/api_service.dart   |
|    * Notification count                               - UI for setting wake deadlines   |
|  - alarm.py: polls /alarm-status every 60 s                                             |
|    * Fires local media/vibration when due                                               |
+--------------------------------------------+--------------------------------------------+
                                             | HTTP POST /logs/raw.log (Header: X-API-Key)
                                             | HTTP GET /alarm-status
                                             v
+-----------------------------------------------------------------------------------------+
|                                2. BACKEND SERVER TIER                                   |
|                                                                                         |
|  [FastAPI Engine - server/main.py]                                                      |
|  - server/src/modules/sleep.py:                                                         |
|    * Ingestion: _insert_log_and_fetch_history() (buffers last 6 pings)                  |
|    * Features: build_feature_vector() (9-dimensional vector)                            |
|    * Inference: predict() via loaded GradientBoostingClassifier                         |
|    * State Machine: process_log() -> 2 consecutive pings >= 0.75 confirms Onset         |
|  - server/src/modules/alarms.py:                                                        |
|    * calculate_alarm(): computes onset + k * 90 min <= deadline                         |
|    * /wake-ack: acknowledges local alarm firing                                         |
|  - server/src/modules/dashboards.py: /dashboard, /rating                                |
|  - Database: PostgreSQL (schema.sql: logs, sleep_sessions, device_registry)            |
+-----------------------------------------------------------------------------------------+
                                             ^
                                             | Offline Artifact: sleep_model.pkl
+-----------------------------------------------------------------------------------------+
|                             3. TRAINING & DATA SCIENCE TIER                             |
|                                                                                         |
|  [train/Train.ipynb & train/GUIDE.md]                                                   |
|  - Source Data: Kaggle arashnic/fitbit (Fitabase minuteIntensities & minuteSleep)       |
|  - Aggregation: Resampled into 5-minute temporal epochs                                 |
|  - Algorithm: GradientBoostingClassifier(n_estimators=200, max_depth=4, lr=0.1)        |
|  - Class Weighting: compute_sample_weight('balanced', y_train)                          |
+-----------------------------------------------------------------------------------------+
```

### File Paths and Line References

| Component | File Path | Line Range | Functional Role |
| :--- | :--- | :--- | :--- |
| **Telemetry Logger** | `termux/logger.py` | L38–47 | Queries `termux-battery-status` for charging flag and battery percentage. |
| **Telemetry Logger** | `termux/logger.py` | L49–73 | Captures 1-sample acceleration `(x, y, z)` via `termux-sensor -s Accelerometer -n 1`. |
| **Telemetry Logger** | `termux/logger.py` | L74–80 | Reads active notification tray count via `termux-notification-list`. |
| **Telemetry Logger** | `termux/logger.py` | L82–105 | Assembles payload and executes HTTP POST to `/logs/raw.log` with `X-API-Key`. |
| **Alarm Client** | `termux/alarm.py` | L61–96 | Polls `/alarm-status?device_id=...` every 60s; triggers audio/vibration upon due time. |
| **Alarm Client** | `termux/alarm.py` | L47–60 | Dispatches HTTP POST to `/wake-ack` upon local alarm trigger. |
| **FastAPI Root** | `server/main.py` | L14–22 | Implements API Key verification (`X-API-Key` header dependency). |
| **FastAPI Lifespan** | `server/main.py` | L38–49 | Initialises connection pool (`shared.init_pool()`) and table schema (`shared.init_db()`). |
| **Feature Extraction** | `server/src/modules/sleep.py` | L142–185 | Computes 9 features across rolling 6-row history buffer. |
| **Model Inference** | `server/src/modules/sleep.py` | L117–139 | Executes `model.predict_proba()` extracting probability of positive sleep class ($p_1$). |
| **Onset State Machine**| `server/src/modules/sleep.py` | L263–308 | Enforces 2 consecutive pings with $p \ge 0.75$ before confirming sleep onset. |
| **Alarm Mathematics** | `server/src/modules/alarms.py` | L18–33 | Implements 90-minute ultradian backward/forward cycle calculation relative to deadline. |
| **Database Pool** | `server/src/modules/shared.py` | L156–175 | Manages `ThreadedConnectionPool` (1 to 20 connections) to PostgreSQL. |
| **Database Schema** | `server/db/schema.sql` | L1–36 | Defines tables `logs`, `sleep_sessions`, and `device_registry`. |

---

## 3. Telemetry Collection Mechanics

* **Sensors Polled:** 
  1. Triaxial Accelerometer: axes $a_x, a_y, a_z$ in $\text{m/s}^2$.
  2. Battery Subsystem: charging status (boolean) and state-of-charge percentage ($0 \dots 100$).
  3. Notification Manager: active status-bar notification count (integer).
* **Sampling Rate & Windowing:**
  - The client polls once every 300 seconds (5 minutes).
  - Each poll reads an instantaneous reading (`-n 1`).
  - The server collects these discrete entries in the database and retrieves the most recent 6 entries (`ORDER BY id DESC LIMIT 6`, inverted to chronological order) to form a rolling window of up to 30 minutes.
* **Payload Schema (`LogPayload` in `server/src/modules/shared.py`):**
  ```json
  {
    "device_id": "UUID-string",
    "timestamp": "ISO-8601 UTC string",
    "charging": true,
    "battery_level": 85,
    "accel_x": 0.05,
    "accel_y": 0.12,
    "accel_z": 9.81,
    "notification_count": 3
  }
  ```

---

## 4. Feature Engineering Pipeline

The server's `build_feature_vector()` function (`server/src/modules/sleep.py:L142-185`) extracts exactly 9 features from the rolling window:

1. **`accel_magnitude_mean`**: Arithmetic mean of Euclidean magnitudes $m_i = \sqrt{a_{x,i}^2 + a_{y,i}^2 + a_{z,i}^2}$.
2. **`accel_magnitude_std`**: Sample standard deviation of Euclidean magnitudes across the window.
3. **`accel_magnitude_max`**: Maximum magnitude recorded in the window.
4. **`zero_crossing_rate`**: Frequency of sign changes in mean-centered acceleration magnitude:
   $$\text{ZCR} = \frac{1}{N} \sum_{i=1}^{N-1} \mathbb{I}\left[\operatorname{sgn}(m_{i+1} - \bar{m}) \neq \operatorname{sgn}(m_i - \bar{m})\right]$$
5. **`notification_delta`**: Difference between the latest notification count and the oldest in the window ($C_{\text{latest}} - C_{\text{oldest}}$).
6. **`consecutive_still_count`**: Number of consecutive pings at the end of the window where $m_i < 0.05$.
7. **`charging`**: Binary flag indicating whether the device was plugged into power at the most recent ping (1 if True, 0 if False).
8. **`hour_sin`**: $\sin(2\pi \cdot t_{\text{min}} / 1440)$ where $t_{\text{min}} = 60 \cdot \text{hour} + \text{minute}$.
9. **`hour_cos`**: $\cos(2\pi \cdot t_{\text{min}} / 1440)$.

### Critical Observations on Feature Design:
- **Circadian Bias:** Features 8 and 9 dominate model behavior. Inspection of the pre-trained `sleep_model.pkl` reveals `hour_sin` (46.5%) and `hour_cos` (40.8%) account for **87.3%** of overall split importance.
- **Offline Training Disconnect:** In `train/Train.ipynb:L122-124`, `notification_delta` and `charging` were hardcoded to `0` during offline training on the Fitbit dataset. Consequently, their feature importances in `sleep_model.pkl` are **exactly 0.0**. The live server extracts values that the trained model has never learned to utilize.
- **Stillness Threshold:** The condition $m_i < 0.05$ assumes dynamic acceleration (gravity-removed), but raw phone accelerometer readings include gravity ($|\mathbf{a}| \approx 9.8\,\text{m/s}^2$). Unless gravity is subtracted, `consecutive_still_count` evaluates to 0.

---

## 5. Ground Truth, Labels, and Circularity Analysis

### Label Provenance
- In `train/Train.ipynb`, labels are obtained by merging `minuteIntensitiesNarrow_merged.csv` and `minuteSleep_merged.csv` from Kaggle's `arashnic/fitbit` dataset.
- The raw `value` field from Fitbit logs sleep status as:
  - `1`: Asleep
  - `2`: Restless
  - `3`: Awake
- The training script maps this to binary:
  $$\text{is\_asleep} = \begin{cases} 1, & \text{if } \text{value} == 1 \\ 0, & \text{otherwise} \end{cases}$$
- For each 5-minute epoch, the aggregate label is:
  $$\text{label} = \begin{cases} 1, & \text{if } \operatorname{median}(\text{is\_asleep}) > 0.5 \\ 0, & \text{otherwise} \end{cases}$$

### Clinical Validity Assessment
- **Category:** The labels fall under category **(b) - Consumer wearable heuristic**.
- **Circularity Risk:** Fitbit derives sleep/wake classifications using proprietary motion and optical heart rate thresholding algorithms. Using these labels to train an accelerometer model creates a surrogate approximation of Fitbit's proprietary heuristic rather than ground-truth human neurophysiology.
- **Absence of Sleep Staging:** The repository does **not** train on or predict N1, N2, N3 (slow-wave), or REM sleep stages. Claims that the system "detects REM-free wake cycles" stem solely from the deterministic 90-minute assumption in `alarms.py`, not machine learning classification of sleep stages.

---

## 6. Model Specification and Alarm Decision Rule

### Trained Artifact Specification (`train/model/sleep_model.pkl` and `server/src/model/sleep_model.pkl`)
- **Algorithm:** `sklearn.ensemble.GradientBoostingClassifier`
- **Hyperparameters:**
  - `n_estimators`: 200
  - `max_depth`: 4
  - `learning_rate`: 0.1
  - `loss`: `'log_loss'`
  - `random_state`: 42
  - `subsample`: 1.0
  - `sample_weight`: `'balanced'` (via `compute_sample_weight`)
- **Number of Input Features:** 9
- **Classes:** `[0, 1]`

### Alarm Scheduling Rule (`server/src/modules/alarms.py:L18-33`)
```python
def calculate_alarm(onset_time: str, wake_deadline: str, cycle_minutes: int = 90) -> str:
    onset = normalize_datetime(datetime.fromisoformat(onset_time))
    deadline = normalize_datetime(datetime.fromisoformat(wake_deadline))
    if deadline <= onset:
        return deadline.isoformat()
    total_minutes = (deadline - onset).total_seconds() / 60.0
    cycles = int(total_minutes // cycle_minutes)
    if cycles <= 0:
        return deadline.isoformat()
    ideal_wake = onset + timedelta(minutes=cycles * cycle_minutes)
    gap_minutes = (deadline - ideal_wake).total_seconds() / 60.0
    return deadline.isoformat() if gap_minutes < 15 else ideal_wake.isoformat()
```
- **Fallback Mechanism:** If the duration between $t_{\text{onset}}$ and $t_{\text{deadline}}$ does not permit a full 90-minute cycle, or if the remaining gap between the last complete cycle and the hard deadline is under 15 minutes, the alarm falls back to $t_{\text{deadline}}$.
- **Client Offline Resilience:** The Termux alarm script (`termux/alarm.py`) queries the server periodically. If the network drops after the alarm time is registered, the local script retains `last_fired_alarm_time` but requires an active server ping to learn scheduled times.

---

## 7. Audit Findings and Limitations

1. **Absence of Real In-Repo Night Recordings:** The `train/dataset/` directory contains no raw session CSVs. The repository relies entirely on the pre-trained `sleep_model.pkl` and instructions in `train/GUIDE.md` to download external Kaggle data.
2. **Feature Mismatch Between Training and Deployment:** Training data features wrist-intensity counts ($0 \dots 3$), while live deployment feeds triaxial accelerometer magnitudes ($m/s^2$) and notification counts.
3. **Database Misalignment in Documentation:** `docs/ARCHITECTURE.md` states SQLite is used, while `server/src/modules/shared.py` implements PostgreSQL (`psycopg2`).
4. **Circularity in Sleep Staging Claims:** The system uses ML for sleep *onset* detection, but sleep *cycles* and *wake timing* rely strictly on an uncalibrated 90-minute fixed constant.
