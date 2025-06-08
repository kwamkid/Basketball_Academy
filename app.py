from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os
import secrets
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))

# Initialize Firebase
# ใน Production, Cloud Run จะใช้ Default Credentials อัตโนมัติ
try:
    if os.path.exists('serviceAccountKey.json'):
        # Local development
        cred = credentials.Certificate('serviceAccountKey.json')
        firebase_admin.initialize_app(cred, {
            'projectId': 'basketball-academy-baf77'
        })
    else:
        # Production on Cloud Run - ระบุ project ID
        firebase_admin.initialize_app(options={
            'projectId': 'basketball-academy-baf77'
        })
    print("Firebase initialized successfully")
except Exception as e:
    print(f"Firebase initialization error: {e}")
    # Try without options
    try:
        firebase_admin.initialize_app()
    except:
        pass

db = firestore.client()

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'กรุณาเข้าสู่ระบบก่อนใช้งาน'


# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username, role='admin'):
        self.id = id
        self.username = username
        self.role = role


@login_manager.user_loader
def load_user(user_id):
    user_doc = db.collection('users').document(user_id).get()
    if user_doc.exists:
        data = user_doc.to_dict()
        return User(user_id, data['username'], data.get('role', 'admin'))
    return None


# Initialize default admin user
def init_default_admin():
    """สร้าง admin user เริ่มต้นถ้ายังไม่มี"""
    admin_ref = db.collection('users').where('username', '==', 'admin').limit(1).stream()

    admin_exists = False
    for doc in admin_ref:
        admin_exists = True
        break

    if not admin_exists:
        # สร้าง admin user
        admin_data = {
            'username': 'admin',
            'password': generate_password_hash('admin123'),
            'role': 'admin',
            'createdAt': firestore.SERVER_TIMESTAMP
        }
        db.collection('users').add(admin_data)
        print("✅ Created default admin user - username: admin, password: admin123")


# Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # ค้นหา user
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
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง', 'error')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('ออกจากระบบแล้ว', 'info')
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    """หน้าหลัก - แสดงรายชื่อนักเรียนทั้งหมด"""
    students = []
    students_ref = db.collection('students').stream()

    for doc in students_ref:
        student = doc.to_dict()
        student['id'] = doc.id

        # Handle old data format (name) vs new format (firstName, lastName)
        if 'name' in student and 'firstName' not in student:
            # Convert old format to new format
            names = student['name'].split(' ', 1)
            student['firstName'] = names[0]
            student['lastName'] = names[1] if len(names) > 1 else ''
            student['nickname'] = student.get('nickname', names[0])

        # ดึงข้อมูลผู้ปกครอง
        if 'parentId' in student and student['parentId']:
            parent_doc = db.collection('parents').document(student['parentId']).get()
            if parent_doc.exists:
                student['parent'] = parent_doc.to_dict()

        students.append(student)

    return render_template('index.html', students=students)


@app.route('/parents')
@login_required
def parents():
    """หน้าจัดการผู้ปกครอง"""
    parents = []
    parents_ref = db.collection('parents').stream()

    for doc in parents_ref:
        parent = doc.to_dict()
        parent['id'] = doc.id

        # นับจำนวนนักเรียนที่ผูกกับผู้ปกครองคนนี้
        students_count = 0
        students_ref = db.collection('students').where('parentId', '==', doc.id).stream()
        for student in students_ref:
            students_count += 1

        parent['students_count'] = students_count
        parents.append(parent)

    return render_template('parents.html', parents=parents)


@app.route('/add_parent', methods=['GET', 'POST'])
@login_required
def add_parent():
    """เพิ่มผู้ปกครอง - หน้าแยก"""
    if request.method == 'POST':
        data = {
            'type': request.form.get('type', 'father'),
            'name': request.form['name'],
            'occupation': request.form.get('occupation', ''),
            'phone': request.form['phone'],
            'address': request.form.get('address', ''),
            'createdAt': firestore.SERVER_TIMESTAMP
        }

        db.collection('parents').add(data)
        flash('เพิ่มผู้ปกครองสำเร็จ!', 'success')
        return redirect(url_for('parents'))

    return render_template('parent_form.html', parent=None)


@app.route('/add_student', methods=['GET', 'POST'])
@login_required
def add_student():
    """เพิ่มนักเรียน"""
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
            'parentId': request.form.get('parentId', ''),
            'remainingClasses': int(request.form['remainingClasses']),
            'createdAt': firestore.SERVER_TIMESTAMP
        }

        db.collection('students').add(data)
        flash('เพิ่มนักเรียนสำเร็จ!', 'success')
        return redirect(url_for('index'))

    # ดึงรายชื่อผู้ปกครองสำหรับ dropdown
    parents = []
    parents_ref = db.collection('parents').stream()
    for doc in parents_ref:
        parent = doc.to_dict()
        parent['id'] = doc.id
        parents.append(parent)

    return render_template('student_form.html', student=None, parents=parents)


@app.route('/student/<student_id>')
@login_required
def student_detail(student_id):
    """หน้ารายละเอียดนักเรียน"""
    student_doc = db.collection('students').document(student_id).get()

    if not student_doc.exists:
        flash('ไม่พบข้อมูลนักเรียน', 'error')
        return redirect(url_for('index'))

    student = student_doc.to_dict()
    student['id'] = student_id

    # ดึงข้อมูลผู้ปกครอง
    if 'parentId' in student:
        parent_doc = db.collection('parents').document(student['parentId']).get()
        if parent_doc.exists:
            student['parent'] = parent_doc.to_dict()

    # ดึงประวัติการเช็คอิน
    attendance = []
    try:
        # ลองใช้ query แบบมี index ก่อน
        attendance_ref = db.collection('attendance').where('studentId', '==', student_id).order_by('checkInTime',
                                                                                                   direction=firestore.Query.DESCENDING).stream()

        for doc in attendance_ref:
            record = doc.to_dict()
            record['id'] = doc.id
            attendance.append(record)
    except:
        # ถ้า index ยังไม่พร้อม ใช้วิธีดึงทั้งหมดแล้วกรองเอง
        attendance_ref = db.collection('attendance').where('studentId', '==', student_id).stream()

        for doc in attendance_ref:
            record = doc.to_dict()
            record['id'] = doc.id
            attendance.append(record)

        # เรียงลำดับด้วย Python
        attendance.sort(key=lambda x: x.get('checkInTime', ''), reverse=True)

    return render_template('student_detail.html', student=student, attendance=attendance)


@app.route('/checkin/<student_id>', methods=['POST'])
@login_required
def checkin(student_id):
    """เช็คอินนักเรียน"""
    # ดึงข้อมูลนักเรียน
    student_ref = db.collection('students').document(student_id)
    student = student_ref.get().to_dict()

    if student['remainingClasses'] <= 0:
        flash('จำนวนครั้งเรียนหมดแล้ว กรุณาเติมครั้งเรียน!', 'warning')
        return redirect(url_for('student_detail', student_id=student_id))

    # หักจำนวนครั้ง
    new_remaining = student['remainingClasses'] - 1
    student_ref.update({'remainingClasses': new_remaining})

    # บันทึกประวัติ
    attendance_data = {
        'studentId': student_id,
        'checkInDate': datetime.now().strftime('%Y-%m-%d'),
        'checkInTime': firestore.SERVER_TIMESTAMP,
        'remainingAfter': new_remaining
    }

    db.collection('attendance').add(attendance_data)

    flash(f'เช็คอินสำเร็จ! คงเหลือ {new_remaining} ครั้ง', 'success')
    return redirect(url_for('student_detail', student_id=student_id))


@app.route('/add_classes/<student_id>', methods=['POST'])
@login_required
def add_classes(student_id):
    """เพิ่มจำนวนครั้งเรียน"""
    amount = int(request.form['amount'])

    student_ref = db.collection('students').document(student_id)
    student = student_ref.get().to_dict()

    new_remaining = student['remainingClasses'] + amount
    student_ref.update({'remainingClasses': new_remaining})

    flash(f'เพิ่มครั้งเรียนสำเร็จ! ปัจจุบันมี {new_remaining} ครั้ง', 'success')
    return redirect(url_for('student_detail', student_id=student_id))


@app.route('/edit_student/<student_id>', methods=['GET', 'POST'])
@login_required
def edit_student(student_id):
    """แก้ไขข้อมูลนักเรียน"""
    student_doc = db.collection('students').document(student_id).get()

    if not student_doc.exists:
        flash('ไม่พบข้อมูลนักเรียน', 'error')
        return redirect(url_for('index'))

    student = student_doc.to_dict()
    student['id'] = student_id

    # Handle old data format
    if 'name' in student and 'firstName' not in student:
        names = student['name'].split(' ', 1)
        student['firstName'] = names[0]
        student['lastName'] = names[1] if len(names) > 1 else ''
        student['nickname'] = student.get('nickname', names[0])

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
        return redirect(url_for('student_detail', student_id=student_id))

    # ดึงรายชื่อผู้ปกครอง
    parents = []
    parents_ref = db.collection('parents').stream()
    for doc in parents_ref:
        parent = doc.to_dict()
        parent['id'] = doc.id
        parents.append(parent)

    return render_template('student_form.html', student=student, parents=parents)


@app.route('/cancel_checkin/<attendance_id>', methods=['POST'])
@login_required
def cancel_checkin(attendance_id):
    """ยกเลิกการเช็คอิน"""
    # ดึงข้อมูลการเช็คอิน
    attendance_doc = db.collection('attendance').document(attendance_id).get()

    if not attendance_doc.exists:
        flash('ไม่พบข้อมูลการเช็คอิน', 'error')
        return redirect(url_for('index'))

    attendance = attendance_doc.to_dict()
    student_id = attendance['studentId']

    # ตรวจสอบว่าเป็นการเช็คอินวันนี้หรือไม่ (optional)
    today = datetime.now().strftime('%Y-%m-%d')
    if attendance['checkInDate'] != today:
        flash('ไม่สามารถยกเลิกการเช็คอินย้อนหลังได้ ยกเลิกได้เฉพาะเช็คอินวันนี้เท่านั้น', 'warning')
        return redirect(url_for('student_detail', student_id=student_id))

    # คืนจำนวนครั้งให้นักเรียน
    student_ref = db.collection('students').document(student_id)
    student = student_ref.get().to_dict()

    new_remaining = student['remainingClasses'] + 1
    student_ref.update({'remainingClasses': new_remaining})

    # ลบประวัติการเช็คอิน
    db.collection('attendance').document(attendance_id).delete()

    flash(f'ยกเลิกการเช็คอินสำเร็จ! คืนครั้งเรียนแล้ว (ปัจจุบันมี {new_remaining} ครั้ง)', 'success')
    return redirect(url_for('student_detail', student_id=student_id))


@app.route('/edit_parent/<parent_id>', methods=['GET', 'POST'])
@login_required
def edit_parent(parent_id):
    """แก้ไขข้อมูลผู้ปกครอง"""
    parent_doc = db.collection('parents').document(parent_id).get()

    if not parent_doc.exists:
        flash('ไม่พบข้อมูลผู้ปกครอง', 'error')
        return redirect(url_for('parents'))

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
        return redirect(url_for('parents'))

    # ดึงรายชื่อนักเรียนที่ผูกกับผู้ปกครองคนนี้
    students = []
    students_ref = db.collection('students').where('parentId', '==', parent_id).stream()
    for doc in students_ref:
        student = doc.to_dict()
        student['id'] = doc.id
        students.append(student)

    return render_template('parent_form.html', parent=parent, students=students)


@app.route('/edit_classes/<student_id>', methods=['POST'])
@login_required
def edit_classes(student_id):
    """แก้ไขจำนวนครั้งเรียน"""
    new_amount = int(request.form['new_amount'])

    student_ref = db.collection('students').document(student_id)
    student_ref.update({'remainingClasses': new_amount})

    flash(f'แก้ไขจำนวนครั้งเรียนเป็น {new_amount} ครั้ง สำเร็จ!', 'success')
    return redirect(url_for('student_detail', student_id=student_id))


@app.route('/delete_parent/<parent_id>', methods=['POST'])
@login_required
def delete_parent(parent_id):
    """ลบผู้ปกครอง"""
    # ตรวจสอบว่ามีนักเรียนผูกอยู่หรือไม่
    students = db.collection('students').where('parentId', '==', parent_id).limit(1).stream()

    has_students = False
    for doc in students:
        has_students = True
        break

    if has_students:
        flash('ไม่สามารถลบผู้ปกครองได้ เนื่องจากมีนักเรียนผูกอยู่', 'warning')
        return redirect(url_for('parents'))

    # ลบผู้ปกครอง
    db.collection('parents').document(parent_id).delete()
    flash('ลบผู้ปกครองสำเร็จ!', 'success')
    return redirect(url_for('parents'))


@app.route('/settings')
@login_required
def settings():
    """หน้าตั้งค่าระบบ"""
    return render_template('settings.html')


@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    """เปลี่ยนรหัสผ่าน"""
    old_password = request.form['old_password']
    new_password = request.form['new_password']

    # ดึงข้อมูล user ปัจจุบัน
    user_doc = db.collection('users').document(current_user.id).get()
    user_data = user_doc.to_dict()

    # ตรวจสอบรหัสผ่านเดิม
    if not check_password_hash(user_data['password'], old_password):
        flash('รหัสผ่านเดิมไม่ถูกต้อง', 'error')
        return redirect(url_for('settings'))

    # อัพเดทรหัสผ่านใหม่
    new_hash = generate_password_hash(new_password)
    db.collection('users').document(current_user.id).update({'password': new_hash})

    flash('เปลี่ยนรหัสผ่านสำเร็จ!', 'success')
    return redirect(url_for('settings'))


if __name__ == '__main__':
    init_default_admin()  # สร้าง admin user ถ้ายังไม่มี
    # Production settings
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=debug, host='0.0.0.0', port=port)