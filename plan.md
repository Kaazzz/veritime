# School RFID Attendance System — Implementation Plan

## Project Overview

A real-time school RFID attendance system using Arduino, Python, SQLite, and a browser-based dashboard. The system reads RFID card taps from an Arduino over serial, logs them to a local SQLite database, and pushes live updates to a web dashboard via WebSockets.

---

## Tech Stack

| Layer | Tool | Why |
|---|---|---|
| Database | SQLite | Zero-install, single file, built into Python |
| Backend | Python + Flask | Lightweight, easy serial + web server combo |
| Real-time | Flask-SocketIO | Pushes scan events to browser instantly via WebSocket |
| Serial reader | PySerial | Reads Arduino COM port on Windows |
| Frontend | HTML + CSS + JS | Single-file dashboard, no framework needed |

---

## Architecture

```
Arduino (COM port)
      │  serial data (CSV: UID,STATUS)
      ▼
Python Serial Reader  ──► SQLite DB (scan_logs + students)
      │
      │  SocketIO event emit
      ▼
Flask Web Server  ──►  Browser Dashboard (real-time)
```

The Python app does three things concurrently: reads the serial port, writes to SQLite, and broadcasts scan events to any open browser tab — no page refresh needed.

---

## File Structure

```
school-rfid/
├── app.py              ← Flask server + SocketIO + serial thread
├── database.py         ← SQLite setup and query helpers
├── requirements.txt    ← pyserial, flask, flask-socketio, eventlet
├── school.db           ← SQLite database (auto-created on first run)
├── static/
│   ├── style.css
│   └── uploads/        ← student photos
└── templates/
    ├── index.html      ← live dashboard
    ├── students.html   ← student management
    └── logs.html       ← scan history
```

---

## Database Schema

### `students` table
```sql
CREATE TABLE students (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    rfid_uid    TEXT UNIQUE NOT NULL,
    lrn         TEXT,
    name        TEXT NOT NULL,
    grade       TEXT,
    section     TEXT,
    photo_path  TEXT
);
```

### `scan_logs` table
```sql
CREATE TABLE scan_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    rfid_uid    TEXT NOT NULL,
    student_id  INTEGER REFERENCES students(id),  -- nullable if card is unknown
    timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
    status      TEXT CHECK(status IN ('On Time', 'Late')) NOT NULL
);
```

---

## Arduino Serial Output Format

Remove all PLX-DAQ headers (`CLEARDATA`, `LABEL`, `DATA`). Output clean one-line CSV only:

```
UID,OnTime
UID,Late
```

The Python parser splits on `,` and reads exactly two fields: `uid` and `status`.

---

## Dashboard Pages

### 1. Live Dashboard (`index.html`)
- Real-time scan feed — new row appears instantly on every card tap via SocketIO
- Each row shows: student photo, name, grade/section, status badge (On Time / Late / Unknown), timestamp
- Summary cards at top: Total Scans Today, On Time count, Late count, Unknown cards

### 2. Students Page (`students.html`)
- Table listing all registered students
- Add / Edit / Delete student via modal form
- Fields: Name, LRN, Grade, Section, RFID UID, Photo upload
- "Capture UID" button: tap a card while the modal is open to auto-fill the UID field

### 3. Logs Page (`logs.html`)
- Full scan history table: Name, UID, Grade/Section, Status, Timestamp
- Filter by date range
- Search by student name or section
- Export current view to CSV

---

## Implementation Steps

### Step 1 — Project scaffold
- Create the full directory structure as shown above
- Create `requirements.txt` with: `flask`, `flask-socketio`, `pyserial`, `eventlet`

### Step 2 — `database.py`
- `init_db()` — creates `school.db` and both tables if they don't exist; call on app startup
- `get_student_by_uid(uid)` — returns student row or None
- `log_scan(uid, student_id, status)` — inserts a row into `scan_logs`
- `get_all_students()` — returns all students for the students page
- `add_student(data)` / `update_student(id, data)` / `delete_student(id)` — CRUD helpers
- `get_logs(date_from, date_to, search)` — filtered query for logs page

### Step 3 — `app.py`
- Initialize Flask + SocketIO + call `init_db()` on startup
- **Serial thread** (daemon `threading.Thread`):
  - Opens the configured COM port (e.g. `COM3`) at the correct baud rate
  - Reads lines, strips whitespace, splits on `,` to get `(uid, status)`
  - Maps `OnTime` → `"On Time"`, `Late` → `"Late"`
  - Looks up student by UID, logs the scan to DB
  - Emits a `scan_event` SocketIO event with student info payload
  - Handles `SerialException` gracefully and retries connection every 5 seconds
- **Flask routes**:
  - `GET /` → render `index.html`
  - `GET /students` → render `students.html` with all students
  - `POST /students/add` → add student, handle photo upload to `static/uploads/`
  - `POST /students/edit/<id>` → update student
  - `POST /students/delete/<id>` → delete student
  - `GET /logs` → render `logs.html` with filtered results
  - `GET /logs/export` → stream CSV download of current filter
  - `GET /api/latest-uid` → returns the most recently scanned UID (for "Capture UID" feature)
- Start server with `socketio.run(app)` not `app.run()`

### Step 4 — `templates/index.html`
- Load Socket.IO client from CDN
- Connect to SocketIO on page load
- On `scan_event`: prepend a new row to the live feed table, increment summary counters
- Style status badges: green for On Time, red for Late, grey for Unknown

### Step 5 — `templates/students.html`
- Table of all students with Edit / Delete buttons
- Modal form for Add/Edit with all fields + photo preview
- "Capture UID" button polls `GET /api/latest-uid` while modal is open and populates the UID field

### Step 6 — `templates/logs.html`
- Date range pickers and search input that submit as GET params
- Table of results rendered server-side
- "Export CSV" button links to `/logs/export` with same filter params

### Step 7 — `static/style.css`
- Clean, school-appropriate styling
- Responsive layout for the dashboard
- Status badge styles: `.badge-ontime` (green), `.badge-late` (red), `.badge-unknown` (grey)

---

## Configuration

Add a config block near the top of `app.py` for easy adjustment:

```python
COM_PORT   = "COM3"           # Arduino serial port
BAUD_RATE  = 9600             # Must match Arduino sketch
DB_PATH    = "school.db"
UPLOAD_DIR = "static/uploads"
```

---

## Key Implementation Notes

- The serial reader runs in a **background daemon thread** — use `eventlet` as the async mode for Flask-SocketIO so threads and WebSockets cooperate correctly.
- `student_id` in `scan_logs` is **nullable** — unknown cards are still logged with their UID and status, shown as "Unknown" in the dashboard.
- Save photo uploads with a filename derived from `student_id` or a UUID to avoid collisions.
- All DB writes must use **parameterized queries** (no string formatting) to prevent SQL injection.
- Store the last-seen UID in a module-level variable in `app.py` for the `/api/latest-uid` endpoint — no DB query needed.
- The serial thread should set a short `timeout` on the serial port (e.g. `timeout=1`) so it doesn't block forever and can be shut down cleanly.
