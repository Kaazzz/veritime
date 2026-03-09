import os
import re
import csv
import threading
import time
from io import StringIO

from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, jsonify, Response, session, flash
from flask_socketio import SocketIO
import serial

from database import (
    init_db, get_student_by_uid, log_scan,
    get_all_students, get_all_grades, add_student, update_student, delete_student,
    get_logs, get_today_summary, get_latest_scan, get_student_logs_from,
    get_student_by_id,
)

# ── Config ────────────────────────────────────────────────────────────────────
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"
COM_PORT   = "COM7"
BAUD_RATE  = 9600
DB_PATH    = "school.db"
UPLOAD_DIR = "static/uploads"
PORT_CFG   = "port.cfg"


def get_active_port():
    """Return port from port.cfg if available, otherwise fall back to COM_PORT."""
    if os.path.exists(PORT_CFG):
        try:
            with open(PORT_CFG, encoding="utf-8") as f:
                port = f.read().strip()
            if port:
                return port
        except OSError:
            pass
    return COM_PORT

# ── App setup ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.urandom(24)
socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")

_latest_uid_lock = threading.Lock()
_latest_uid = None


# ── Serial reader thread ───────────────────────────────────────────────────────
def serial_reader():
    global _latest_uid
    while True:
        try:
            port = get_active_port()
            ser = serial.Serial(port, BAUD_RATE, timeout=1)
            print(f"[Serial] Connected to {port}")
            socketio.emit("serial_status", {"connected": True})
            while True:
                line = ser.readline().decode("utf-8", errors="ignore").strip()
                if not line:
                    continue
                print(f"[Serial] Raw: {repr(line)}")

                parts = [p.strip() for p in line.split(",")]
                first = parts[0].upper()

                # Skip PLX-DAQ control lines and error messages
                if first in ("CLEARDATA", "LABEL", "MSG", "ROW", "FONT"):
                    continue

                STATUS_MAP = {
                    "ONTIME": "On Time", "ON TIME": "On Time",
                    "LATE": "Late",
                }

                uid = None
                status = None

                if first == "DATA":
                    # Try each plausible UID position and find the one whose
                    # neighbour matches a known status value
                    for i in range(1, len(parts) - 1):
                        candidate_status = STATUS_MAP.get(parts[i + 1].upper().strip())
                        if candidate_status and parts[i].strip():
                            uid    = parts[i].strip()
                            status = candidate_status
                            break
                    # Fallback: standard PLX-DAQ position DATA,date,time,UID,Status
                    if uid is None and len(parts) >= 5:
                        uid        = parts[3].strip()
                        status     = STATUS_MAP.get(parts[4].upper().strip())
                elif len(parts) == 2:
                    # Plain UID,Status
                    uid    = parts[0]
                    status = STATUS_MAP.get(parts[1].upper().strip())

                if not uid:
                    continue

                print(f"[Serial] UID={uid!r}  status={status!r}")

                if status is None:
                    print(f"[Serial] Could not determine status — skipping")
                    continue

                with _latest_uid_lock:
                    _latest_uid = uid

                student = get_student_by_uid(uid)
                student_id = student["id"] if student else None
                log_scan(uid, student_id, status)

                socketio.emit("scan_event", {
                    "uid": uid,
                    "status": status,
                    "student_name": student["name"] if student else "Unknown",
                    "student_grade": student["grade"] if student else "",
                    "student_section": student["section"] if student else "",
                    "student_lrn": student["lrn"] if student else "",
                    "photo_path": student["photo_path"] if student else None,
                })
        except serial.SerialException as e:
            print(f"[Serial] Error: {e}. Retrying in 5s...")
            socketio.emit("serial_status", {"connected": False})
            time.sleep(5)
        except Exception as e:
            print(f"[Serial] Unexpected error: {e}. Retrying in 5s...")
            socketio.emit("serial_status", {"connected": False})
            time.sleep(5)


# ── Auth ──────────────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("index"))
    error = None
    if request.method == "POST":
        if (request.form.get("username") == ADMIN_USERNAME and
                request.form.get("password") == ADMIN_PASSWORD):
            session["logged_in"] = True
            return redirect(url_for("index"))
        error = "Invalid username or password."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/landing")
def landing():
    return render_template("landing.html")


@app.route("/")
@login_required
def index():
    summary = get_today_summary()
    latest  = get_latest_scan()
    return render_template("index.html", summary=summary, latest=latest, active_page="dashboard")


@app.route("/students")
@login_required
def students():
    grade = request.args.get("grade", "")
    all_students = get_all_students(grade)
    all_grades = get_all_grades()
    return render_template("students.html", students=all_students, all_grades=all_grades,
                           selected_grade=grade, active_page="students")


def build_full_name():
    last  = request.form.get("last_name", "").strip()
    first = request.form.get("first_name", "").strip()
    mi    = request.form.get("middle_initial", "").strip()
    if mi:
        mi = mi[0].upper() + "."
    parts = [first, mi] if mi else [first]
    return f"{last}, {' '.join(p for p in parts if p)}" if last else first


@app.route("/students/add", methods=["POST"])
@login_required
def add_student_route():
    data = {
        "rfid_uid": request.form.get("rfid_uid", "").strip(),
        "lrn":      request.form.get("lrn", "").strip(),
        "name":     build_full_name(),
        "grade":    request.form.get("grade", "").strip(),
        "section":  request.form.get("section", "").strip(),
        "photo_path": None,
    }
    student_id = add_student(data)
    photo = request.files.get("photo")
    if photo and photo.filename:
        ext = os.path.splitext(photo.filename)[1].lower()
        filename = f"{student_id}{ext}"
        photo.save(os.path.join(UPLOAD_DIR, filename))
        update_student(student_id, {"photo_path": f"uploads/{filename}"})
    return redirect(url_for("students"))


@app.route("/students/edit/<int:student_id>", methods=["POST"])
@login_required
def edit_student_route(student_id):
    data = {
        "rfid_uid": request.form.get("rfid_uid", "").strip(),
        "lrn":      request.form.get("lrn", "").strip(),
        "name":     build_full_name(),
        "grade":    request.form.get("grade", "").strip(),
        "section":  request.form.get("section", "").strip(),
    }
    photo = request.files.get("photo")
    if photo and photo.filename:
        ext = os.path.splitext(photo.filename)[1].lower()
        filename = f"{student_id}{ext}"
        photo.save(os.path.join(UPLOAD_DIR, filename))
        data["photo_path"] = f"uploads/{filename}"
    update_student(student_id, data)
    return redirect(url_for("students"))


@app.route("/students/delete/<int:student_id>", methods=["POST"])
@login_required
def delete_student_route(student_id):
    delete_student(student_id)
    return redirect(url_for("students"))


@app.route("/logs")
@login_required
def logs():
    date_from = request.args.get("date_from", "")
    date_to   = request.args.get("date_to", "")
    search    = request.args.get("search", "")
    log_data  = get_logs(date_from, date_to, search)
    return render_template(
        "logs.html",
        logs=log_data,
        date_from=date_from,
        date_to=date_to,
        search=search,
        active_page="logs",
    )


@app.route("/logs/export")
@login_required
def logs_export():
    date_from = request.args.get("date_from", "")
    date_to   = request.args.get("date_to", "")
    search    = request.args.get("search", "")
    log_data  = get_logs(date_from, date_to, search)

    def generate():
        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow(["Name", "UID", "Grade", "Section", "Status", "Timestamp"])
        for row in log_data:
            writer.writerow([
                row["student_name"], row["rfid_uid"],
                row["grade"], row["section"],
                row["status"], row["timestamp"],
            ])
        yield buf.getvalue()

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance_logs.csv"},
    )


@app.route("/api/latest-uid")
@login_required
def api_latest_uid():
    with _latest_uid_lock:
        return jsonify({"uid": _latest_uid})


@app.route("/api/summary")
@login_required
def api_summary():
    return jsonify(get_today_summary())


@app.route("/api/student/<int:student_id>/logs")
@login_required
def api_student_logs(student_id):
    date_from = request.args.get("date_from", "")
    date_to   = request.args.get("date_to", "")

    date_re = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    if not date_from or not date_re.match(date_from):
        return jsonify({"error": "date_from is required (YYYY-MM-DD)."}), 400
    if not date_to or not date_re.match(date_to):
        return jsonify({"error": "date_to is required (YYYY-MM-DD)."}), 400

    if not get_student_by_id(student_id):
        return jsonify({"error": "Student not found."}), 404

    data = get_student_logs_from(student_id, date_from, date_to)
    return jsonify(data)


# ── Startup ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    init_db()
    t = threading.Thread(target=serial_reader, daemon=True)
    t.start()
    socketio.run(app, debug=True, host="0.0.0.0", port=5000, use_reloader=False)
