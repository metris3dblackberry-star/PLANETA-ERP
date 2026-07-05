from datetime import date, timedelta

from app import db
from app.models import Invoice, Project


def update_overdue_invoices():
    """Mark pending invoices with past due dates as overdue."""
    Invoice.query.filter(
        Invoice.status == 'pending',
        Invoice.due_date < date.today(),
        Invoice.due_date.isnot(None),
    ).update({'status': 'overdue'})
    db.session.commit()


def deadline_alert_projects(days=14):
    """Return dashboard rows for active projects nearing or missing deadline."""
    today = date.today()
    soon = today + timedelta(days=days)
    projects = Project.query.filter(
        Project.status == 'active',
        Project.end_date.isnot(None),
        Project.end_date <= soon,
    ).order_by(Project.end_date).all()

    rows = []
    for project in projects:
        state = project_deadline_state(project)
        if state:
            rows.append({
                'project': project,
                'state': state,
            })
    return rows


def project_deadline_state(project):
    """Return a dashboard badge payload describing deadline urgency."""
    if not project.end_date:
        return None

    delta = (project.end_date - date.today()).days
    if delta < 0:
        return {
            'level': 'danger',
            'label': 'Lejárt',
            'days': abs(delta),
        }
    if delta <= 3:
        return {
            'level': 'danger',
            'label': 'Közelgő határidő',
            'days': delta,
        }
    if delta <= 7:
        return {
            'level': 'warning',
            'label': 'Közeleg',
            'days': delta,
        }
    if delta <= 14:
        return {
            'level': 'info',
            'label': 'Figyelendő',
            'days': delta,
        }
    return {
        'level': 'success',
        'label': 'Rendben',
        'days': delta,
    }
