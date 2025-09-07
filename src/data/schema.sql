PRAGMA foreign_keys = ON;

CREATE TABLE bookings (
  booking_id     TEXT PRIMARY KEY,
  route_from     TEXT NOT NULL,
  route_to       TEXT NOT NULL,
  depart_time    TEXT NOT NULL,      -- ISO8601, ví dụ '2025-09-05T20:00:00'
  status         TEXT NOT NULL CHECK (status IN ('PAID','CANCELLED','USED','REFUNDED')),
  seat_class     TEXT NOT NULL,
  user_phone     TEXT
);

CREATE TABLE trips (
  trip_id        TEXT PRIMARY KEY,
  route_from     TEXT NOT NULL,
  route_to       TEXT NOT NULL,
  depart_time    TEXT NOT NULL,      -- ISO8601
  seats_total    INTEGER NOT NULL,
  seats_available INTEGER NOT NULL,
  base_price     INTEGER NOT NULL
);

CREATE TABLE booking_changes (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  booking_id    TEXT NOT NULL REFERENCES bookings(booking_id) ON DELETE CASCADE,
  old_time      TEXT NOT NULL,
  new_time      TEXT NOT NULL,
  fee           INTEGER NOT NULL,
  created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE complaints (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  booking_id    TEXT NOT NULL REFERENCES bookings(booking_id) ON DELETE CASCADE,
  complaint_type TEXT NOT NULL CHECK (complaint_type IN ('SERVICE','REFUND','CANCELLATION','OTHER')),
  description   TEXT NOT NULL,
  status        TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','IN_PROGRESS','RESOLVED','CLOSED')),
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  resolved_at   TEXT
);

-- Chạy candidates nhanh theo tuyến + ngày
CREATE INDEX idx_trips_route_date
ON trips(route_from, route_to, substr(depart_time, 1, 10)); -- YYYY-MM-DD
