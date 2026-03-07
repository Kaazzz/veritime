# Veritime — System Summary
**St. Catherine's College RFID Attendance System**

This document summarizes all features, specifications, and design decisions implemented in the current version of Veritime. It is intended for comparison against the original manuscript/proposal.

---

## 1. System Overview

Veritime is a real-time, RFID-based student attendance system designed for on-campus use. It runs entirely on a single school computer — no internet connection required during operation. An Arduino reads RFID card taps at the entrance, and a browser-based dashboard displays arrivals in real time.

**System name:** Veritime
**School:** St. Catherine's College
**Purpose:** Campus security, student wellness monitoring, and attendance recordkeeping

---

## 2. Technology Stack

| Layer | Technology | Notes |
|---|---|---|
| Hardware | Arduino + RFID reader | Connected via USB (serial/COM port) |
| Serial communication | PySerial | Reads Arduino output over USB |
| Backend server | Python + Flask | Local web server, runs on port 5000 |
| Real-time updates | Flask-SocketIO (WebSocket) | Pushes scan events to browser instantly |
| Database | SQLite (`school.db`) | Single-file database, no installation needed |
| Frontend | HTML + CSS + JavaScript | No frontend framework; runs in any browser |
| Fonts | DM Sans, Plus Jakarta Sans, DM Mono | Google Fonts |

**Python version required:** 3.8 or later (3.12 recommended)

---

## 3. System Architecture

```
Arduino (USB/COM port)
      |  serial CSV: UID, Status
      v
Python Serial Reader Thread  -->  SQLite Database (school.db)
      |
      |  SocketIO event broadcast
      v
Flask Web Server  -->  Browser Dashboard (live, no page refresh)
```

- The serial reader runs in a **background daemon thread** alongside the web server
- If the Arduino disconnects, the system retries the connection every 5 seconds automatically
- The browser receives scan events via **WebSocket** — no polling, no page refresh required
- The system works **offline** (LAN only); no external services are called during operation

---

## 4. Database Schema

### Table: `students`
Stores registered student records.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER (PK, autoincrement) | Internal record ID |
| `rfid_uid` | TEXT (unique, not null) | RFID card UID — must be unique per student |
| `lrn` | TEXT (nullable) | DepEd Learner Reference Number |
| `name` | TEXT (not null) | Full name stored as "Lastname, Firstname M." |
| `grade` | TEXT (nullable) | Grade level (e.g. "Grade 7") |
| `section` | TEXT (nullable) | Section name (e.g. "Mabini") |
| `photo_path` | TEXT (nullable) | Relative path to uploaded photo in `static/uploads/` |

### Table: `scan_logs`
Stores every RFID scan event.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER (PK, autoincrement) | Internal log ID |
| `rfid_uid` | TEXT (not null) | The UID that was scanned |
| `student_id` | INTEGER (nullable, FK) | Links to `students.id`; NULL if card is not registered |
| `timestamp` | DATETIME (default: now) | Auto-set to current date and time on insert |
| `status` | TEXT (constrained) | Only accepts `'On Time'` or `'Late'` |

**Note:** Unregistered cards are still logged with their UID and status — they appear as "Unknown" in the dashboard. No scan is silently dropped.

---

## 5. Arduino Serial Protocol

The system accepts two serial output formats from the Arduino:

**Format A — Plain (2 fields):**
```
UID,OnTime
UID,Late
```

**Format B — PLX-DAQ style (5+ fields):**
```
DATA,date,time,UID,OnTime
DATA,date,time,UID,Late
```

- Control lines (`CLEARDATA`, `LABEL`, `MSG`, `ROW`, `FONT`) are automatically ignored
- Status values accepted: `OnTime`, `On Time`, `Late` (case-insensitive)
- Baud rate: **9600**
- The COM port is **auto-detected** at startup (see Section 8)

---

## 6. Pages and Features

### 6.1 Landing Page (`/landing`)
- Introductory/welcome page for the system
- Displays the Veritime branding and a brief description of the system's purpose
- Links to Dashboard, Students, and Logs
- Features section describing: Campus Security, Student Wellness Monitoring, Live Dashboard, Records & Reporting
- "How It Works" section with 3 steps: Enroll, Set up reader, Monitor arrivals
- Animated mock dashboard preview shown in the hero section
- Statistics bar: "<1s scan-to-dashboard", "100% on-campus offline-capable", "Safe — student welfare first"
- Scroll-reveal animations on sections
- Fully responsive (mobile-friendly)

### 6.2 Live Dashboard (`/`)
**Real-time attendance monitoring screen**

- **Latest Scan panel** — shows the most recently scanned student's:
  - Photo (or initial avatar if no photo)
  - Full name
  - Grade and Section
  - LRN (Learner Reference Number)
  - Status badge (On Time / Late / Unknown)
  - Timestamp
- **Summary cards (4 counters):**
  - Total Scans Today
  - On Time count
  - Late count
  - Unknown cards count
- **Live feed table** — every new scan appears instantly at the top without refreshing:
  - Student avatar (photo or initial)
  - Name
  - Grade & Section
  - Status badge (color-coded)
  - Time of scan
  - Feed is capped at the 50 most recent rows
- **Connection status indicators:**
  - Server (WebSocket): Connected / Disconnected
  - Arduino (Serial): Connected / Disconnected
- Counters and the latest scan panel update live on every scan event

### 6.3 Students Page (`/students`)
**Student enrollment and management**

- Displays all registered students in a table:
  - Photo avatar (or initial placeholder)
  - Full name
  - LRN
  - Grade
  - Section
  - RFID UID
  - Edit and Delete buttons
- **Grade filter bar** — filter the list by grade level (pills/tabs, dynamically built from existing grades)
- **Add Student modal form:**
  - Last Name, First Name, Middle Initial (stored as "Lastname, Firstname M.")
  - LRN (Learner Reference Number)
  - Grade
  - Section
  - RFID UID field with **Capture button** — tap a card while the modal is open to auto-fill the UID (polls `/api/latest-uid` every 500ms)
  - Photo upload with live preview before saving
- **Edit Student modal** — pre-fills all fields from the selected student record; supports updating any field including replacing the photo
- **Delete Student** — prompts for confirmation before deleting
- Student count shown in page subtitle (updates with grade filter)

### 6.4 Logs Page (`/logs`)
**Full attendance history and export**

- Displays all scan records in a table:
  - Student name (shows "Unknown" for unregistered cards)
  - RFID UID
  - Grade
  - Section
  - Status badge (On Time / Late)
  - Timestamp
- **Filter controls:**
  - Date From / Date To (date range filter)
  - Search by student name or section (partial match)
  - Clear filters button (shown only when filters are active)
- **Export CSV button** — downloads the currently filtered view as a `.csv` file with columns: Name, UID, Grade, Section, Status, Timestamp
- Record count shown in page subtitle

---

## 7. API Endpoints

| Method | URL | Description |
|---|---|---|
| GET | `/landing` | Landing/welcome page |
| GET | `/` | Live dashboard |
| GET | `/students` | Students list (optional `?grade=` filter) |
| POST | `/students/add` | Add a new student (with optional photo upload) |
| POST | `/students/edit/<id>` | Update an existing student record |
| POST | `/students/delete/<id>` | Delete a student record |
| GET | `/logs` | Scan logs (optional `?date_from=`, `?date_to=`, `?search=` filters) |
| GET | `/logs/export` | Download filtered logs as CSV |
| GET | `/api/latest-uid` | Returns the most recently scanned RFID UID (used by Capture button) |
| GET | `/api/summary` | Returns today's scan summary counts as JSON |

**WebSocket events (SocketIO):**
- `scan_event` — emitted on every RFID scan; payload includes UID, status, student name, grade, section, LRN, photo path
- `serial_status` — emitted when the Arduino connects or disconnects; payload: `{ connected: true/false }`

---

## 8. Auto COM Port Detection (`configure_port.py`)

- Runs automatically when `start.bat` is launched (before the server starts)
- Scans all available USB/serial ports
- If **one port** is found: selects it automatically and patches `app.py` with the correct COM port
- If **multiple ports** are found: prompts the user to choose from a numbered list
- If **no ports** are found: exits with an error message instructing the user to plug in the Arduino
- This means the system works on any computer without manually editing configuration files

---

## 9. Startup (`start.bat`)

The system is launched by double-clicking `start.bat`. It performs the following steps automatically:

1. Checks if Python is installed (`python` or `py` launcher as fallback)
2. Creates a Python virtual environment (`venv\`) on first run
3. Activates the virtual environment
4. Installs/updates required packages from `requirements.txt` (Flask, Flask-SocketIO, PySerial)
5. Runs `configure_port.py` to detect and set the Arduino COM port
6. Opens the browser to `http://localhost:5000/landing` after a 4-second delay
7. Starts the Flask server

If any step fails, an error message is displayed and the script pauses so the user can read it.

---

## 10. Student Name Format

Names are stored in the database as:
```
Lastname, Firstname M.
```

- The Add/Edit form uses **three separate fields**: Last Name, First Name, Middle Initial
- Middle Initial is stored as a single uppercase letter followed by a period (e.g. "B.")
- When editing, the stored name is **parsed back** into the three fields automatically

---

## 11. Photo Uploads

- Photos are stored in `static/uploads/`
- Filename is the student's database `id` plus the original file extension (e.g. `12.jpg`)
- Supported formats: any image type accepted by the browser (`image/*`)
- Photo preview is shown in the modal before saving
- Photos are displayed in the dashboard live feed, the latest scan panel, and the students table
- If no photo is uploaded, an initial-letter avatar is shown instead

---

## 12. Security

- All database queries use **parameterized statements** (no string-formatted SQL) — SQL injection is prevented
- HTML output in the live feed is escaped using a custom `escHtml()` function — XSS is prevented
- The server binds to `0.0.0.0:5000` (accessible on the local network), intended for LAN use within the school only
- The app secret key is randomly generated on each startup (`os.urandom(24)`)

---

## 13. File Structure

```
veritime/
├── app.py                  -- Flask server, SocketIO, serial reader thread, all routes
├── database.py             -- SQLite setup and all query functions
├── configure_port.py       -- Auto-detects Arduino COM port at startup
├── requirements.txt        -- Python package dependencies
├── start.bat               -- One-click launcher for Windows
├── school.db               -- SQLite database (auto-created on first run)
├── static/
│   ├── style.css           -- All dashboard/app styling
│   └── uploads/            -- Student photo files
└── templates/
    ├── base.html           -- Shared navigation layout for app pages
    ├── landing.html        -- Welcome/landing page (standalone, full design)
    ├── index.html          -- Live dashboard
    ├── students.html       -- Student management
    └── logs.html           -- Scan history and export
```

---

## 14. Dependencies (`requirements.txt`)

| Package | Purpose |
|---|---|
| `flask` | Web server and routing |
| `flask-socketio` | WebSocket support for real-time scan events |
| `pyserial` | Serial communication with the Arduino over USB |

All dependencies are installed automatically by `start.bat` on first run.
