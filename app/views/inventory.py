from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required
from app.models import InventoryItem, ProjectInventory, Project
from app import db
import openpyxl
import io

inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory')


@inventory_bp.route('/')
@login_required
def list():
    q = (request.args.get('q') or '').strip()
    category = request.args.get('category', 'all')
    query = InventoryItem.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            InventoryItem.name.ilike(like)
            | InventoryItem.sku.ilike(like)
            | InventoryItem.category.ilike(like)
        )
    if category != 'all':
        query = query.filter(InventoryItem.category == category)
    items = query.order_by(InventoryItem.name).all()
    categories = [
        row[0] for row in db.session.query(InventoryItem.category)
        .filter(InventoryItem.category.isnot(None), InventoryItem.category != '')
        .distinct()
        .order_by(InventoryItem.category)
        .all()
    ]
    return render_template('inventory/list.html', items=items, q=q, category=category, categories=categories)


@inventory_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    if request.method == 'POST':
        item = InventoryItem(
            name=request.form.get('name'),
            sku=request.form.get('sku'),
            unit=request.form.get('unit'),
            unit_price=float(request.form.get('unit_price') or 0),
            total_stock=float(request.form.get('total_stock') or 0),
            category=request.form.get('category'),
            notes=request.form.get('notes')
        )
        db.session.add(item)
        db.session.commit()
        flash(f'{item.name} hozzáadva!', 'success')
        return redirect(url_for('inventory.list'))
    return render_template('inventory/form.html', item=None)


@inventory_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    item = InventoryItem.query.get_or_404(id)
    if request.method == 'POST':
        item.name = request.form.get('name')
        item.sku = request.form.get('sku')
        item.unit = request.form.get('unit')
        item.unit_price = float(request.form.get('unit_price') or 0)
        item.total_stock = float(request.form.get('total_stock') or 0)
        item.category = request.form.get('category')
        item.notes = request.form.get('notes')
        db.session.commit()
        flash('Készlet tétel frissítve!', 'success')
        return redirect(url_for('inventory.list'))
    return render_template('inventory/form.html', item=item)


@inventory_bp.route('/import-excel', methods=['GET', 'POST'])
@login_required
def import_excel():
    if request.method == 'POST':
        file = request.files.get('excel_file')
        if not file:
            flash('Nincs fájl kiválasztva!', 'danger')
            return redirect(request.url)
        try:
            wb = openpyxl.load_workbook(io.BytesIO(file.read()))
            ws = wb.active
            count = 0
            for row in ws.iter_rows(min_row=2, values_only=True):
                if not row[0]:
                    continue
                item = InventoryItem(
                    name=str(row[0]),
                    sku=str(row[1]) if row[1] else None,
                    unit=str(row[2]) if row[2] else 'db',
                    unit_price=float(row[3]) if row[3] else 0,
                    total_stock=float(row[4]) if row[4] else 0,
                    category=str(row[5]) if len(row) > 5 and row[5] else None
                )
                db.session.add(item)
                count += 1
            db.session.commit()
            flash(f'{count} tétel importálva!', 'success')
        except Exception as e:
            flash(f'Import hiba: {str(e)}', 'danger')
        return redirect(url_for('inventory.list'))
    return render_template('inventory/import.html')


@inventory_bp.route('/project/<int:project_id>/add', methods=['POST'])
@login_required
def add_to_project(project_id):
    project = Project.query.get_or_404(project_id)
    item_id = request.form.get('item_id')
    qty_planned = float(request.form.get('quantity_planned') or 0)
    existing = ProjectInventory.query.filter_by(
        project_id=project_id, item_id=item_id
    ).first()
    if existing:
        existing.quantity_planned = qty_planned
    else:
        pi = ProjectInventory(
            project_id=project_id,
            item_id=item_id,
            quantity_planned=qty_planned,
            quantity_used=0
        )
        db.session.add(pi)
    db.session.commit()
    flash('Készlet hozzáadva a projekthez!', 'success')
    return redirect(url_for('projects.detail', id=project_id))


@inventory_bp.route('/project-item/<int:id>/update', methods=['POST'])
@login_required
def update_usage(id):
    pi = ProjectInventory.query.get_or_404(id)
    pi.quantity_used = float(request.form.get('quantity_used') or 0)
    db.session.commit()
    flash('Felhasználás frissítve!', 'success')
    return redirect(url_for('projects.detail', id=pi.project_id))
