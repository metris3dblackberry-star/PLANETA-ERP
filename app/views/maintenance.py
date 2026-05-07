from app.models import Invoice
from app import db
from datetime import date


def update_overdue_invoices():
    """Mark pending invoices with past due_date as overdue."""
    Invoice.query.filter(
        Invoice.status == 'pending',
        Invoice.due_date < date.today(),
        Invoice.due_date.isnot(None)
    ).update({'status': 'overdue'})
    db.session.commit()
