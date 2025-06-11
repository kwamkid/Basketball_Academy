from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from werkzeug.security import check_password_hash
from models import User

# Create blueprint
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and authentication"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        from app import db  # Import here to avoid circular import

        username = request.form.get('username')
        password = request.form.get('password')

        # Find user
        users = db.collection('users').where('username', '==', username).limit(1).stream()

        user_found = None
        user_id = None
        for doc in users:
            user_found = doc.to_dict()
            user_id = doc.id
            break

        if user_found and check_password_hash(user_found['password'], password):
            user = User(user_id, user_found['username'], user_found.get('role', 'admin'))
            login_user(user)

            next_page = request.args.get('next')
            flash('เข้าสู่ระบบสำเร็จ!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        else:
            flash('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง', 'error')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
def logout():
    """Logout user"""
    logout_user()
    flash('ออกจากระบบแล้ว', 'info')
    return redirect(url_for('auth.login'))