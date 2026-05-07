from app.models import Invoice, Project
from app import db
from datetime import date, timedelta


def update_overdue_invoices():
    """Mark pending invoices with past due_date as overdue."""
    Invoice.query.filter(
        Invoice.status == 'pending',
        Invoice.due_date < date.today(),
        Invoice.due_date.isnot(None)
    ).update({'status': 'overdue'})
    db.session.commit()


def deadline_alert_projects(days=14):
    """Return active projects whose end_date is within `days` days (including overdue)."""
    today = date.today()
    soon = today + timedelta(days=days)
    return Project.query.filter(
        Project.status == 'active',
        Project.end_date.isnot(None),
        Project.end_date <= soon,
    ).order_by(Project.end_date).all()


def project_deadline_state(project):
    """Return a Bootstrap colour name based on how close the project deadline is."""
    if not project.end_date:
        return 'secondary'
    delta = (project.end_date - date.today()).days
    if delta < 0:
        return 'danger'    # lejárt
    elif delta <= 3:
        return 'danger'
    elif delta <= 7:
        return 'warning'
    elif delta <= 14:
        return 'info'
    return 'success'
