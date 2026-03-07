# Veritime — What Changed From the Manuscript
**St. Catherine's College | Capstone Research Project**

This document explains what was changed, improved, or added to Veritime compared to what was originally written in the manuscript. It is written so that everyone on the research team — not just the technical members — can understand what the final system looks like and why certain decisions were made.

---

## The Big Picture

The manuscript described a system where an Arduino reads RFID cards and sends the data directly into a Microsoft Excel spreadsheet through a tool called PLX-DAQ. That was the original plan.

What was actually built is much more than that. The final Veritime is a complete web-based attendance platform — with a live dashboard, student profiles, attendance history, photo support, and a one-click launcher — all running locally on the school computer with no internet needed.

Think of it this way:

> **Manuscript:** A smart card reader that writes to a spreadsheet.
>
> **Final System:** A full attendance management application that runs in a browser, updates in real time, stores everything in a proper database, and can be accessed from any device on the school's Wi-Fi.

The core purpose remained exactly the same — record when students arrive and whether they are on time or late. But nearly everything around that core was upgraded to be more practical, more reliable, and more useful for a real school environment.

---

## 1. Excel and PLX-DAQ Were Replaced

**What the manuscript said:**
Attendance data would be logged into Microsoft Excel using a tool called PLX-DAQ, which acts as a bridge between the Arduino and Excel. Each card tap would add a new row to the spreadsheet.

**What changed:**
Excel and PLX-DAQ were completely removed from the system. In their place, a proper database now stores all attendance records automatically. A browser-based dashboard replaces the spreadsheet as the place where staff view and manage attendance.

**Why this is better for the school:**
- Microsoft Excel no longer needs to be installed or open for the system to work
- The data is organized, searchable, and cannot be accidentally edited or deleted the way a spreadsheet can
- Multiple people can view the dashboard at the same time from different devices on the school Wi-Fi — not just the one computer connected to the Arduino

---

## 2. A Real Dashboard Was Built

**What the manuscript said:**
The attendance log would be viewed inside an Excel spreadsheet. There were no mockups or descriptions of a visual interface beyond the spreadsheet rows.

**What changed:**
A proper web dashboard was designed and built with four separate pages, accessible from any browser on the school network.

### Landing Page *(New — not in the manuscript)*
A welcome screen that introduces Veritime, explains what it does, and guides users to the rest of the system. It includes the Veritime branding, a preview animation of the dashboard, and a short "How It Works" walkthrough for first-time users.

### Live Dashboard *(Replaced the Excel spreadsheet)*
The main screen that staff watch during arrival time. It shows:
- The **most recently scanned student** — their photo, full name, grade, section, LRN, and a colored badge showing On Time or Late
- **Four live counters** that update automatically: Total Scans Today, On Time, Late, and Unknown cards
- A **scrolling feed** of every scan from today, with new entries appearing at the top the instant a card is tapped — no refresh button needed

### Students Page *(New — not in the manuscript)*
A page for managing the list of enrolled students. Staff can add a new student, update their details, or remove them from the system. Each student can have their photo uploaded and their RFID card assigned to their profile.

### Logs Page *(New — not in the manuscript)*
A searchable history of all attendance records ever recorded. Staff can filter by date range, search by student name or section, and download the results as a file for reporting or printing.

---

## 3. Student Profiles Were Added

**What the manuscript said:**
The system would only record the card's unique ID number, the time of tap, and whether the student was on time or late. There was no concept of linking a card to a student's name, section, photo, or LRN.

**What changed:**
Every RFID card is now linked to a complete student profile containing:
- Full name (Last Name, First Name, Middle Initial)
- Learner Reference Number (LRN)
- Grade level and section
- A profile photo

When a student taps their card, the dashboard immediately shows their name and photo — not just an anonymous card number. This makes it easy for a teacher or security guard to visually confirm who just arrived. If a card has not been registered yet, the scan is still recorded and marked as "Unknown" — no data is ever lost.

---

## 4. Updates Are Now Instant — Across Any Device

**What the manuscript said:**
Data would appear in Excel as the Arduino sent it through PLX-DAQ. This required the Excel file to be open on the specific computer the Arduino was plugged into.

**What changed:**
The dashboard now uses a live connection between the server and the browser. The moment a student taps their card, the dashboard updates on every device currently viewing it — simultaneously, with no delay, and no need to refresh the page. A teacher monitoring from their classroom tablet and the security guard at the entrance watching the desktop would both see the update at the same time.

The dashboard also shows two live status indicators:
- **Server status** — whether the system is running
- **Arduino status** — whether the card reader is physically connected and working

If the Arduino gets accidentally unplugged, the system tries to reconnect on its own every 5 seconds, and the dashboard shows the disconnected status so staff know what's happening.

---

## 5. Starting the System Is Now One Click

**What the manuscript said:**
The operation section described a multi-step manual process: install the Arduino IDE, upload the code, open Excel, set up PLX-DAQ, and manually configure the correct COM port. Each step required some technical knowledge.

**What changed:**
The entire startup process is now automated. A staff member simply double-clicks a file called `start.bat`, and the system handles everything:
1. Sets itself up on the first run (only once, automatically)
2. Detects which port the Arduino is plugged into — no manual configuration needed
3. Opens the browser directly to the Veritime welcome page
4. Starts the attendance system

No Arduino software needs to be open. No Excel needs to be running. No settings need to be adjusted. If something goes wrong (for example, the Arduino is not plugged in), a clear message is shown explaining what to check.

---

## 6. Attendance History Can Now Be Exported Properly

**What the manuscript said:**
No specific export feature was described. Sharing data meant saving or printing the Excel file as-is.

**What changed:**
The Logs page has a dedicated **Export CSV** button. When clicked, it downloads a clean spreadsheet of exactly the records currently shown — filtered by whatever date range or name search the staff member applied. This makes it straightforward to generate weekly or monthly attendance reports, share records with parents, or submit data to school administration — without needing to send the entire database.

---

## 7. The System Works Fully Offline

**What the manuscript said:**
The requirements listed an internet connection of at least 2 Mbps for the system to function, with 10 Mbps recommended for real-time monitoring.

**What changed:**
The final Veritime requires **no internet connection at all** during normal operation. Everything runs on the school's local network (or even on a single computer). This means the system continues working even during internet outages, which is important for a school that may have unreliable connectivity.

---

## 8. The 7:30 AM Cutoff Was Preserved

**What the manuscript said:**
The 7:30 AM on-time/late threshold was set inside the Arduino code. If the school needed to change it, someone would have to rewrite and re-upload the Arduino program.

**What changed:**
The 7:30 AM cutoff is still determined by the Arduino and was preserved. The improvement is that the web server also records its own timestamp for every scan, so even if the Arduino's internal clock drifts over time, the official log record uses the more reliable server time. Changing the cutoff in the future would still require updating the Arduino code, but the rest of the system adjusts automatically.

---

## Summary of Changes at a Glance

| Area | Original Manuscript | Final Veritime |
|---|---|---|
| Data storage | Microsoft Excel spreadsheet | Structured database (no Excel needed) |
| Data bridge | PLX-DAQ add-in | Python web server (automatic) |
| User interface | Excel spreadsheet rows | Multi-page browser dashboard |
| Real-time updates | Excel updated by PLX-DAQ | Instant update on all devices simultaneously |
| Student profiles | Not included | Full registry: name, LRN, grade, section, photo |
| Startup process | Multiple manual steps | One double-click to launch everything |
| COM port setup | Manual configuration | Auto-detected at startup |
| Attendance history | Raw Excel rows | Searchable and filterable Logs page |
| Data export | Save or print the Excel file | Export CSV button with date and name filters |
| Welcome / landing page | Not included | Fully designed landing page with system overview |
| Multi-device access | No — Excel on one PC only | Yes — any device on the school's Wi-Fi |
| Internet required | Yes (2–10 Mbps recommended) | No — fully offline on local network |

---

## Closing Note

The changes described in this document were not made to move away from the research goals — they were made to fulfill them more completely. The manuscript's core objective — an accurate, automated, real-time tardiness monitoring system for St. Catherine's College — is exactly what was built. The difference is that the final system is more practical and significantly more useful for everyday school operations than the Excel-based prototype originally described.

Every feature that was added exists to serve the people this system was built for: the students who tap their cards, the teachers who monitor arrivals, and the administrators who review the records.
