from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app import db

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip()
        password = request.form.get('password') or ''
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password) and user.is_active:
            login_user(user)
            return redirect(url_for('main.dashboard'))
        flash('Hibás email vagy jelszó!', 'danger')
        return render_template('auth/login.html', panel='login')
    return render_template('auth/login.html', panel=request.args.get('panel', 'login'))


@auth_bp.route('/register', methods=['POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    name     = (request.form.get('reg_name') or '').strip()
    email    = (request.form.get('reg_email') or '').strip()
    password = request.form.get('reg_password') or ''
    confirm  = request.form.get('reg_confirm') or ''

    if not name or not email or not password:
        flash('Minden mező kitöltése kötelező!', 'danger')
        return render_template('auth/login.html', panel='register')
    if len(password) < 6:
        flash('A jelszónak legalább 6 karakter hosszúnak kell lennie!', 'danger')
        return render_template('auth/login.html', panel='register')
    if password != confirm:
        flash('A két jelszó nem egyezik!', 'danger')
        return render_template('auth/login.html', panel='register')
    if User.query.filter_by(email=email).first():
        flash('Ez az email cím már regisztrált!', 'danger')
        return render_template('auth/login.html', panel='register')

    user = User(name=name, email=email, role='user')
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    login_user(user)
    flash(f'Üdvözöljük, {name}! Sikeresen regisztrált.', 'success')
    return redirect(url_for('main.dashboard'))


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@auth_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    """Initial setup - create first admin user"""
    if User.query.count() > 0:
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        user = User(
            email=request.form.get('email'),
            name=request.form.get('name'),
            role='admin'
        )
        user.set_password(request.form.get('password'))
        db.session.add(user)
        db.session.commit()
        flash('Admin felhasználó létrehozva!', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/setup.html')
