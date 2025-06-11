from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
from config import Config
from models import Student, Attendance, ClassLog
from utils.helpers import get_student_with_parent
import math

# Create blueprint
students_bp = Blueprint('students', __name__, url_prefix='/students')


@students_bp.route('/')
@login_required
def list():
    """List all students"""
    from app import db

    students = []
    students_ref = db.collection('students').stream()

    for doc in students_ref:
        student = get_student_with_parent(db, doc)
        students.append(student)

    return render_template('students/list.html', students=students)


@students_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Add new student"""
    from app import db

    if request.method == 'POST':
        data = Student.prepare_data(request.form)
        db.collection('students').add(data)
        flash('เพิ่มนักเรียนสำเร็จ!', 'success')
        return redirect(url_for('students.list'))

    # Get parents for dropdown
    parents = []
    parents_ref = db.collection('parents').stream()
    for doc in parents_ref:
        parent = doc.to_dict()
        parent['id'] = doc.id
        parents.append(parent)

    return render_template('students/form.html', student=None, parents=parents)


@students_bp.route('/<student_id>')
@login_required
def detail(student_id):
    """Student detail page"""
    from app import db

    student_doc = db.collection('students').document(student_id).get()

    if not student_doc.exists:
        flash('ไม่พบข้อมูลนักเรียน', 'error')
        return redirect(url_for('main.dashboard'))

    student = get_student_with_parent(db, student_doc)

    # Get page number from query string
    page = request.args.get('page', 1, type=int)
    per_page = Config.ITEMS_PER_PAGE

    # Get attendance history
    all_attendance = []
    try:
        attendance_ref = db.collection('attendance').where('studentId', '==', student_id).stream()
        for doc in attendance_ref:
            record = doc.to_dict()
            record['id'] = doc.id

            # Convert to Thai timezone
            if 'checkInTime' in record and record['checkInTime']:
                if hasattr(record['checkInTime'], 'tzinfo'):
                    record['checkInTimeThai'] = record['checkInTime'].astimezone(Config.TIMEZONE)

            all_attendance.append(record)
    except:
        pass

    # Sort by latest first
    all_attendance.sort(key=lambda x: x.get('checkInTime', ''), reverse=True)

    # Calculate pagination
    total_attendance = len(all_attendance)
    total_pages = math.ceil(total_attendance / per_page)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    attendance = all_attendance[start_idx:end_idx]

    # Get class management logs
    class_logs = []
    try:
        logs_ref = db.collection('class_logs').where('studentId', '==', student_id).stream()
        for doc in logs_ref:
            log = doc.to_dict()
            log['id'] = doc.id
            class_logs.append(log)
        # Sort by latest first
        class_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    except:
        pass

    return render_template('students/detail.html',
                           student=student,
                           attendance=attendance,
                           class_logs=class_logs,
                           page=page,
                           total_pages=total_pages,
                           total_attendance=total_attendance)


@students_bp.route('/<student_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(student_id):
    """Edit student information"""
    from app import db

    student_doc = db.collection('students').document(student_id).get()

    if not student_doc.exists:
        flash('ไม่พบข้อมูลนักเรียน', 'error')
        return redirect(url_for('main.dashboard'))

    student = get_student_with_parent(db, student_doc)

    if request.method == 'POST':
        data = {
            'firstName': request.form['firstName'],
            'lastName': request.form['lastName'],
            'nickname': request.form['nickname'],
            'birthDate': request.form['birthDate'],
            'gender': request.form['gender'],
            'nationality': request.form.get('nationality', 'ไทย'),
            'school': request.form['school'],
            'grade': request.form['grade'],
            'phone': request.form.get('phone', ''),
            'allergies': request.form.get('allergies', ''),
            'parentId': request.form.get('parentId', '')
        }

        db.collection('students').document(student_id).update(data)
        flash('แก้ไขข้อมูลนักเรียนสำเร็จ!', 'success')
        return redirect(url_for('students.detail', student_id=student_id))

    # Get parents for dropdown
    parents = []
    parents_ref = db.collection('parents').stream()
    for doc in parents_ref:
        parent = doc.to_dict()
        parent['id'] = doc.id
        parents.append(parent)

    return render_template('students/form.html', student=student, parents=parents)


@students_bp.route('/<student_id>/checkin', methods=['POST'])
@login_required
def checkin(student_id):
    """Check-in student"""
    from app import db

    # Get student data
    student_ref = db.collection('students').document(student_id)
    student = student_ref.get().to_dict()

    if student['remainingClasses'] <= 0:
        flash('จำนวนครั้งเรียนหมดแล้ว กรุณาเติมครั้งเรียน!', 'warning')
        return redirect(url_for('students.detail', student_id=student_id))

    # Deduct one class
    new_remaining = student['remainingClasses'] - 1
    student_ref.update({'remainingClasses': new_remaining})

    # Record attendance
    attendance_data = Attendance.prepare_data(student_id, new_remaining)
    db.collection('attendance').add(attendance_data)

    flash(f'เช็คอินสำเร็จ! คงเหลือ {new_remaining} ครั้ง', 'success')
    return redirect(url_for('students.detail', student_id=student_id))


@students_bp.route('/<student_id>/add_classes', methods=['POST'])
@login_required
def add_classes(student_id):
    """Add classes to student"""
    from app import db

    amount = int(request.form['amount'])

    student_ref = db.collection('students').document(student_id)
    student = student_ref.get().to_dict()

    old_remaining = student['remainingClasses']
    new_remaining = old_remaining + amount
    student_ref.update({'remainingClasses': new_remaining})

    # Log the change
    log_data = ClassLog.prepare_add_log(student_id, old_remaining, new_remaining, amount, current_user.username)
    db.collection('class_logs').add(log_data)

    flash(f'เพิ่มครั้งเรียนสำเร็จ! ปัจจุบันมี {new_remaining} ครั้ง', 'success')
    return redirect(url_for('students.detail', student_id=student_id))


@students_bp.route('/<student_id>/edit_classes', methods=['POST'])
@login_required
def edit_classes(student_id):
    """Edit class count directly"""
    from app import db

    new_amount = int(request.form['new_amount'])
    reason = request.form.get('reason', 'ไม่ได้ระบุเหตุผล')

    student_ref = db.collection('students').document(student_id)
    student = student_ref.get().to_dict()

    old_remaining = student['remainingClasses']
    student_ref.update({'remainingClasses': new_amount})

    # Log the change
    log_data = ClassLog.prepare_edit_log(student_id, old_remaining, new_amount, reason, current_user.username)
    db.collection('class_logs').add(log_data)

    flash(f'แก้ไขจำนวนครั้งเรียนเป็น {new_amount} ครั้ง สำเร็จ!', 'success')
    return redirect(url_for('students.detail', student_id=student_id))


@students_bp.route('/attendance/<attendance_id>/cancel', methods=['POST'])
@login_required
def cancel_checkin(attendance_id):
    """Cancel a check-in"""
    from app import db

    # Get attendance record
    attendance_doc = db.collection('attendance').document(attendance_id).get()

    if not attendance_doc.exists:
        flash('ไม่พบข้อมูลการเช็คอิน', 'error')
        return redirect(url_for('main.dashboard'))

    attendance = attendance_doc.to_dict()
    student_id = attendance['studentId']

    # Check if it's today's check-in
    today = datetime.now(Config.TIMEZONE).strftime('%Y-%m-%d')
    if attendance['checkInDate'] != today:
        flash('ไม่สามารถยกเลิกการเช็คอินย้อนหลังได้ ยกเลิกได้เฉพาะเช็คอินวันนี้เท่านั้น', 'warning')
        return redirect(url_for('students.detail', student_id=student_id))

    # Return the class to student
    student_ref = db.collection('students').document(student_id)
    student = student_ref.get().to_dict()

    new_remaining = student['remainingClasses'] + 1
    student_ref.update({'remainingClasses': new_remaining})

    # Delete attendance record
    db.collection('attendance').document(attendance_id).delete()

    flash(f'ยกเลิกการเช็คอินสำเร็จ! คืนครั้งเรียนแล้ว (ปัจจุบันมี {new_remaining} ครั้ง)', 'success')
    return redirect(url_for('students.detail', student_id=student_id))