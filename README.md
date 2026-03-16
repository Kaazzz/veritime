# Veritime

A real-time RFID-based school attendance system. Students tap their RFID cards on an Arduino reader; the web dashboard updates instantly and logs every scan to a local SQLite database.

---

## Features

- **Live Dashboard** — real-time scan feed via WebSocket, shows the latest student scan with photo, name, LRN, grade/section, and status
- **Summary Cards** — today's total scans, on-time count, late count, and unknown cards at a glance
- **Student Management** — add, edit, and delete student records with photo upload and RFID UID capture
- **Scan Logs** — filterable by date range and student name/section, with CSV export
- **Arduino Integration** — reads PLX-DAQ serial output from an Arduino RFID reader over USB serial
- **Connection Status** — live indicators for WebSocket and Arduino serial connection health

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask, Flask-SocketIO |
| Database | SQLite (`school.db`) |
| Hardware | Arduino + RFID reader (PLX-DAQ serial protocol) |
| Frontend | Jinja2, vanilla JS, Socket.IO |
| Styling | Neumorphism design system (yellow & black accents) |

---

## Requirements

- Python 3.9+
- Arduino with RFID reader connected via USB serial
- Windows (tested on Windows 11); other platforms require changing `COM_PORT` in `app.py`

---

## Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd veritime
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the serial port

Run the configuration utility to set your COM port interactively:

```bash
python configure_port.py
```

Or manually open `app.py` and set the correct COM port for your Arduino:

```python
COM_PORT = "COM7"   # change to match your system (e.g. COM3, COM5)
BAUD_RATE = 9600
```

To find your port: Device Manager → Ports (COM & LPT).

### 5. Run the app

```bash
python app.py
```

Open your browser at `http://localhost:5000`.

---

## Project Structure

```
veritime/
├── app.py              # Flask app, serial reader thread, routes
├── database.py         # SQLite helpers (init, queries, CRUD)
├── configure_port.py   # Interactive COM port configuration utility
├── requirements.txt    # Python dependencies
├── school.db           # SQLite database (auto-created on first run)
├── static/
│   ├── style.css       # Neumorphism design system
│   └── uploads/        # Student photo uploads
└── templates/
    ├── base.html       # Shared nav, layout shell
    ├── index.html      # Live dashboard
    ├── students.html   # Student management
    └── logs.html       # Scan log viewer & CSV export
```

---

## Arduino Serial Format

The system expects PLX-DAQ formatted serial output from the Arduino:

```
CLEARDATA
LABEL,Date,Time,RFID UID,Status,Late Total
DATA,03/07/2026,08:15:00,A1B2C3D4,ONTIME,0
DATA,03/07/2026,08:45:00,E5F6A7B8,LATE,1
```

Plain `UID,Status` lines are also accepted as a fallback:

```
A1B2C3D4,ONTIME
E5F6A7B8,LATE
```

Valid status values: `ONTIME`, `ON TIME`, `LATE` (case-insensitive).

---

## Student Records

Each student has:

| Field | Description |
|---|---|
| RFID UID | Unique card identifier read from the Arduino |
| LRN | Learner Reference Number |
| Name | Stored as `Lastname, Firstname M.` |
| Grade | e.g. `Grade 7` |
| Section | e.g. `Sampaguita` |
| Photo | Optional, stored in `static/uploads/` |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Live dashboard |
| `GET` | `/students` | Student list & management |
| `POST` | `/students/add` | Add a new student |
| `POST` | `/students/edit/<id>` | Edit an existing student |
| `POST` | `/students/delete/<id>` | Delete a student |
| `GET` | `/logs` | Scan log viewer |
| `GET` | `/logs/export` | Download logs as CSV |
| `GET` | `/api/latest-uid` | Get the most recently scanned UID (JSON) |
| `GET` | `/api/summary` | Get today's scan summary (JSON) |

---

## Notes

- The database and uploads folder are excluded from version control via `.gitignore`
- Flask runs with `use_reloader=False` to prevent the serial port from being opened twice in debug mode
- If the Arduino is disconnected, the serial reader thread retries automatically every 5 seconds

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `SerialException: could not open port` | Check the COM port in `port.cfg` or `app.py`; ensure no other app has the port open |
| Dashboard shows no scans | Confirm Arduino serial output matches the expected format (see **Arduino Serial Format**) |
| Photos not displaying | Ensure `static/uploads/` exists and Flask has write permission |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` inside the activated virtual environment |
