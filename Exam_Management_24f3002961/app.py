import sys
sys.modules['app'] = sys.modules[__name__]

from flask import Flask, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user, logout_user

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///emp.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'emp-secret-key-2026'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'

from models import User

@login_manager.user_loader
def load_user(user_id):
    try:
        user = db.session.get(User, int(user_id))
        if user and user.status in ['deactivated', 'rejected']:
            return None
        return user
    except (ValueError, TypeError):
        return None

@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    if current_user.status in ['deactivated', 'rejected']:
        logout_user()
        flash('Your account is not active. Access denied.', 'danger')
        return redirect(url_for('login'))

    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))

    if current_user.is_examiner:
        if current_user.is_approved_examiner:
            return redirect(url_for('examiner_dashboard'))
        if current_user.status == 'pending':
            return redirect(url_for('examiner_pending'))
        logout_user()
        flash('Your examiner registration has not been approved.', 'warning')
        return redirect(url_for('login'))

    return redirect(url_for('student_dashboard'))

import auth
import admin
import examiner
import student

with app.app_context():
    db.create_all()
    admin_user = User.query.filter_by(role='admin').first()
    if not admin_user:
        from seed import seed_data
        seed_data()

if __name__ == '__main__':
    app.run(debug=True)
