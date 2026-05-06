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
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password) and user.is_active:
            login_user(user)
            return redirect(url_for('main.dashboard'))
        flash('Hibás email vagy jelszó!', 'danger')
    return render_template('auth/login.html')


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
