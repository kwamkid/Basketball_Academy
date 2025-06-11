from werkzeug.security import generate_password_hash
from datetime import datetime
from config import Config


def init_default_admin(db):
    """สร้าง admin user เริ่มต้นถ้ายังไม่มี"""
    admin_ref = db.collection('users').where('username', '==', 'admin').limit(1).stream()

    admin_exists = False
    for doc in admin_ref:
        admin_exists = True
        break

    if not admin_exists:
        admin_data = {
            'username': 'admin',
            'password': generate_password_hash('admin123'),
            'role': 'admin',
            'createdAt': datetime.now(Config.TIMEZONE)
        }
        db.collection('users').add(admin_data)
        print("✅ Created default admin user - username: admin, password: admin123")


def get_student_with_parent(db, student_doc):
    """Get student data with parent information"""
    student = student_doc.to_dict()
    student['id'] = student_doc.id

    # Handle old data format
    if 'name' in student and 'firstName' not in student:
        names = student['name'].split(' ', 1)
        student['firstName'] = names[0]
        student['lastName'] = names[1] if len(names) > 1 else ''
        student['nickname'] = student.get('nickname', names[0])

    # Get parent data
    if 'parentId' in student and student['parentId']:
        parent_doc = db.collection('parents').document(student['parentId']).get()
        if parent_doc.exists:
            student['parent'] = parent_doc.to_dict()

    return student


def count_parent_students(db, parent_id):
    """Count number of students linked to a parent"""
    count = 0
    students_ref = db.collection('students').where('parentId', '==', parent_id).stream()
    for _ in students_ref:
        count += 1
    return count