# Placement Portal Application (PPA)

A role-based web app for campus recruitment — connecting an Institute
Admin, Companies, and Students. Built to run entirely on localhost, tuned
for an 8 GB Ubuntu machine.

## Tech stack

- **Backend:** Flask
- **Frontend:** Vue 3 (CDN, no build step) — `.vue` single-file components loaded at runtime via `vue3-sfc-loader`, entry point is a Jinja2 template
- **Styling:** Bootstrap 5 (CDN)
- **Database:** SQLite, schema created programmatically via SQLAlchemy (never a GUI tool) — `backend/seed.py` / `flask create-admin`
- **Caching:** Redis, via Flask-Caching
- **Background/scheduled jobs:** Celery + Celery Beat, Redis as broker & result backend
- **Auth:** Flask-Login session-based auth, single `User` model with a `role` field (`admin` / `company` / `student`)
- **Email:** Flask-Mail, sent to a local debug SMTP server for the demo

## Project layout

```
Placement/
├── backend/
│   ├── routes/                 # one blueprint per role
│   │   ├── auth_routes.py      # register/login/logout, /api/auth
│   │   ├── admin_routes.py     # dashboard, approvals, blacklist, stats, /api/admin
│   │   ├── company_routes.py   # profile, drives, applicants, /api/company
│   │   └── student_routes.py   # profile, resume, drives, applications, /api/student
│   ├── models/                 # SQLAlchemy models
│   │   ├── user.py             # unified User (role: admin/company/student)
│   │   ├── company.py
│   │   ├── student_profile.py
│   │   ├── drive.py            # PlacementDrive
│   │   └── application.py
│   ├── templates/index.html    # Jinja2 entry point, boots the Vue app
│   ├── uploads/resumes/        # uploaded student resumes
│   ├── reports/                # generated CSV exports
│   ├── instance/               # SQLite DB file (gitignored)
│   ├── app.py                  # Flask app factory / entry point (port 8001)
│   ├── config.py                # all env-driven config
│   ├── extensions.py            # db, login_manager, cache, mail
│   ├── decorators.py            # roles_required() route guard
│   ├── validation.py            # shared input validators
│   ├── caching.py                # Redis cache-key/versioning helpers
│   ├── celery_app.py             # lightweight Celery producer (imported by the Flask app to enqueue jobs)
│   ├── tasks.py                  # Celery task implementations (run by worker/beat only)
│   ├── notifications.py          # notifier abstraction (Google Chat webhook)
│   ├── exports.py                # shared cache-key format for CSV export status
│   ├── seed.py                   # creates DB schema + seeds the admin user
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    └── src/components/
        ├── App.vue               # root shell, session check, role routing
        ├── auth/                 # Login, RegisterStudent, RegisterCompany
        ├── admin/AdminDashboard.vue
        ├── company/CompanyDashboard.vue
        └── student/StudentDashboard.vue
```

## Prerequisites (Ubuntu, 8 GB RAM)

- Python 3.10+ (developed against 3.12)
- Redis server
- A modern browser (Vue is loaded from CDN at runtime, so an internet connection is needed for the CDN scripts — everything else is local)

Install Redis if you don't have it:

```bash
sudo apt update
sudo apt install redis-server
sudo systemctl enable --now redis-server   # or: redis-server --daemonize yes
redis-cli ping   # should print PONG
```

## First-time setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # adjust values if you want (webhook URL, ports, etc.)

python seed.py                 # creates the SQLite schema + the admin user
```

The seeded admin credentials come from `.env` (`ADMIN_EMAIL` / `ADMIN_PASSWORD`, defaults `admin@ppa.local` / `ChangeMe123!`). There is no admin registration route — only this seeded account, or a fresh one via `flask create-admin`.

## Running it locally

You need **4 processes** running at once (each in its own terminal, all from `backend/` with the venv active). This app deliberately keeps this to the minimum needed for the full feature set — no heavier services than a Flask dev server + Redis + two lightweight Celery processes + a debug mail server.

**1. Redis** (if not already running as a service):
```bash
redis-server
```

**2. Flask app** — runs on port **8001** (port 8000 is assumed taken; override via `PORT` in `.env`):
```bash
cd backend
source .venv/bin/activate
python app.py
```
Open http://localhost:8001

**3. Celery worker** (handles the async CSV export + runs scheduled jobs when triggered by beat):
```bash
cd backend
source .venv/bin/activate
celery -A tasks worker --loglevel=info
```

**4. Celery Beat** (fires the scheduled jobs — daily deadline reminders, monthly activity report):
```bash
cd backend
source .venv/bin/activate
celery -A tasks beat --loglevel=info
```

**5. (Optional) Local debug SMTP server** — lets you see the monthly activity report email without a real mail server. Python 3.12 removed the stdlib `smtpd` module, so this project uses `aiosmtpd` instead (already in `requirements.txt`):
```bash
cd backend
source .venv/bin/activate
python -m aiosmtpd -n -l localhost:1025
```
Any message sent to it is just printed to its terminal — nothing is actually delivered anywhere, which is exactly what you want for a local demo.

You can skip step 5 if you don't need to see the monthly report; the task will simply fail to connect (logged, not fatal to the worker) until a server is listening on port 1025.

### Quick health check

```bash
redis-cli ping                                    # PONG
curl -s http://localhost:8001/ | grep title        # <title>Placement Portal</title>
```

## Configuration (`backend/.env`)

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `8001` | Flask server port |
| `SECRET_KEY` | dev value | Flask session signing — change for anything beyond local demo |
| `DATABASE_URL` | `sqlite:///instance/ppa.db` | SQLAlchemy DB URI |
| `REDIS_URL` | `redis://localhost:6379/0` | Cache backend |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | same as `REDIS_URL` | Celery |
| `MAIL_SERVER` / `MAIL_PORT` | `localhost` / `1025` | Points at the local `aiosmtpd` debug server |
| `ADMIN_NOTIFICATION_EMAIL` | `admin@localhost` | Recipient of the monthly activity report |
| `GOOGLE_CHAT_WEBHOOK_URL` | empty | If set, deadline reminders post here; if empty, they're just logged (`LoggingNotifier`) |
| `REMINDER_WINDOW_HOURS` | `24` | How far ahead the daily reminder job looks for closing drives |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` / `ADMIN_NAME` | `admin@ppa.local` / `ChangeMe123!` / `Placement Admin` | Seeded admin account (used by `seed.py` and `flask create-admin`) |

## Feature summary

**Admin** (seeded, no self-registration): dashboard with counts by status, approve/reject companies and drives, search students/companies, blacklist/deactivate accounts, placement stats (by branch/company).

**Company** (self-register → pending admin approval): profile management, create drives (locked until approved), view/manage applicants, shortlist → select/reject, schedule interviews.

**Student** (self-register): browse approved drives with eligibility-based filtering (branch/CGPA/grad year), apply (duplicate-blocked, eligibility-enforced), live application status, placement history, resume upload, async CSV export of application history.

**Background jobs** (Celery + Beat): daily deadline reminders (Google Chat webhook, or logged locally), monthly HTML activity report emailed to the admin, async CSV export triggered from the student dashboard (poll-based "ready" notification).

**Caching**: dashboards and drive listings are cached in Redis for 60s, with a version-counter invalidation strategy so writes (approvals, applications, profile edits) are reflected immediately rather than waiting out the TTL.

## Troubleshooting

- **`redis-cli ping` fails** — Redis isn't running; `sudo systemctl start redis-server` or `redis-server` in a terminal.
- **Celery worker can't connect** — check `redis-cli ping` first; Celery logs the broker URL it's using on startup.
- **Monthly report task errors on send** — the local `aiosmtpd` debug server (step 5) isn't running; start it or ignore (task failure there doesn't affect anything else).
- **Port 8001 already in use** — set `PORT` in `.env` to something else and restart `python app.py`.
- **Resetting the database** — stop the Flask app, delete `backend/instance/ppa.db`, run `python seed.py` again.
