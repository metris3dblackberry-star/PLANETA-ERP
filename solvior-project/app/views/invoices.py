from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from app.models import Invoice, Project, Client
from app.email_helper import notify_invoice_created, notify_invoice_paid
from app import db
from datetime import datetime, date

invoices_bp = Blueprint('invoices', __name__, url_prefix='/invoices')


def next_invoice_number():
    last = Invoice.query.order_by(Invoice.id.desc()).first()
    year = datetime.now().year
    if last:
        return f"SLV-{year}-{last.id + 1:04d}"
    return f"SLV-{year}-0001"


@invoices_bp.route('/')
@login_required
def list():
    direction = request.args.get('direction', 'all')
    status = request.args.get('status', 'all')
    q = Invoice.query
    if direction != 'all':
        q = q.filter_by(direction=direction)
    if status != 'all':
        q = q.filter_by(status=status)
    invoices = q.order_by(Invoice.created_at.desc()).all()
    return render_template('invoices/list.html', invoices=invoices, direction=direction, status=status)


@invoices_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    projects = Project.query.filter_by(status='active').order_by(Project.name).all()
    clients = Client.query.filter_by(is_active=True).order_by(Client.name).all()
    if request.method == 'POST':
        amount = float(request.form.get('amount', 0))
        vat_rate = float(request.form.get('vat_rate', 27))
        amount_with_vat = amount * (1 + vat_rate / 100)

        invoice = Invoice(
            invoice_number=request.form.get('invoice_number') or next_invoice_number(),
            project_id=request.form.get('project_id'),
            client_id=request.form.get('client_id'),
            direction=request.form.get('direction'),
            amount=amount,
            vat_rate=vat_rate,
            amount_with_vat=amount_with_vat,
            description=request.form.get('description'),
            issue_date=datetime.strptime(request.form.get('issue_date'), '%Y-%m-%d').date() if request.form.get('issue_date') else date.today(),
            due_date=datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date() if request.form.get('due_date') else None,
            status=request.form.get('status', 'pending'),
            notes=request.form.get('notes'),
            created_by=current_user.id
        )
        db.session.add(invoice)
        db.session.commit()

        # Email értesítő az ügyfélnek
        if invoice.direction == 'outgoing' and not invoice.notification_sent:
            notify_invoice_created(invoice)
            invoice.notification_sent = True
            db.session.commit()

        flash(f'Számla {invoice.invoice_number} létrehozva!', 'success')
        return redirect(url_for('invoices.detail', id=invoice.id))
    return render_template('invoices/form.html', projects=projects, clients=clients,
                           next_number=next_invoice_number(), invoice=None)


@invoices_bp.route('/<int:id>')
@login_required
def detail(id):
    invoice = Invoice.query.get_or_404(id)
    return render_template('invoices/detail.html', invoice=invoice)


@invoices_bp.route('/<int:id>/mark-paid', methods=['POST'])
@login_required
def mark_paid(id):
    invoice = Invoice.query.get_or_404(id)
    invoice.status = 'paid'
    invoice.paid_date = date.today()
    db.session.commit()
    notify_invoice_paid(invoice)
    flash(f'{invoice.invoice_number} kifizetettnek jelölve!', 'success')
    return redirect(request.referrer or url_for('invoices.list'))


@invoices_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    invoice = Invoice.query.get_or_404(id)
    projects = Project.query.order_by(Project.name).all()
    clients = Client.query.filter_by(is_active=True).order_by(Client.name).all()
    if request.method == 'POST':
        invoice.project_id = request.form.get('project_id')
        invoice.client_id = request.form.get('client_id')
        invoice.direction = request.form.get('direction')
        invoice.amount = float(request.form.get('amount', 0))
        invoice.vat_rate = float(request.form.get('vat_rate', 27))
        invoice.amount_with_vat = invoice.amount * (1 + invoice.vat_rate / 100)
        invoice.description = request.form.get('description')
        invoice.status = request.form.get('status')
        invoice.notes = request.form.get('notes')
        if request.form.get('due_date'):
            invoice.due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date()
        db.session.commit()
        flash('Számla frissítve!', 'success')
        return redirect(url_for('invoices.detail', id=invoice.id))
    return render_template('invoices/form.html', projects=projects, clients=clients,
                           invoice=invoice, next_number=invoice.invoice_number)


@invoices_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    invoice = Invoice.query.get_or_404(id)
    db.session.delete(invoice)
    db.session.commit()
    flash('Számla törölve!', 'success')
    return redirect(url_for('invoices.list'))
