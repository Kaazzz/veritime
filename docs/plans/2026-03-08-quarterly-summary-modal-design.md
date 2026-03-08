# Design: Student Quarterly Summary Modal

**Date:** 2026-03-08
**Status:** Approved

## Overview

Add a per-student quarterly attendance summary modal to the Students page. Each student row gets a "Quarterly" button that opens a modal showing total On Time / Late counts and a full log list for the selected quarter.

## Quarter Definitions (Philippine School Year)

| Quarter | Months         | Note                          |
|---------|----------------|-------------------------------|
| Q1      | Jun – Aug      | Same calendar year            |
| Q2      | Sep – Nov      | Same calendar year            |
| Q3      | Dec – Feb      | Dec of year, Jan–Feb of year+1 |
| Q4      | Mar – May      | Same calendar year            |

## Data Layer

### `database.py` — new function

```python
get_student_quarterly_summary(student_id, quarter, year)
```

- Computes date range from quarter + year using the PH school year mapping
- Queries `scan_logs` for that student within the date range
- Returns:
  ```python
  {
    "on_time": int,
    "late": int,
    "total": int,
    "logs": [{"timestamp": str, "status": str}, ...]  # newest first
  }
  ```

### `app.py` — new API route

```
GET /api/student/<id>/quarterly?quarter=Q1&year=2026
```

- Validates `quarter` (Q1–Q4) and `year` (integer)
- Returns JSON from `get_student_quarterly_summary`
- Returns 400 on invalid params, 404 if student not found

## Frontend

### Trigger

- New button added to each row's `.action-btns` in `students.html`
- Uses a calendar icon, labeled "Quarterly"
- Stores `data-student-id` and `data-student-name` attributes

### Modal Structure

```
[ Student Avatar + Name ]                    [ × ]
─────────────────────────────────────────────────
[ Q1 ] [ Q2 ] [ Q3 ] [ Q4 ]    Year: [ 2026 ▾ ]
─────────────────────────────────────────────────
[ Total: N ]  [ On Time: N ]  [ Late: N ]
─────────────────────────────────────────────────
Timestamp                 Status
2026-03-01 07:15          On Time
2026-02-28 07:45          Late
...  (scrollable)
```

### Behavior

- Quarter pills: Q1–Q4 (Q2 active by default based on current date)
- Year select: current school year and 2 prior years
- Changing quarter or year triggers a new `fetch` to the API and re-renders stats + log list
- Loading state shown while fetching
- Empty state shown if no logs found for that quarter
- Closes on Escape, backdrop click, or close button
- Fully separate from the add/edit student modal

## Files Changed

| File | Change |
|------|--------|
| `database.py` | Add `get_student_quarterly_summary()` |
| `app.py` | Add `/api/student/<id>/quarterly` route; import new DB function |
| `templates/students.html` | Add Quarterly button per row, quarterly modal HTML, JS logic |
