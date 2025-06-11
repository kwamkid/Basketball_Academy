from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from config import Config
import pandas as pd
import io

# Create blueprint
admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/settings')
@login_required
def settings():
    """Settings page"""
    return render_template('admin/settings.html')


@admin_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    from app import db

    old_password = request.form['old_password']
    new_password = request.form['new_password']

    # Get current user data
    user_doc = db.collection('users').document(current_user.id).get()
    user_data = user_doc.to_dict()

    # Verify old password
    if not check_password_hash(user_data['password'], old_password):
        flash('รหัสผ่านเดิมไม่ถูกต้อง', 'error')
        return redirect(url_for('admin.settings'))

    # Update password
    new_hash = generate_password_hash(new_password)
    db.collection('users').document(current_user.id).update({'password': new_hash})

    flash('เปลี่ยนรหัสผ่านสำเร็จ!', 'success')
    return redirect(url_for('admin.settings'))


@admin_bp.route('/import')
@login_required
def import_data():
    """Import data page"""
    return render_template('admin/import.html')


@admin_bp.route('/process_import', methods=['POST'])
@login_required
def process_import():
    """Process imported file"""
    from app import db

    if 'file' not in request.files:
        flash('กรุณาเลือกไฟล์', 'error')
        return redirect(url_for('admin.import_data'))

    file = request.files['file']
    if file.filename == '':
        flash('กรุณาเลือกไฟล์', 'error')
        return redirect(url_for('admin.import_data'))

    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        flash('รองรับเฉพาะไฟล์ Excel (.xlsx, .xls) หรือ CSV', 'error')
        return redirect(url_for('admin.import_data'))

    try:
        # Read file
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(file.stream.read().decode("utf-8")))
        else:
            df = pd.read_excel(file)

        # Check required columns
        required_columns = ['ชื่อนักเรียน', 'นามสกุลนักเรียน', 'ชื่อเล่น', 'วันเกิด',
                            'เพศ', 'โรงเรียน', 'ระดับชั้น', 'ชื่อผู้ปกครอง', 'เบอร์ผู้ปกครอง']

        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            flash(f'ไฟล์ขาดคอลัมน์: {", ".join(missing_columns)}', 'error')
            return redirect(url_for('admin.import_data'))

        # Process data
        imported_count = 0
        error_rows = []
        parent_cache = {}

        for index, row in df.iterrows():
            try:
                # Process parent data
                parent_name = str(row['ชื่อผู้ปกครอง']).strip()
                parent_phone = str(row['เบอร์ผู้ปกครอง']).strip()
                parent_key = f"{parent_name}_{parent_phone}"

                if parent_key in parent_cache:
                    parent_id = parent_cache[parent_key]
                else:
                    # Check if parent exists
                    parent_query = db.collection('parents').where('name', '==', parent_name).where('phone', '==',
                                                                                                   parent_phone).limit(
                        1).stream()
                    parent_exists = False

                    for doc in parent_query:
                        parent_id = doc.id
                        parent_exists = True
                        break

                    # Create new parent if not exists
                    if not parent_exists:
                        parent_data = {
                            'type': 'father' if str(row.get('ประเภทผู้ปกครอง', 'พ่อ')).strip() == 'พ่อ' else 'mother',
                            'name': parent_name,
                            'occupation': str(row.get('อาชีพผู้ปกครอง', '')).strip() if pd.notna(
                                row.get('อาชีพผู้ปกครอง')) else '',
                            'phone': parent_phone,
                            'address': str(row.get('ที่อยู่ผู้ปกครอง', '')).strip() if pd.notna(
                                row.get('ที่อยู่ผู้ปกครอง')) else '',
                            'createdAt': datetime.now(Config.TIMEZONE)
                        }
                        parent_ref = db.collection('parents').add(parent_data)
                        parent_id = parent_ref[1].id

                    parent_cache[parent_key] = parent_id

                # Process student data
                birth_date = pd.to_datetime(row['วันเกิด'], dayfirst=True).strftime('%Y-%m-%d')

                # Calculate remaining classes
                total_classes = 8
                if pd.notna(row.get('จำนวนครั้งที่เรียนไปแล้ว')):
                    classes_used = int(row['จำนวนครั้งที่เรียนไปแล้ว'])
                    courses_bought = ((classes_used - 1) // 8) + 1
                    total_classes = courses_bought * 8
                    remaining_classes = total_classes - classes_used
                else:
                    remaining_classes = 8

                student_data = {
                    'firstName': str(row['ชื่อนักเรียน']).strip(),
                    'lastName': str(row['นามสกุลนักเรียน']).strip(),
                    'nickname': str(row['ชื่อเล่น']).strip(),
                    'birthDate': birth_date,
                    'gender': str(row['เพศ']).strip(),
                    'nationality': str(row.get('สัญชาติ', 'ไทย')).strip(),
                    'school': str(row['โรงเรียน']).strip(),
                    'grade': str(row['ระดับชั้น']).strip(),
                    'phone': str(row.get('เบอร์นักเรียน', '')).strip() if pd.notna(
                        row.get('เบอร์นักเรียน')) and row.get('เบอร์นักเรียน') != '-' else '',
                    'allergies': str(row.get('ประวัติแพ้ยา', '')).strip() if pd.notna(
                        row.get('ประวัติแพ้ยา')) and row.get('ประวัติแพ้ยา') != '-' else '',
                    'parentId': parent_id,
                    'remainingClasses': remaining_classes,
                    'createdAt': datetime.now(Config.TIMEZONE),
                    'importNote': str(row.get('หมายเหตุ', '')).strip() if pd.notna(row.get('หมายเหตุ')) else ''
                }

                # Add class history info
                if pd.notna(row.get('วันที่เริ่มเรียนครั้งแรก')):
                    first_class_date = pd.to_datetime(row['วันที่เริ่มเรียนครั้งแรก'], dayfirst=True)
                    student_data['firstClassDate'] = first_class_date.strftime('%Y-%m-%d')

                if pd.notna(row.get('จำนวนครั้งที่เรียนไปแล้ว')):
                    student_data['totalClassesAttended'] = int(row['จำนวนครั้งที่เรียนไปแล้ว'])

                # Save student
                student_ref = db.collection('students').add(student_data)

                # Create import log
                log_data = {
                    'studentId': student_ref[1].id,
                    'type': 'import',
                    'performedBy': current_user.username,
                    'timestamp': datetime.now(Config.TIMEZONE),
                    'note': f'Import จากไฟล์ - เริ่มเรียน: {student_data.get("firstClassDate", "-")}, เรียนไปแล้ว: {student_data.get("totalClassesAttended", 0)} ครั้ง'
                }
                db.collection('class_logs').add(log_data)

                imported_count += 1

            except Exception as e:
                error_rows.append({
                    'row': index + 2,
                    'student': f"{row.get('ชื่อนักเรียน', '')} {row.get('นามสกุลนักเรียน', '')}",
                    'error': str(e)
                })

        # Show results
        if imported_count > 0:
            flash(f'✅ Import ข้อมูลสำเร็จ {imported_count} รายการ', 'success')

        if error_rows:
            error_msg = 'มีข้อผิดพลาดในบางแถว:<br>'
            for err in error_rows[:5]:
                error_msg += f'- แถว {err["row"]} ({err["student"]}): {err["error"]}<br>'
            if len(error_rows) > 5:
                error_msg += f'และอีก {len(error_rows) - 5} ข้อ'
            flash(error_msg, 'warning')

        return redirect(url_for('main.dashboard'))

    except Exception as e:
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
        return redirect(url_for('admin.import_data'))


@admin_bp.route('/download_template')
@login_required
def download_template():
    """Download Excel template"""
    # Create sample data
    template_data = {
        'ชื่อนักเรียน': ['สมชาย', 'สมหญิง'],
        'นามสกุลนักเรียน': ['ใจดี', 'ใจดี'],
        'ชื่อเล่น': ['ชาย', 'หญิง'],
        'วันเกิด': ['15/03/2015', '10/08/2017'],
        'เพศ': ['ชาย', 'หญิง'],
        'สัญชาติ': ['ไทย', 'ไทย'],
        'โรงเรียน': ['โรงเรียนสาธิต', 'โรงเรียนสาธิต'],
        'ระดับชั้น': ['ป.3', 'ป.1'],
        'เบอร์นักเรียน': ['0812345678', '-'],
        'ประวัติแพ้ยา': ['-', 'แพ้ถั่ว'],
        'ประเภทผู้ปกครอง': ['พ่อ', 'พ่อ'],
        'ชื่อผู้ปกครอง': ['นายสมศักดิ์ ใจดี', 'นายสมศักดิ์ ใจดี'],
        'อาชีพผู้ปกครอง': ['ธุรกิจส่วนตัว', 'ธุรกิจส่วนตัว'],
        'เบอร์ผู้ปกครอง': ['0891234567', '0891234567'],
        'ที่อยู่ผู้ปกครอง': ['123 หมู่ 1 ต.บางนา', '123 หมู่ 1 ต.บางนา'],
        'วันที่เริ่มเรียนครั้งแรก': ['01/06/2023', '15/09/2023'],
        'จำนวนครั้งที่เรียนไปแล้ว': [45, 20],
        'หมายเหตุ': ['-', 'น้องของสมชาย']
    }

    df = pd.DataFrame(template_data)

    # Create Excel file
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='นักเรียน', index=False)

        # Format
        workbook = writer.book
        worksheet = writer.sheets['นักเรียน']

        # Header format
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#ff6b35',
            'font_color': 'white',
            'border': 1
        })

        # Write header
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)

        # Adjust column width
        worksheet.set_column('A:R', 15)

    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='template_import_students.xlsx'
    )