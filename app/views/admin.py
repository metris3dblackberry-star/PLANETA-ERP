from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models import User

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return view(*args, **kwargs)

    return wrapped


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    q = (request.args.get('q') or '').strip()
    status = request.args.get('status', 'all')
    role = request.args.get('role', 'all')

    query = User.query
    if q:
        like = f"%{q}%"
        query = query.filter(User.name.ilike(like) | User.email.ilike(like))
    if status == 'active':
        query = query.filter_by(is_active=True)
    elif status == 'inactive':
        query = query.filter_by(is_active=False)
    if role != 'all':
        query = query.filter_by(role=role)

    users = query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users, q=q, status=status, role=role)


@admin_bp.route('/users/<int:id>/toggle-active', methods=['POST'])
@login_required
@admin_required
def toggle_active(id):
    user = User.query.get_or_404(id)
    if user.id == current_user.id:
        flash('A saját fiókodat nem deaktiválhatod.', 'danger')
        return redirect(url_for('admin.users'))

    user.is_active = not user.is_active
    db.session.commit()
    flash('Felhasználó állapota frissítve.', 'success')
    return redirect(request.referrer or url_for('admin.users'))


@admin_bp.route('/users/<int:id>/role', methods=['POST'])
@login_required
@admin_required
def change_role(id):
    user = User.query.get_or_404(id)
    new_role = request.form.get('role')
    if new_role not in ('admin', 'user'):
        flash('Érvénytelen jogosultsági szint.', 'danger')
        return redirect(url_for('admin.users'))
    if user.id == current_user.id and new_role != 'admin':
        flash('A saját admin jogosultságodat nem veheted el.', 'danger')
        return redirect(url_for('admin.users'))

    user.role = new_role
    db.session.commit()
    flash('Felhasználói jogosultság frissítve.', 'success')
    return redirect(request.referrer or url_for('admin.users'))
