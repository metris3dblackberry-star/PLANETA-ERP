from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from app.models import Project, Client, Invoice, SubcontractorPayment, ProjectInventory, Subcontractor, InventoryItem
from app import db
from datetime import datetime

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
    return render_template(
        'projects/detail.html',
        project=project,
        subcontractors=subcontractors,
        inventory_items=inventory_items,
    )


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
