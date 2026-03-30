# SmartWake — Database Map

SQLite file: `db/smartwake.db` (local dev) · `/data/smartwake.db` (Railway volume)

---

## Table: `logs`

Every telemetry ping sent by the phone via `POST /logs/raw.log`.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | INTEGER PK | NO | Auto-incremented row ID |
| `device_id` | TEXT | NO | Unique phone identifier (min length 1) |
| `timestamp` | TEXT | NO | ISO-8601 datetime of the reading (sent by phone) |
| `charging` | BOOLEAN | NO | Whether the phone was on charge at ping time |
| `battery_level` | INTEGER | NO | Battery % — constrained 0–100 |
| `accel_x` | REAL | NO | Raw accelerometer X axis (m/s²) |
| `accel_y` | REAL | NO | Raw accelerometer Y axis (m/s²) |
| `accel_z` | REAL | NO | Raw accelerometer Z axis (m/s²) |
| `accel_magnitude` | REAL | NO | Derived: `sqrt(x²+y²+z²)` — computed server-side |
| `notification_count` | INTEGER | NO | Running notification count from phone — constrained ≥ 0 |
| `hour` | INTEGER | NO | Hour extracted from `timestamp` (0–23) |
| `minute` | INTEGER | NO | Minute extracted from `timestamp` (0–59) |
| `sleep_prob` | REAL | YES | ML output: probability of sleep (0.0–1.0) — written after inference |
| `created_at` | TIMESTAMP | NO | Server-side wall clock when the row was inserted |

**Notes**
- `sleep_prob` starts as `NULL` and is back-filled with `UPDATE` after the feature vector is computed.
- `hour` and `minute` are stored denormalized so the feature builder avoids re-parsing ISO strings.
- The last 6 rows per `device_id` (ordered by `id DESC`) are used as the ML sliding window.

---

## Table: `sleep_sessions`

One row per **confirmed sleep onset** detected by the state machine.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | INTEGER PK | NO | Auto-incremented row ID |
| `device_id` | TEXT | NO | Phone that triggered this session |
| `onset_time` | TEXT | YES | ISO-8601 timestamp when sleep was first confirmed |
| `wake_deadline` | TEXT | YES | User's desired latest wake time — copied from `device_registry` at alarm schedule time |
| `alarm_time` | TEXT | YES | Computed optimal wake alarm — nearest 90-min cycle boundary before `wake_deadline` |
| `alarm_fired` | BOOLEAN | NO | Reserved for future use — defaults `0` (not yet set by any route) |
| `quality_rating` | INTEGER | YES | 1–5 star rating submitted by user via `POST /rating` after waking |
| `cycle_count` | INTEGER | YES | Reserved — number of sleep cycles completed (not yet computed) |
| `created_at` | TIMESTAMP | NO | Server-side wall clock when the session row was inserted |

**Notes**
- A row is inserted the moment the state machine transitions to `CONFIRMED` (2 consecutive pings ≥ 0.75).
- `alarm_time` is populated immediately after insert by `schedule_alarm()`.
- The session resets after `alarm_time` (or `wake_deadline`) passes — the next ping starts a fresh session.
- `GET /dashboard` returns the most recent session for a device.
- `POST /rating` updates `quality_rating` on the most recent session by `id DESC`.

---

## Table: `device_registry`

One row per phone. Stores the desired wake deadline so the alarm scheduler can look it up.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | INTEGER PK | NO | Auto-incremented row ID |
| `device_id` | TEXT UNIQUE | NO | Phone identifier — unique constraint, one row per device |
| `wake_deadline` | TEXT | YES | ISO-8601 datetime: when the user needs to be up by |
| `registered_at` | TIMESTAMP | NO | Last time `POST /wake-time` was called for this device |

**Notes**
- Written/updated by `POST /wake-time` — uses `INSERT OR REPLACE` semantics (`ON CONFLICT DO UPDATE`).
- Read by `schedule_alarm()` each time a sleep onset is confirmed.
- If `wake_deadline` is `NULL` (device registered but no deadline set), alarm scheduling is skipped.

---

## Data Flow Summary

```
POST /wake-time
  └─► device_registry (upsert wake_deadline)

POST /logs/raw.log
  ├─► logs INSERT (raw telemetry + derived accel_magnitude)
  ├─► logs SELECT last 6 rows → build feature vector
  ├─► ML inference → sleep_prob
  ├─► logs UPDATE (write sleep_prob back)
  └─► Onset state machine
        └─ CONFIRMED ──► sleep_sessions INSERT (onset_time)
                    └──► schedule_alarm()
                              ├─ device_registry SELECT (wake_deadline)
                              └─ sleep_sessions UPDATE (alarm_time)

POST /rating
  └─► sleep_sessions UPDATE (quality_rating on latest session)

GET /dashboard
  ├─► sleep_sessions SELECT latest 1
  └─► logs SELECT latest 48
```
