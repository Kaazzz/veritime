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


def log_scan(uid, student_id, status):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO scan_logs (rfid_uid, student_id, status) VALUES (?, ?, ?)",
            (uid, student_id, status),
        )
        conn.commit()


def get_all_students():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM students ORDER BY name").fetchall()
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
