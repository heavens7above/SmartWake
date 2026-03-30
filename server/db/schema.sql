CREATE TABLE IF NOT EXISTS logs (
    id                  SERIAL PRIMARY KEY,
    device_id           TEXT NOT NULL,
    timestamp           TEXT NOT NULL,
    charging            BOOLEAN NOT NULL,
    battery_level       INTEGER NOT NULL,
    accel_x             REAL NOT NULL,
    accel_y             REAL NOT NULL,
    accel_z             REAL NOT NULL,
    accel_magnitude     REAL NOT NULL,
    notification_count  INTEGER NOT NULL,
    hour                INTEGER NOT NULL,
    minute              INTEGER NOT NULL,
    sleep_prob          REAL,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sleep_sessions (
    id              SERIAL PRIMARY KEY,
    device_id       TEXT NOT NULL,
    onset_time      TEXT,
    wake_deadline   TEXT,
    alarm_time      TEXT,
    alarm_fired     BOOLEAN DEFAULT FALSE,
    quality_rating  INTEGER,
    cycle_count     INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS device_registry (
    id              SERIAL PRIMARY KEY,
    device_id       TEXT NOT NULL UNIQUE,
    wake_deadline   TEXT,
    registered_at   TIMESTAMPTZ DEFAULT NOW()
);
