import re
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app import app, db
from models import User

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        login_identifier = request.form.get('login_identifier', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        if not login_identifier or not password:
            flash('Please enter username/email and password.', 'warning')
            return render_template('auth/login.html')

        user = User.query.filter(
            (User.username == login_identifier) |
            (User.email == login_identifier.lower())
        ).first()

        if not user or not user.check_password(password):
            flash('Invalid username/email or password.', 'danger')
            return render_template('auth/login.html')

        if user.status == 'deactivated':
            flash('Your account has been deactivated.', 'danger')
            return render_template('auth/login.html')

        if user.status == 'rejected':
            flash('Your registration was rejected.', 'danger')
            return render_template('auth/login.html')

        login_user(user, remember=remember)
        flash(f'Welcome back, {user.name}!', 'success')
        return redirect(url_for('index'))

    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role = request.form.get('role', 'student')
        phone = request.form.get('phone', '').strip()
        department = request.form.get('department', '').strip()

        if not name or not email or not password or not username:
            flash('Please fill in all required fields.', 'warning')
            return render_template('auth/register.html')

        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            flash('Please enter a valid email address.', 'warning')
            return render_template('auth/register.html')

        if role not in ['student', 'examiner']:
            role = 'student'

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'warning')
            return render_template('auth/register.html')

        if User.query.filter_by(username=username).first():
            flash('Username is already taken.', 'danger')
            return render_template('auth/register.html')

        if User.query.filter_by(email=email).first():
            flash('Email is already registered.', 'danger')
            return render_template('auth/register.html')

        if role == 'examiner':
            status = 'pending'
            message = 'Examiner registration submitted. Please wait for admin approval.'
        else:
            status = 'active'
            message = 'Registration successful. You can now login.'

        new_user = User(
            username=username,
            email=email,
            name=name,
            phone=phone,
            department=department,
            role=role,
            status=status
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash(message, 'success')
        return redirect(url_for('login'))

    return render_template('auth/register.html')

@app.route('/pending-approval')
@login_required
def examiner_pending():
    if current_user.status in ['deactivated', 'rejected']:
        logout_user()
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))

    if not current_user.is_examiner or current_user.status != 'pending':
        return redirect(url_for('index'))

    return render_template('auth/pending.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))
