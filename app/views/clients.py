from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required
from app.models import Client
from app import db

clients_bp = Blueprint('clients', __name__, url_prefix='/clients')

@clients_bp.route('/')
@login_required
def list():
    q = (request.args.get('q') or '').strip()
    query = Client.query.filter_by(is_active=True)
    if q:
        like = f"%{q}%"
        query = query.filter(
            Client.name.ilike(like)
            | Client.email.ilike(like)
            | Client.phone.ilike(like)
            | Client.contact_person.ilike(like)
            | Client.tax_number.ilike(like)
        )
    clients = query.order_by(Client.name).all()
    return render_template('clients/list.html', clients=clients, q=q)

@clients_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    if request.method == 'POST':
        c = Client(
            name=request.form.get('name'),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            address=request.form.get('address'),
            tax_number=request.form.get('tax_number'),
            contact_person=request.form.get('contact_person'),
            notes=request.form.get('notes')
        )
        db.session.add(c)
        db.session.commit()
        flash(f'{c.name} létrehozva!', 'success')
        return redirect(url_for('clients.list'))
    return render_template('clients/form.html', client=None)

@clients_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    c = Client.query.get_or_404(id)
    if request.method == 'POST':
        c.name = request.form.get('name')
        c.email = request.form.get('email')
        c.phone = request.form.get('phone')
        c.address = request.form.get('address')
        c.tax_number = request.form.get('tax_number')
        c.contact_person = request.form.get('contact_person')
        c.notes = request.form.get('notes')
        db.session.commit()
        flash('Ügyfél frissítve!', 'success')
        return redirect(url_for('clients.list'))
    return render_template('clients/form.html', client=c)

@clients_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    c = Client.query.get_or_404(id)
    c.is_active = False
    db.session.commit()
    flash('Ügyfél törölve!', 'success')
    return redirect(url_for('clients.list'))
