from flask import Blueprint, render_template
from flask_login import login_required
from app.models import Project, Invoice, Client, Subcontractor, SubcontractorPayment
from app import db
from sqlalchemy import func
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def dashboard():
    # Stats
    total_projects = Project.query.filter_by(status='active').count()
    total_clients = Client.query.filter_by(is_active=True).count()
    total_subcontractors = Subcontractor.query.filter_by(is_active=True).count()

    # Pénzügyi összesítők
    total_invoiced = db.session.query(
        func.sum(Invoice.amount)
    ).filter_by(direction='outgoing').scalar() or 0

    total_received = db.session.query(
        func.sum(Invoice.amount)
    ).filter(Invoice.direction == 'outgoing', Invoice.status == 'paid').scalar() or 0

    total_outstanding = float(total_invoiced) - float(total_received)

    total_subcontractor_cost = db.session.query(
        func.sum(SubcontractorPayment.amount)
    ).scalar() or 0

    total_subcontractor_paid = db.session.query(
        func.sum(SubcontractorPayment.amount)
    ).filter_by(status='paid').scalar() or 0

    # Legutóbbi számlák
    recent_invoices = Invoice.query.order_by(Invoice.created_at.desc()).limit(5).all()

    # Lejárt számlák
    overdue_invoices = Invoice.query.filter(
        Invoice.status == 'pending',
        Invoice.due_date < date.today(),
        Invoice.direction == 'outgoing'
    ).count()

    # Aktív projektek
    active_projects = Project.query.filter_by(status='active').order_by(
        Project.created_at.desc()
    ).limit(5).all()

    # Cash flow havi bontás (utolsó 6 hónap)
    cashflow_data = []
    for i in range(5, -1, -1):
        month_start = (datetime.now() - relativedelta(months=i)).replace(day=1)
        month_end = (month_start + relativedelta(months=1))
        month_income = db.session.query(func.sum(Invoice.amount)).filter(
            Invoice.direction == 'outgoing',
            Invoice.status == 'paid',
            Invoice.paid_date >= month_start.date(),
            Invoice.paid_date < month_end.date()
        ).scalar() or 0
        month_expense = db.session.query(func.sum(SubcontractorPayment.amount)).filter(
            SubcontractorPayment.status == 'paid',
            SubcontractorPayment.paid_date >= month_start.date(),
            SubcontractorPayment.paid_date < month_end.date()
        ).scalar() or 0
        cashflow_data.append({
            'month': month_start.strftime('%Y %b'),
            'income': float(month_income),
            'expense': float(month_expense),
            'profit': float(month_income) - float(month_expense)
        })

    return render_template('main/dashboard.html',
        total_projects=total_projects,
        total_clients=total_clients,
        total_subcontractors=total_subcontractors,
        total_invoiced=float(total_invoiced),
        total_received=float(total_received),
        total_outstanding=total_outstanding,
        total_subcontractor_cost=float(total_subcontractor_cost),
        total_subcontractor_paid=float(total_subcontractor_paid),
        recent_invoices=recent_invoices,
        overdue_invoices=overdue_invoices,
        active_projects=active_projects,
        cashflow_data=cashflow_data
    )
