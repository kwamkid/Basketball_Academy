from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from models import Parent
from utils.helpers import count_parent_students

# Create blueprint
parents_bp = Blueprint('parents', __name__, url_prefix='/parents')


@parents_bp.route('/')
@login_required
def list():
    """List all parents"""
    from app import db

    parents = []
    parents_ref = db.collection('parents').stream()

    for doc in parents_ref:
        parent = doc.to_dict()
        parent['id'] = doc.id
        parent['students_count'] = count_parent_students(db, doc.id)
        parents.append(parent)

    return render_template('parents/list.html', parents=parents)


@parents_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Add new parent"""
    from app import db

    if request.method == 'POST':
        data = Parent.prepare_data(request.form)
        db.collection('parents').add(data)
        flash('เพิ่มผู้ปกครองสำเร็จ!', 'success')
        return redirect(url_for('parents.list'))

    return render_template('parents/form.html', parent=None)


@parents_bp.route('/<parent_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(parent_id):
    """Edit parent information"""
    from app import db

    parent_doc = db.collection('parents').document(parent_id).get()

    if not parent_doc.exists:
        flash('ไม่พบข้อมูลผู้ปกครอง', 'error')
        return redirect(url_for('parents.list'))

    parent = parent_doc.to_dict()
    parent['id'] = parent_id

    if request.method == 'POST':
        data = {
            'type': request.form.get('type', parent.get('type', 'father')),
            'name': request.form['name'],
            'occupation': request.form.get('occupation', ''),
            'phone': request.form['phone'],
            'address': request.form.get('address', '')
        }

        db.collection('parents').document(parent_id).update(data)
        flash('แก้ไขข้อมูลผู้ปกครองสำเร็จ!', 'success')
        return redirect(url_for('parents.list'))

    # Get students linked to this parent
    students = []
    students_ref = db.collection('students').where('parentId', '==', parent_id).stream()
    for doc in students_ref:
        student = doc.to_dict()
        student['id'] = doc.id
        students.append(student)

    return render_template('parents/form.html', parent=parent, students=students)


@parents_bp.route('/<parent_id>/delete', methods=['POST'])
@login_required
def delete(parent_id):
    """Delete parent"""
    from app import db

    # Check if parent has students
    students = db.collection('students').where('parentId', '==', parent_id).limit(1).stream()

    has_students = False
    for doc in students:
        has_students = True
        break

    if has_students:
        flash('ไม่สามารถลบผู้ปกครองได้ เนื่องจากมีนักเรียนผูกอยู่', 'warning')
        return redirect(url_for('parents.list'))

    # Delete parent
    db.collection('parents').document(parent_id).delete()
    flash('ลบผู้ปกครองสำเร็จ!', 'success')
    return redirect(url_for('parents.list'))