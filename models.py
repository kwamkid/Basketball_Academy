from flask_login import UserMixin
from datetime import datetime
from config import Config


class User(UserMixin):
    """User model for Flask-Login"""

    def __init__(self, id, username, role='admin'):
        self.id = id
        self.username = username
        self.role = role


class Student:
    """Student data model"""

    @staticmethod
    def prepare_data(form_data):
        """Prepare student data from form"""
        return {
            'firstName': form_data['firstName'],
            'lastName': form_data['lastName'],
            'nickname': form_data['nickname'],
            'birthDate': form_data['birthDate'],
            'gender': form_data['gender'],
            'nationality': form_data.get('nationality', 'ไทย'),
            'school': form_data['school'],
            'grade': form_data['grade'],
            'phone': form_data.get('phone', ''),
            'allergies': form_data.get('allergies', ''),
            'parentId': form_data.get('parentId', ''),
            'remainingClasses': int(form_data.get('remainingClasses', Config.CLASSES_PER_COURSE)),
            'createdAt': datetime.now(Config.TIMEZONE)
        }


class Parent:
    """Parent data model"""

    @staticmethod
    def prepare_data(form_data):
        """Prepare parent data from form"""
        return {
            'type': form_data.get('type', 'father'),
            'name': form_data['name'],
            'occupation': form_data.get('occupation', ''),
            'phone': form_data['phone'],
            'address': form_data.get('address', ''),
            'createdAt': datetime.now(Config.TIMEZONE)
        }


class Attendance:
    """Attendance data model"""

    @staticmethod
    def prepare_data(student_id, remaining_classes):
        """Prepare attendance data"""
        th_time = datetime.now(Config.TIMEZONE)
        return {
            'studentId': student_id,
            'checkInDate': th_time.strftime('%Y-%m-%d'),
            'checkInTime': th_time,
            'checkInTimeStr': th_time.strftime('%H:%M น.'),
            'remainingAfter': remaining_classes
        }


class ClassLog:
    """Class management log model"""

    @staticmethod
    def prepare_add_log(student_id, old_value, new_value, amount, username):
        """Prepare log for adding classes"""
        th_time = datetime.now(Config.TIMEZONE)
        return {
            'studentId': student_id,
            'type': 'add_classes',
            'oldValue': old_value,
            'newValue': new_value,
            'changeAmount': amount,
            'performedBy': username,
            'timestamp': th_time,
            'timestampStr': th_time.strftime('%d/%m/%Y %H:%M น.'),
            'note': f'เพิ่มครั้งเรียน {amount} ครั้ง'
        }

    @staticmethod
    def prepare_edit_log(student_id, old_value, new_value, reason, username):
        """Prepare log for editing classes"""
        th_time = datetime.now(Config.TIMEZONE)
        return {
            'studentId': student_id,
            'type': 'edit_classes',
            'oldValue': old_value,
            'newValue': new_value,
            'changeAmount': new_value - old_value,
            'performedBy': username,
            'timestamp': th_time,
            'timestampStr': th_time.strftime('%d/%m/%Y %H:%M น.'),
            'reason': reason,
            'note': f'แก้ไขจำนวนครั้งเรียนจาก {old_value} เป็น {new_value} ครั้ง'
        }