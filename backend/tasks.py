"""Celery task implementations.

Only loaded by the worker/beat processes (`celery -A tasks worker`,
`celery -A tasks beat`) — never by the Flask web server, which only enqueues
tasks via `celery_app.celery.send_task(...)` and so never needs a Flask app
of its own for this. Each task runs inside a Flask app context (via
ContextTask below) so it can use `db`, `mail`, and `cache` normally.
"""

import csv
import os
from datetime import datetime, timedelta, timezone

from celery.utils.log import get_task_logger
from flask import render_template_string
from flask_mail import Message

from celery_app import celery
from app import create_app
from extensions import db, cache, mail
from exports import export_cache_key
from notifications import get_notifier
from models.drive import PlacementDrive, DriveStatus
from models.application import Application, ApplicationStatus
from models.student_profile import StudentProfile

logger = get_task_logger(__name__)

flask_app = create_app()


class ContextTask(celery.Task):
    def __call__(self, *args, **kwargs):
        with flask_app.app_context():
            return self.run(*args, **kwargs)


celery.Task = ContextTask


def _aware(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _eligible_unapplied_count(drive):
    applied_student_ids = {a.student_id for a in drive.applications}
    branches = set(drive.eligible_branches_list())
    students = StudentProfile.query.filter_by(grad_year=drive.eligible_grad_year).all()
    return sum(
        1
        for s in students
        if s.id not in applied_student_ids and s.branch in branches and s.cgpa >= drive.min_cgpa
    )


@celery.task(name="tasks.send_deadline_reminders")
def send_deadline_reminders():
    """Daily (Celery Beat): notify about drives closing within the next
    REMINDER_WINDOW_HOURS, via the Google Chat webhook notifier."""
    window_hours = flask_app.config.get("REMINDER_WINDOW_HOURS", 24)
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(hours=window_hours)

    closing_soon = [
        d
        for d in PlacementDrive.query.filter_by(status=DriveStatus.APPROVED).all()
        if d.application_deadline and now <= _aware(d.application_deadline) <= horizon
    ]

    if not closing_soon:
        logger.info("No drives closing within %sh; skipping reminder.", window_hours)
        return {"drives_notified": 0}

    lines = ["*Upcoming placement drive deadlines*"]
    for d in closing_soon:
        hours_left = int((_aware(d.application_deadline) - now).total_seconds() // 3600)
        unapplied = _eligible_unapplied_count(d)
        lines.append(
            f"- *{d.job_title}* @ {d.company.company_name}: closes in ~{hours_left}h "
            f"({unapplied} eligible student(s) haven't applied yet)"
        )

    get_notifier().send("\n".join(lines))
    return {"drives_notified": len(closing_soon)}


@celery.task(name="tasks.send_monthly_activity_report")
def send_monthly_activity_report():
    """Monthly (Celery Beat, 1st of month): HTML email to the admin
    summarizing last month's drives, applicants, and selections."""
    now = datetime.now(timezone.utc)
    first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    first_of_last_month = (first_of_this_month - timedelta(days=1)).replace(day=1)

    drives = [
        d
        for d in PlacementDrive.query.all()
        if d.created_at and first_of_last_month <= _aware(d.created_at) < first_of_this_month
    ]
    drive_ids = {d.id for d in drives}
    applications = Application.query.filter(Application.drive_id.in_(drive_ids)).all() if drive_ids else []
    selected = [a for a in applications if a.status == ApplicationStatus.SELECTED]

    html = render_template_string(
        """
        <h2>Placement Activity Report &mdash; {{ month_label }}</h2>
        <p>Drives conducted: <strong>{{ drives|length }}</strong></p>
        <p>Students applied: <strong>{{ applications|length }}</strong></p>
        <p>Students selected: <strong>{{ selected|length }}</strong></p>
        <table border="1" cellpadding="6" cellspacing="0">
          <tr><th>Drive</th><th>Company</th><th>Applicants</th><th>Selected</th></tr>
          {% for d in drives %}
          <tr>
            <td>{{ d.job_title }}</td>
            <td>{{ d.company.company_name }}</td>
            <td>{{ d.applications|length }}</td>
            <td>{{ d.applications|selectattr('status', 'equalto', 'selected')|list|length }}</td>
          </tr>
          {% endfor %}
        </table>
        """,
        month_label=first_of_last_month.strftime("%B %Y"),
        drives=drives,
        applications=applications,
        selected=selected,
    )

    message = Message(
        subject=f"PPA Monthly Activity Report — {first_of_last_month.strftime('%B %Y')}",
        recipients=[flask_app.config["ADMIN_NOTIFICATION_EMAIL"]],
        html=html,
    )
    mail.send(message)
    return {"drives": len(drives), "applied": len(applications), "selected": len(selected)}


@celery.task(name="tasks.export_student_applications_csv")
def export_student_applications_csv(student_id):
    """Async, user-triggered: build a CSV of a student's applications and
    mark the export ready for download (polled via /applications/export/status)."""
    profile = db.session.get(StudentProfile, student_id)
    if not profile:
        cache.set(export_cache_key(student_id), {"status": "failed", "error": "Student not found"}, timeout=3600)
        return {"status": "failed"}

    applications = (
        Application.query.filter_by(student_id=student_id)
        .order_by(Application.application_date.desc())
        .all()
    )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"applications_student_{student_id}_{timestamp}.csv"
    filepath = os.path.join(flask_app.config["REPORTS_FOLDER"], filename)

    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Student ID", "Company", "Drive Title", "Status", "Application Date", "Interview Date"])
        for a in applications:
            writer.writerow(
                [
                    student_id,
                    a.drive.company.company_name,
                    a.drive.job_title,
                    a.status,
                    a.application_date.isoformat() if a.application_date else "",
                    a.interview_date.isoformat() if a.interview_date else "",
                ]
            )

    status_payload = {"status": "ready", "filename": filename, "created_at": timestamp}
    cache.set(export_cache_key(student_id), status_payload, timeout=3600)
    return status_payload
