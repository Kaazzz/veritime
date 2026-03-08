import calendar
import sqlite3

DB_PATH = "school.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                rfid_uid    TEXT UNIQUE NOT NULL,
                lrn         TEXT,
                name        TEXT NOT NULL,
                grade       TEXT,
                section     TEXT,
                photo_path  TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scan_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                rfid_uid    TEXT NOT NULL,
                student_id  INTEGER REFERENCES students(id),
                timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
                status      TEXT CHECK(status IN ('On Time', 'Late')) NOT NULL
            )
        """)
        conn.commit()


def get_student_by_uid(uid):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM students WHERE rfid_uid = ?", (uid,)).fetchone()
        return dict(row) if row else None


def get_student_by_id(student_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        return dict(row) if row else None


def log_scan(uid, student_id, status):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO scan_logs (rfid_uid, student_id, status) VALUES (?, ?, ?)",
            (uid, student_id, status),
        )
        conn.commit()


def get_all_grades():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT grade FROM students WHERE grade IS NOT NULL AND grade != '' ORDER BY grade"
        ).fetchall()
        return [r["grade"] for r in rows]


def get_all_students(grade=""):
    query = "SELECT * FROM students"
    params = []
    if grade:
        query += " WHERE grade = ?"
        params.append(grade)
    query += " ORDER BY name"
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def add_student(data):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO students (rfid_uid, lrn, name, grade, section, photo_path) VALUES (?, ?, ?, ?, ?, ?)",
            (data["rfid_uid"], data["lrn"], data["name"], data["grade"], data["section"], data.get("photo_path")),
        )
        conn.commit()
        return cur.lastrowid


def update_student(student_id, data):
    fields = []
    values = []
    for key in ("rfid_uid", "lrn", "name", "grade", "section", "photo_path"):
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])
    if not fields:
        return
    values.append(student_id)
    with get_conn() as conn:
        conn.execute(f"UPDATE students SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()


def delete_student(student_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
        conn.commit()


def get_logs(date_from="", date_to="", search=""):
    query = """
        SELECT
            sl.id, sl.rfid_uid, sl.timestamp, sl.status,
            COALESCE(s.name, 'Unknown') AS student_name,
            COALESCE(s.grade, '') AS grade,
            COALESCE(s.section, '') AS section
        FROM scan_logs sl
        LEFT JOIN students s ON sl.student_id = s.id
        WHERE 1=1
    """
    params = []
    if date_from:
        query += " AND DATE(sl.timestamp) >= ?"
        params.append(date_from)
    if date_to:
        query += " AND DATE(sl.timestamp) <= ?"
        params.append(date_to)
    if search:
        query += " AND (s.name LIKE ? OR s.section LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    query += " ORDER BY sl.timestamp DESC"
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_latest_scan():
    with get_conn() as conn:
        row = conn.execute("""
            SELECT
                sl.rfid_uid, sl.timestamp, sl.status,
                COALESCE(s.name, 'Unknown') AS student_name,
                COALESCE(s.grade, '')       AS grade,
                COALESCE(s.section, '')     AS section,
                COALESCE(s.lrn, '')         AS lrn,
                s.photo_path
            FROM scan_logs sl
            LEFT JOIN students s ON sl.student_id = s.id
            ORDER BY sl.timestamp DESC
            LIMIT 1
        """).fetchone()
        return dict(row) if row else None


def get_today_summary():
    with get_conn() as conn:
        row = conn.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'On Time' THEN 1 ELSE 0 END) AS on_time,
                SUM(CASE WHEN status = 'Late' THEN 1 ELSE 0 END) AS late,
                SUM(CASE WHEN student_id IS NULL THEN 1 ELSE 0 END) AS unknown
            FROM scan_logs
            WHERE DATE(timestamp) = DATE('now')
        """).fetchone()
        return dict(row) if row else {"total": 0, "on_time": 0, "late": 0, "unknown": 0}


def get_student_quarterly_summary(student_id, quarter, year):
    """
    Return attendance counts and log list for a student in a PH school-year quarter.

    quarter: "Q1" | "Q2" | "Q3" | "Q4"
    year:    int — start year of the school year (e.g. 2025 for SY 2025-2026)
    """
    quarter_ranges = {
        "Q1": (f"{year}-06-01",   f"{year}-08-31"),
        "Q2": (f"{year}-09-01",   f"{year}-11-30"),
        "Q3": (f"{year}-12-01",   f"{year+1}-02-{calendar.monthrange(year+1, 2)[1]:02d}"),
        "Q4": (f"{year+1}-03-01", f"{year+1}-05-31"),
    }

    if quarter not in quarter_ranges:
        raise ValueError(f"Invalid quarter: {quarter}")

    date_from, date_to = quarter_ranges[quarter]

    with get_conn() as conn:
        row = conn.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'On Time' THEN 1 ELSE 0 END) AS on_time,
                SUM(CASE WHEN status = 'Late'    THEN 1 ELSE 0 END) AS late
            FROM scan_logs
            WHERE student_id = ?
              AND DATE(timestamp) >= ?
              AND DATE(timestamp) <= ?
        """, (student_id, date_from, date_to)).fetchone()

        logs = conn.execute("""
            SELECT timestamp, status
            FROM scan_logs
            WHERE student_id = ?
              AND DATE(timestamp) >= ?
              AND DATE(timestamp) <= ?
            ORDER BY timestamp DESC
        """, (student_id, date_from, date_to)).fetchall()

    return {
        "on_time":   row["on_time"] or 0,
        "late":      row["late"]    or 0,
        "total":     row["total"]   or 0,
        "date_from": date_from,
        "date_to":   date_to,
        "logs":      [{"timestamp": r["timestamp"], "status": r["status"]} for r in logs],
    }
