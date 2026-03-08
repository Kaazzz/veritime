# Quarterly Summary Modal Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a per-student quarterly attendance summary modal to the Students page showing On Time / Late totals and a full log list for a selected PH school-year quarter.

**Architecture:** Three-layer change — a new DB query function, a new JSON API route, and frontend HTML/JS in the existing students template. No new files needed. No page navigation — data loads via fetch on demand.

**Tech Stack:** Python 3 / Flask / SQLite3 / Jinja2 / vanilla JS / existing neu CSS design system

---

## Quarter Date Ranges (Philippine School Year)

The `year` parameter always refers to the **start** year of the school year (e.g., `2025` = SY 2025–2026).

| Quarter | Start         | End              |
|---------|---------------|------------------|
| Q1      | Jun 1, {year} | Aug 31, {year}   |
| Q2      | Sep 1, {year} | Nov 30, {year}   |
| Q3      | Dec 1, {year} | Feb 28/29, {year+1} |
| Q4      | Mar 1, {year+1} | May 31, {year+1} |

---

### Task 1: Add `get_student_quarterly_summary` to `database.py`

**Files:**
- Modify: `database.py`

**Step 1: Add the function at the bottom of `database.py`, before the final newline**

```python
def get_student_quarterly_summary(student_id, quarter, year):
    """
    Return attendance counts and log list for a student in a PH school-year quarter.

    quarter: "Q1" | "Q2" | "Q3" | "Q4"
    year:    int — start year of the school year (e.g. 2025 for SY 2025-2026)
    """
    import calendar

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
```

**Step 2: Verify manually**

Open a Python shell in the project root:
```bash
cd C:\Users\Zak\Documents\Veritime\veritime
venv\Scripts\python
```
Then:
```python
from database import get_student_quarterly_summary
# Replace 1 with a real student_id from your DB
result = get_student_quarterly_summary(1, "Q1", 2025)
print(result)
# Expected: dict with keys on_time, late, total, date_from, date_to, logs
```

**Step 3: Commit**

```bash
git add database.py
git commit -m "feat: add get_student_quarterly_summary DB function"
```

---

### Task 2: Add API route to `app.py`

**Files:**
- Modify: `app.py` (two locations)

**Step 1: Update the import from database (line ~11–15)**

Current:
```python
from database import (
    init_db, get_student_by_uid, log_scan,
    get_all_students, get_all_grades, add_student, update_student, delete_student,
    get_logs, get_today_summary, get_latest_scan,
)
```

Replace with:
```python
from database import (
    init_db, get_student_by_uid, log_scan,
    get_all_students, get_all_grades, add_student, update_student, delete_student,
    get_logs, get_today_summary, get_latest_scan, get_student_quarterly_summary,
)
```

**Step 2: Add the new route just before the `# ── Startup ───` block**

```python
@app.route("/api/student/<int:student_id>/quarterly")
def api_student_quarterly(student_id):
    quarter = request.args.get("quarter", "").upper()
    year_str = request.args.get("year", "")

    if quarter not in ("Q1", "Q2", "Q3", "Q4"):
        return jsonify({"error": "Invalid quarter. Use Q1–Q4."}), 400

    try:
        year = int(year_str)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid year."}), 400

    # Verify student exists
    with __import__('database').get_conn() as conn:
        student = conn.execute(
            "SELECT id, name FROM students WHERE id = ?", (student_id,)
        ).fetchone()
    if not student:
        return jsonify({"error": "Student not found."}), 404

    data = get_student_quarterly_summary(student_id, quarter, year)
    return jsonify(data)
```

**Step 3: Verify manually**

Start the server:
```bash
venv\Scripts\python app.py
```

In a browser or curl:
```
http://localhost:5000/api/student/1/quarterly?quarter=Q1&year=2025
```

Expected response:
```json
{"date_from": "2025-06-01", "date_to": "2025-08-31", "late": 0, "logs": [], "on_time": 0, "total": 0}
```

Bad params should return 400:
```
http://localhost:5000/api/student/1/quarterly?quarter=Q5&year=2025
```

**Step 4: Commit**

```bash
git add app.py
git commit -m "feat: add /api/student/<id>/quarterly route"
```

---

### Task 3: Add Quarterly button + modal + JS to `students.html`

**Files:**
- Modify: `templates/students.html`

**Step 1: Add the Quarterly button to each student row's action buttons**

Find this block in the `{% for s in students %}` loop (currently the last `</form>` before `</div>`):
```html
              <form method="post" action="/students/delete/{{ s.id }}" onsubmit="return confirm('Delete {{ s.name }}?')" style="display:inline">
                  <button type="submit" class="neu-btn neu-btn--sm neu-btn--danger" aria-label="Delete {{ s.name }}">
```

Add the Quarterly button **before** the delete `<form>`:
```html
                <button
                  class="neu-btn neu-btn--sm neu-btn--secondary quarterly-btn"
                  data-student-id="{{ s.id }}"
                  data-student-name="{{ s.name }}"
                  aria-label="Quarterly summary for {{ s.name }}"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
                  Quarterly
                </button>
```

**Step 2: Add the quarterly modal HTML after the existing student add/edit modal closing `</div>`**

Place this after line `</div>` that closes `id="modal-overlay"` (around line 186, just before `{% endblock %}`):

```html
<!-- ── Quarterly Summary Modal ──────────────────────────────────────────── -->
<div class="modal-overlay" id="quarterly-overlay" hidden role="dialog" aria-modal="true" aria-labelledby="quarterly-modal-title">
  <div class="modal neu-card" id="quarterly-modal" style="max-width:600px;width:100%">
    <div class="modal-header">
      <div style="display:flex;align-items:center;gap:12px">
        <div id="q-avatar" class="student-avatar student-avatar--placeholder" aria-hidden="true">?</div>
        <h2 class="modal-title" id="quarterly-modal-title">Quarterly Summary</h2>
      </div>
      <button class="modal-close" id="quarterly-modal-close" aria-label="Close quarterly summary">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </div>

    <!-- Quarter + Year selectors -->
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:16px">
      <div class="quarter-pills" role="group" aria-label="Select quarter">
        <button class="quarter-pill" data-q="Q1">Q1</button>
        <button class="quarter-pill" data-q="Q2">Q2</button>
        <button class="quarter-pill" data-q="Q3">Q3</button>
        <button class="quarter-pill" data-q="Q4">Q4</button>
      </div>
      <label for="q-year-select" class="form-label" style="margin:0">SY</label>
      <select id="q-year-select" class="neu-input" style="width:auto;padding:6px 10px"></select>
    </div>

    <!-- Date range label -->
    <p id="q-date-range" style="font-size:0.78rem;color:var(--text-muted,#888);margin-bottom:14px"></p>

    <!-- Stats -->
    <div id="q-stats" style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:18px">
      <div class="neu-card" style="text-align:center;padding:14px 8px">
        <div style="font-size:1.6rem;font-weight:700" id="q-total">—</div>
        <div style="font-size:0.75rem;color:var(--text-muted,#888);margin-top:2px">Total</div>
      </div>
      <div class="neu-card" style="text-align:center;padding:14px 8px">
        <div style="font-size:1.6rem;font-weight:700;color:#4ade80" id="q-ontime">—</div>
        <div style="font-size:0.75rem;color:var(--text-muted,#888);margin-top:2px">On Time</div>
      </div>
      <div class="neu-card" style="text-align:center;padding:14px 8px">
        <div style="font-size:1.6rem;font-weight:700;color:#F5C400" id="q-late">—</div>
        <div style="font-size:0.75rem;color:var(--text-muted,#888);margin-top:2px">Late</div>
      </div>
    </div>

    <!-- Log list -->
    <div id="q-log-body" style="max-height:280px;overflow-y:auto">
      <table class="data-table" style="width:100%">
        <thead>
          <tr>
            <th scope="col">Timestamp</th>
            <th scope="col">Status</th>
          </tr>
        </thead>
        <tbody id="q-log-rows"></tbody>
      </table>
    </div>
    <div id="q-empty" hidden style="text-align:center;padding:24px;color:var(--text-muted,#888);font-size:0.875rem">
      No scan logs found for this quarter.
    </div>
    <div id="q-loading" hidden style="text-align:center;padding:24px;color:var(--text-muted,#888);font-size:0.875rem">
      Loading…
    </div>
  </div>
</div>
```

**Step 3: Add the quarterly modal JS at the end of the `{% block scripts %}` section**

Add this after the closing `</script>` of the existing block (before `{% endblock %}`):

```html
<script>
  // ── Quarterly Summary Modal ───────────────────────────────────────────────
  const qOverlay   = document.getElementById('quarterly-overlay');
  const qClose     = document.getElementById('quarterly-modal-close');
  const qAvatar    = document.getElementById('q-avatar');
  const qTitle     = document.getElementById('quarterly-modal-title');
  const qDateRange = document.getElementById('q-date-range');
  const qTotal     = document.getElementById('q-total');
  const qOntime    = document.getElementById('q-ontime');
  const qLate      = document.getElementById('q-late');
  const qLogRows   = document.getElementById('q-log-rows');
  const qEmpty     = document.getElementById('q-empty');
  const qLoading   = document.getElementById('q-loading');
  const qLogBody   = document.getElementById('q-log-body');
  const qYearSel   = document.getElementById('q-year-select');

  let activeStudentId = null;
  let activeQuarter   = null;
  let activeYear      = null;

  // Populate year selector with current SY and 2 prior
  function currentSchoolYear() {
    const now = new Date();
    // SY starts June — if before June, we're in the previous SY
    return now.getMonth() >= 5 ? now.getFullYear() : now.getFullYear() - 1;
  }

  function defaultQuarter() {
    const m = new Date().getMonth() + 1; // 1-12
    if (m >= 6 && m <= 8)  return "Q1";
    if (m >= 9 && m <= 11) return "Q2";
    if (m === 12)           return "Q3";
    if (m >= 1 && m <= 2)  return "Q3";
    return "Q4"; // Mar–May
  }

  (function buildYearOptions() {
    const sy = currentSchoolYear();
    for (let y = sy; y >= sy - 2; y--) {
      const opt = document.createElement('option');
      opt.value = y;
      opt.textContent = `${y}–${y + 1}`;
      qYearSel.appendChild(opt);
    }
  })();

  function setActiveQuarterPill(q) {
    document.querySelectorAll('.quarter-pill').forEach(pill => {
      pill.classList.toggle('quarter-pill--active', pill.dataset.q === q);
    });
  }

  function showLoading() {
    qLoading.removeAttribute('hidden');
    qLogBody.setAttribute('hidden', '');
    qEmpty.setAttribute('hidden', '');
    qTotal.textContent = '—';
    qOntime.textContent = '—';
    qLate.textContent = '—';
    qDateRange.textContent = '';
  }

  function renderData(data) {
    qTotal.textContent  = data.total;
    qOntime.textContent = data.on_time;
    qLate.textContent   = data.late;
    qDateRange.textContent = `${data.date_from} — ${data.date_to}`;
    qLoading.setAttribute('hidden', '');

    if (data.logs.length === 0) {
      qEmpty.removeAttribute('hidden');
      qLogBody.setAttribute('hidden', '');
      return;
    }

    qEmpty.setAttribute('hidden', '');
    qLogBody.removeAttribute('hidden');
    qLogRows.innerHTML = data.logs.map(log => `
      <tr>
        <td><span class="timestamp">${log.timestamp}</span></td>
        <td><span class="badge ${log.status === 'On Time' ? 'badge--ontime' : 'badge--late'}">${log.status}</span></td>
      </tr>
    `).join('');
  }

  function fetchQuarterly() {
    showLoading();
    fetch(`/api/student/${activeStudentId}/quarterly?quarter=${activeQuarter}&year=${activeYear}`)
      .then(r => r.json())
      .then(renderData)
      .catch(() => {
        qLoading.setAttribute('hidden', '');
        qEmpty.removeAttribute('hidden');
        qEmpty.textContent = 'Error loading data.';
      });
  }

  function openQuarterlyModal(studentId, studentName) {
    activeStudentId = studentId;
    activeQuarter   = defaultQuarter();
    activeYear      = parseInt(qYearSel.value);
    qTitle.textContent = studentName;
    qAvatar.textContent = studentName.charAt(0).toUpperCase();
    setActiveQuarterPill(activeQuarter);
    qOverlay.removeAttribute('hidden');
    fetchQuarterly();
  }

  function closeQuarterlyModal() {
    qOverlay.setAttribute('hidden', '');
  }

  // Quarter pill clicks
  document.querySelectorAll('.quarter-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      activeQuarter = pill.dataset.q;
      setActiveQuarterPill(activeQuarter);
      fetchQuarterly();
    });
  });

  // Year change
  qYearSel.addEventListener('change', () => {
    activeYear = parseInt(qYearSel.value);
    fetchQuarterly();
  });

  // Open buttons
  document.querySelectorAll('.quarterly-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      openQuarterlyModal(
        parseInt(btn.dataset.studentId),
        btn.dataset.studentName
      );
    });
  });

  qClose.addEventListener('click', closeQuarterlyModal);
  qOverlay.addEventListener('click', e => { if (e.target === qOverlay) closeQuarterlyModal(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeQuarterlyModal(); });
</script>
```

**Step 4: Add quarter pill CSS to `static/style.css`**

Find any existing `.grade-pill` styles and add after them:

```css
/* ── Quarter pills ─────────────────────────────────────────────────────── */
.quarter-pills {
  display: flex;
  gap: 6px;
}

.quarter-pill {
  padding: 5px 14px;
  border-radius: 20px;
  border: 1px solid var(--border, #2a2a2a);
  background: var(--surface, #141414);
  color: var(--text-muted, #888);
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.quarter-pill--active,
.quarter-pill:hover {
  background: #F5C400;
  color: #0B0B0B;
  border-color: #F5C400;
}
```

**Step 5: Manual verification**

1. Start the server: `venv\Scripts\python app.py`
2. Open `http://localhost:5000/students`
3. Click "Quarterly" on any student row
4. Verify modal opens with correct student name
5. Click Q1, Q2, Q3, Q4 — verify stats update each time
6. Change the SY year dropdown — verify stats reload
7. Press Escape — verify modal closes
8. Click backdrop — verify modal closes

**Step 6: Commit**

```bash
git add templates/students.html static/style.css
git commit -m "feat: add quarterly summary modal to students page"
```

---

## Done

All three tasks complete. The feature adds:
- `get_student_quarterly_summary()` in `database.py`
- `GET /api/student/<id>/quarterly` in `app.py`
- Quarterly button + modal + JS in `students.html`
- Quarter pill CSS in `style.css`
