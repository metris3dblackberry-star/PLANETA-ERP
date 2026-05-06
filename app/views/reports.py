from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required
from app.models import Project, Invoice, SubcontractorPayment, Client, Subcontractor
from app import db
from sqlalchemy import func

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')


@reports_bp.route('/')
@login_required
def index():
    # Per-client összesítő
    clients = Client.query.filter_by(is_active=True).all()
    client_stats = []
    for c in clients:
        invoiced = sum(float(i.amount) for p in c.projects for i in p.invoices if i.direction == 'outgoing')
        received = sum(float(i.amount) for p in c.projects for i in p.invoices if i.direction == 'outgoing' and i.status == 'paid')
        client_stats.append({
            'client': c,
            'invoiced': invoiced,
            'received': received,
            'outstanding': invoiced - received,
            'project_count': len(c.projects)
        })

    # Per-subcontractor összesítő
    subs = Subcontractor.query.filter_by(is_active=True).all()
    sub_stats = []
    for s in subs:
        total = sum(float(p.amount) for p in s.payments)
        paid = sum(float(p.amount) for p in s.payments if p.status == 'paid')
        sub_stats.append({
            'sub': s,
            'total': total,
            'paid': paid,
            'pending': total - paid
        })

    return render_template('reports/index.html',
                           client_stats=client_stats,
                           sub_stats=sub_stats)


@reports_bp.route('/project/<int:id>')
@login_required
def project_report(id):
    project = Project.query.get_or_404(id)
    return render_template('reports/project.html', project=project)
