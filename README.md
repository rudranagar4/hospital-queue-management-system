# Hospital Smart Queue Management System

A web-based **Hospital Smart Queue Management System** designed to eliminate long physical waiting lines. Patients can register and take digital queue tokens remotely, track live estimated waiting times and positions in real-time, while hospital administrators triage, manage departments, and dispatch patients via a dual-queue algorithmic architecture.

---

## 1. System Architecture & Queue Data Structures

The system handles two distinct categories of hospital cases with separate, optimized data structures:

| Case Category | In-Memory Data Structure | Scheduling Rule | Algorithmic Complexity |
|---------------|--------------------------|-----------------|------------------------|
| **Normal Case** | `collections.deque` (FIFO) | First-Come, First-Served | $O(1)$ Enqueue & Dequeue |
| **Emergency Case** | `heapq` (Min-Heap Priority Queue) | Highest severity served first; equal severity ordered by arrival timestamp | $O(\log N)$ Insert & Pop |

### Dual Queue Algorithm & Fairness Rule
- **Priority Dispatch:** Emergency patients are always served before normal routine visits.
- **Min-Heap Keying:** Each emergency patient is stored as a tuple `(severity, arrival_timestamp, token_id)`.
  - Severity 1 = **Critical**
  - Severity 2 = **Serious**
  - Severity 3 = **Urgent**
  - Lower severity number = higher priority. If severities are identical, the earlier arrival timestamp takes precedence.
- **Starvation Prevention (Fairness Rule):** Under high trauma load, routine patients could face indefinite starvation. The system enforces a configurable fairness rule (`MAX_CONSECUTIVE_EMERGENCY = 5`): after every 5 consecutive emergency consultations in a department, 1 waiting normal patient is guaranteed immediate consultation if present.
- **Wait Time Estimation:** Calculated as `estimated_wait = patients_ahead * average_consultation_time` (default 10 mins, configurable in `config.py`).
- **Database Persistence & Crash Recovery:** SQLite via SQLAlchemy is the source of truth. Upon server startup or restart, `queue_manager.rebuild_from_db(app)` reconstructs the in-memory min-heaps and FIFO deques from waiting tokens in order.

---

## 2. Tech Stack

- **Backend:** Python 3 + Flask
- **Database:** SQLite with SQLAlchemy ORM
- **Authentication:** Flask-Login + Werkzeug password hashing (`generate_password_hash` / `check_password_hash`)
- **Queue Engine:** Python `heapq` (min-heap) & `collections.deque` (FIFO)
- **Frontend:** HTML5, CSS3, Bootstrap 5.3, Bootstrap Icons, Web Audio API Synth chime
- **CSRF Protection:** Flask-WTF CSRF tokens on forms and AJAX headers
- **Testing:** Pytest

---

## 3. Project Structure

```
adc/
├── app.py                      # Flask application factory, routes, and queue startup rebuild
├── config.py                   # Central configurations (fairness limit, wait times, DB URI)
├── models.py                   # SQLAlchemy Models: User, Department, Doctor, Token
├── queue_manager.py            # DepartmentQueue & QueueManager (deque + heapq + fairness)
├── seed.py                     # Database initialization and demo accounts seed script
├── requirements.txt            # Python dependencies
├── routes/
│   ├── __init__.py
│   ├── auth.py                 # Patient & Admin authentication and role decorators
│   ├── patient.py              # Patient token booking, status view, cancellation, history
│   ├── admin.py                # Operations command, Call Next, walk-in admissions, stats
│   └── api.py                  # Real-time JSON endpoints for 5s auto-refresh
├── templates/
│   ├── base.html               # Responsive navigation, theme switching, flash alerts
│   ├── index.html              # Landing page with live ticker and architecture explainer
│   ├── patient/
│   │   ├── login.html          # Patient portal sign-in with demo shortcut
│   │   ├── register.html       # Patient account registration
│   │   ├── dashboard.html      # Active token tracker, status stepper, booking modal
│   │   └── history.html        # Consultation history table
│   └── admin/
│       ├── login.html          # Administrator login portal
│       ├── dashboard.html      # Operations command center with dual queues & Now Serving
│       ├── departments.html    # Clinical departments and doctors CRUD
│       ├── patients.html       # Patient search and registry
│       └── stats.html          # KPIs, wait times, and emergency vs normal distribution
├── static/
│   ├── css/
│   │   ├── style.css           # Global typography, glassmorphism, fluid keyframes
│   │   ├── patient.css         # Patient theme (clean blue / medical cyan)
│   │   └── admin.css           # Admin theme (dark slate / emerald command center)
│   └── js/
│       ├── main.js             # Web Audio chime synthesizer & flash dismisser
│       ├── patient.js          # Patient token auto-polling & call alert sound
│       └── admin.js            # Admin queue auto-refresh & keyboard shortcuts (Shift+C)
└── tests/
    ├── __init__.py
    ├── test_queue_manager.py   # Unit tests for FIFO, heapq, fairness, and removal
    ├── test_integration.py     # Role isolation and DB rebuild verification
    └── test_full_workflow.py   # Full lifecycle booking, priority triage, and API test
```

---

## 4. Setup and Installation

### 4.1 Prerequisites
- Python 3.10+ installed
- Virtual environment (`venv`)

### 4.2 Installation Steps

1. **Activate virtual environment:**
   ```powershell
   # Windows PowerShell
   .\.venv\Scripts\Activate.ps1
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Seed the database:**
   Initializes tables, default departments, doctors, administrator, and demo patient:
   ```bash
   python seed.py
   ```

4. **Run the application:**
   ```bash
   python app.py
   ```
   The application will be live at: **`http://127.0.0.1:5000`**

---

## 5. Default Credentials for Testing

| Role | Portal URL | Email | Password |
|------|------------|-------|----------|
| **Hospital Administrator** | `/admin/login` | `admin@hospital.com` | `admin123` |
| **Demo Patient** | `/patient/login` | `patient@hospital.com` | `PatientPassword123!` |

*(Both login screens include a convenient one-click **"Demo Fill"** button for rapid testing).*

---

## 6. Running Tests

The test suite validates all required conditions:
- Emergency patients arriving after normal patients jump ahead
- Severity 1 (Critical) served before Severity 2 (Serious) & Severity 3 (Urgent)
- Equal severity emergency cases resolved chronologically
- Normal patients served strictly FIFO
- Starvation prevention fairness rule triggers after 5 consecutive emergencies
- Cancelled tokens cleanly update positions and queues
- Unauthenticated / wrong-role users cannot cross patient and admin barriers
- Server restart correctly rebuilds queues from SQLite

Execute all tests:
```bash
pytest -v
```

---

## 7. Key Features & Visual Design

- **Two Distinct Visual Themes:**
  - **Patient Panel:** Clean medical blue/cyan aesthetic with card glassmorphism.
  - **Admin Command Center:** Dark high-tech operations dashboard with emerald accents.
- **Audio Chime Notification:** Built using browser Web Audio API oscillator synthesis; chimes when a patient's token is called.
- **Emergency Pulsing Highlights:** Severity badges and emergency queue rows glow with pulsing red accents.
- **Live Auto-Refresh:** Dashboards poll `/api/queue/<dept_id>` every 5 seconds for seamless real-time coordination without full page reloads.
- **Now Serving Display:** Prominent status card showing current consultation with quick actions (`Start Consultation`, `Complete`, `Skip`, `No-Show`).
- **Walk-In Registration:** Allows triage desk staff to instantly admit walk-in patients directly into the normal or priority queues.
