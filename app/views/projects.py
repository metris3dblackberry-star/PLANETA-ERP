from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from app.models import Project, Client, Invoice, SubcontractorPayment, Subcontractor, InventoryItem
from app import db
from datetime import datetime, date as date_type

projects_bp = Blueprint('projects', __name__, url_prefix='/projects')


@projects_bp.route('/')
@login_required
def list():
    status = request.args.get('status', 'all')
    q = Project.query
    if status != 'all':
        q = q.filter_by(status=status)
    projects = q.order_by(Project.created_at.desc()).all()
    return render_template('projects/list.html', projects=projects, status=status)


@projects_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    clients = Client.query.filter_by(is_active=True).order_by(Client.name).all()
    if request.method == 'POST':
        project = Project(
            name=request.form.get('name'),
            description=request.form.get('description'),
            client_id=request.form.get('client_id'),
            status=request.form.get('status', 'active'),
            contract_value=request.form.get('contract_value') or 0,
            notes=request.form.get('notes'),
            created_by=current_user.id
        )
        start = request.form.get('start_date')
        end = request.form.get('end_date')
        if start:
            project.start_date = datetime.strptime(start, '%Y-%m-%d').date()
        if end:
            project.end_date = datetime.strptime(end, '%Y-%m-%d').date()
        db.session.add(project)
        db.session.commit()
        flash(f'"{project.name}" projekt létrehozva!', 'success')
        return redirect(url_for('projects.detail', id=project.id))
    return render_template('projects/form.html', clients=clients, project=None)


@projects_bp.route('/<int:id>')
@login_required
def detail(id):
    project = Project.query.get_or_404(id)
    subcontractors = Subcontractor.query.filter_by(is_active=True).all()
    inventory_items = InventoryItem.query.order_by(InventoryItem.name).all()
    today = date_type.today().isoformat()
    invoiced_gross = sum(
        float(i.amount_with_vat or i.amount)
        for i in project.invoices if i.direction == 'outgoing'
    )
    return render_template(
        'projects/detail.html',
        project=project,
        subcontractors=subcontractors,
        inventory_items=inventory_items,
        today=today,
        invoiced_gross=invoiced_gross,
    )


@projects_bp.route('/<int:id>/quick-invoice', methods=['POST'])
@login_required
def quick_invoice(id):
    project = Project.query.get_or_404(id)
    now = datetime.today()
    base = f"SZL-{now.year}-{now.month:02d}"
    existing_count = Invoice.query.filter(Invoice.invoice_number.like(f"{base}-%")).count()
    inv_number = f"{base}-{existing_count + 1:03d}"
    while Invoice.query.filter_by(invoice_number=inv_number).first():
        existing_count += 1
        inv_number = f"{base}-{existing_count:03d}"

    raw_amount = request.form.get('amount', '0')
    vat_rate = float(request.form.get('vat_rate', 27))
    amount = float(raw_amount) if raw_amount else 0.0
    issue_str = request.form.get('issue_date')
    due_str = request.form.get('due_date')

    invoice = Invoice(
        invoice_number=inv_number,
        project_id=project.id,
        client_id=project.client_id,
        direction=request.form.get('direction', 'outgoing'),
        amount=amount,
        vat_rate=vat_rate,
        amount_with_vat=round(amount * (1 + vat_rate / 100), 2),
        description=request.form.get('description', ''),
        issue_date=datetime.strptime(issue_str, '%Y-%m-%d').date() if issue_str else now.date(),
        due_date=datetime.strptime(due_str, '%Y-%m-%d').date() if due_str else None,
        status='pending',
        created_by=current_user.id,
    )
    db.session.add(invoice)
    db.session.commit()
    flash(f'Számla {inv_number} sikeresen rögzítve!', 'success')
    return redirect(url_for('projects.detail', id=id))


@projects_bp.route('/<int:id>/quick-payment', methods=['POST'])
@login_required
def quick_payment(id):
    project = Project.query.get_or_404(id)
    now = datetime.today()
    raw_amount = request.form.get('amount', '0')
    issue_str = request.form.get('issue_date')
    due_str = request.form.get('due_date')

    payment = SubcontractorPayment(
        project_id=project.id,
        subcontractor_id=request.form.get('subcontractor_id'),
        amount=float(raw_amount) if raw_amount else 0.0,
        description=request.form.get('description', ''),
        invoice_ref=request.form.get('invoice_ref', ''),
        issue_date=datetime.strptime(issue_str, '%Y-%m-%d').date() if issue_str else now.date(),
        due_date=datetime.strptime(due_str, '%Y-%m-%d').date() if due_str else None,
        status='pending',
    )
    db.session.add(payment)
    db.session.commit()
    flash('Alvállalkozói kifizetés rögzítve!', 'success')
    return redirect(url_for('projects.detail', id=id))


@projects_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    project = Project.query.get_or_404(id)
    clients = Client.query.filter_by(is_active=True).order_by(Client.name).all()
    if request.method == 'POST':
        project.name = request.form.get('name')
        project.description = request.form.get('description')
        project.client_id = request.form.get('client_id')
        project.status = request.form.get('status')
        project.contract_value = request.form.get('contract_value') or 0
        project.notes = request.form.get('notes')
        start = request.form.get('start_date')
        end = request.form.get('end_date')
        if start:
            project.start_date = datetime.strptime(start, '%Y-%m-%d').date()
        if end:
            project.end_date = datetime.strptime(end, '%Y-%m-%d').date()
        db.session.commit()
        flash('Projekt frissítve!', 'success')
        return redirect(url_for('projects.detail', id=project.id))
    return render_template('projects/form.html', clients=clients, project=project)


@projects_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    project = Project.query.get_or_404(id)
    db.session.delete(project)
    db.session.commit()
    flash('Projekt törölve!', 'success')
    return redirect(url_for('projects.list'))
