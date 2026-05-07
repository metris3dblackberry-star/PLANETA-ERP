from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from app.models import Subcontractor, SubcontractorPayment, Project
from app.email_helper import notify_subcontractor_payment
from app import db
from datetime import datetime, date

subcontractors_bp = Blueprint('subcontractors', __name__, url_prefix='/subcontractors')


@subcontractors_bp.route('/')
@login_required
def list():
    q = (request.args.get('q') or '').strip()
    query = Subcontractor.query.filter_by(is_active=True)
    if q:
        like = f"%{q}%"
        query = query.filter(
            Subcontractor.name.ilike(like)
            | Subcontractor.email.ilike(like)
            | Subcontractor.phone.ilike(like)
            | Subcontractor.contact_person.ilike(like)
            | Subcontractor.specialty.ilike(like)
            | Subcontractor.tax_number.ilike(like)
        )
    subs = query.order_by(Subcontractor.name).all()
    return render_template('subcontractors/list.html', subcontractors=subs, q=q)


@subcontractors_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    if request.method == 'POST':
        s = Subcontractor(
            name=request.form.get('name'),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            address=request.form.get('address'),
            tax_number=request.form.get('tax_number'),
            contact_person=request.form.get('contact_person'),
            specialty=request.form.get('specialty'),
            notes=request.form.get('notes')
        )
        db.session.add(s)
        db.session.commit()
        flash(f'{s.name} létrehozva!', 'success')
        return redirect(url_for('subcontractors.list'))
    return render_template('subcontractors/form.html', subcontractor=None)


@subcontractors_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    s = Subcontractor.query.get_or_404(id)
    if request.method == 'POST':
        s.name = request.form.get('name')
        s.email = request.form.get('email')
        s.phone = request.form.get('phone')
        s.address = request.form.get('address')
        s.tax_number = request.form.get('tax_number')
        s.contact_person = request.form.get('contact_person')
        s.specialty = request.form.get('specialty')
        s.notes = request.form.get('notes')
        db.session.commit()
        flash('Alvállalkozó frissítve!', 'success')
        return redirect(url_for('subcontractors.list'))
    return render_template('subcontractors/form.html', subcontractor=s)


@subcontractors_bp.route('/payments/new', methods=['GET', 'POST'])
@login_required
def new_payment():
    projects = Project.query.filter_by(status='active').order_by(Project.name).all()
    subs = Subcontractor.query.filter_by(is_active=True).order_by(Subcontractor.name).all()
    if request.method == 'POST':
        p = SubcontractorPayment(
            project_id=request.form.get('project_id'),
            subcontractor_id=request.form.get('subcontractor_id'),
            amount=float(request.form.get('amount', 0)),
            description=request.form.get('description'),
            invoice_ref=request.form.get('invoice_ref'),
            status=request.form.get('status', 'pending'),
            notes=request.form.get('notes')
        )
        if request.form.get('due_date'):
            p.due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date()
        if request.form.get('issue_date'):
            p.issue_date = datetime.strptime(request.form.get('issue_date'), '%Y-%m-%d').date()
        db.session.add(p)
        db.session.commit()
        notify_subcontractor_payment(p)
        flash('Kifizetés rögzítve!', 'success')
        return redirect(url_for('subcontractors.list'))
    return render_template('subcontractors/payment_form.html', projects=projects, subcontractors=subs)


@subcontractors_bp.route('/payments/<int:id>/mark-paid', methods=['POST'])
@login_required
def mark_payment_paid(id):
    p = SubcontractorPayment.query.get_or_404(id)
    p.status = 'paid'
    p.paid_date = date.today()
    db.session.commit()
    notify_subcontractor_payment(p)
    flash('Kifizetés teljesítve!', 'success')
    return redirect(request.referrer or url_for('subcontractors.list'))
