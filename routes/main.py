from flask import Blueprint, render_template
from flask_login import login_required
from datetime import datetime
from config import Config

# Create blueprint
main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def dashboard():
    """หน้าหลัก - Dashboard"""
    from app import db  # Import here to avoid circular import

    # Calculate statistics
    total_students = 0
    active_students = 0
    students_ref = db.collection('students').stream()

    for doc in students_ref:
        total_students += 1
        student = doc.to_dict()
        if student.get('remainingClasses', 0) > 0:
            active_students += 1

    # Count parents
    total_parents = 0
    parents_ref = db.collection('parents').stream()
    for doc in parents_ref:
        total_parents += 1

    # Count today's check-ins
    today = datetime.now(Config.TIMEZONE).strftime('%Y-%m-%d')
    today_checkins = 0
    recent_checkins = []

    attendance_ref = db.collection('attendance').where('checkInDate', '==', today).stream()
    for doc in attendance_ref:
        today_checkins += 1

    # Find students with low remaining classes
    low_classes_students = []
    students_ref = db.collection('students').where('remainingClasses', '<=', 5).stream()
    for doc in students_ref:
        student = doc.to_dict()
        student['id'] = doc.id

        # Get parent info
        if 'parentId' in student and student['parentId']:
            parent_doc = db.collection('parents').document(student['parentId']).get()
            if parent_doc.exists:
                student['parent'] = parent_doc.to_dict()

        low_classes_students.append(student)

    # Sort by remaining classes
    low_classes_students.sort(key=lambda x: x.get('remainingClasses', 0))

    return render_template('dashboard.html',
                           total_students=total_students,
                           active_students=active_students,
                           today_checkins=today_checkins,
                           total_parents=total_parents,
                           recent_checkins=recent_checkins,
                           low_classes_students=low_classes_students[:5])