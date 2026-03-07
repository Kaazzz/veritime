import os
import csv
import threading
import time
from io import StringIO

from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
from flask_socketio import SocketIO
import serial

from database import (
    init_db, get_student_by_uid, log_scan,
    get_all_students, add_student, update_student, delete_student,
    get_logs, get_today_summary,
)

# ── Config ────────────────────────────────────────────────────────────────────
COM_PORT   = "COM7"
BAUD_RATE  = 9600
DB_PATH    = "school.db"
UPLOAD_DIR = "static/uploads"

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
            ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)
            print(f"[Serial] Connected to {COM_PORT}")
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

                # PLX-DAQ data line: DATA,Date,Time,UID,Status,...
                if first == "DATA" and len(parts) >= 5:
                    uid = parts[3]
                    raw_status = parts[4]
                # Plain CSV line: UID,Status
                elif len(parts) == 2:
                    uid = parts[0]
                    raw_status = parts[1]
                else:
                    continue

                if not uid:
                    continue

                print(f"[Serial] UID={uid!r}  status={raw_status!r}")
                status = {
                    "OnTime": "On Time",
                    "On Time": "On Time",
                    "ONTIME": "On Time",
                    "Late": "Late",
                    "LATE": "Late",
                }.get(raw_status)
                if status is None:
                    print(f"[Serial] Unknown status {raw_status!r} — skipping")
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
                    "photo_path": student["photo_path"] if student else None,
                })
        except serial.SerialException as e:
            print(f"[Serial] Error: {e}. Retrying in 5s...")
            time.sleep(5)
        except Exception as e:
            print(f"[Serial] Unexpected error: {e}. Retrying in 5s...")
            time.sleep(5)


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    summary = get_today_summary()
    return render_template("index.html", summary=summary, active_page="dashboard")


@app.route("/students")
def students():
    all_students = get_all_students()
    return render_template("students.html", students=all_students, active_page="students")


def build_full_name():
    last  = request.form.get("last_name", "").strip()
    first = request.form.get("first_name", "").strip()
    mi    = request.form.get("middle_initial", "").strip()
    if mi:
        mi = mi[0].upper() + "."
    parts = [first, mi] if mi else [first]
    return f"{last}, {' '.join(p for p in parts if p)}" if last else first


@app.route("/students/add", methods=["POST"])
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
def delete_student_route(student_id):
    delete_student(student_id)
    return redirect(url_for("students"))


@app.route("/logs")
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
def api_latest_uid():
    with _latest_uid_lock:
        return jsonify({"uid": _latest_uid})


@app.route("/api/summary")
def api_summary():
    return jsonify(get_today_summary())


# ── Startup ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    init_db()
    t = threading.Thread(target=serial_reader, daemon=True)
    t.start()
    socketio.run(app, debug=True, host="0.0.0.0", port=5000, use_reloader=False)
