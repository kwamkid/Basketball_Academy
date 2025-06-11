# clear_data.py
# ⚠️ WARNING: Script นี้จะลบข้อมูลทั้งหมดในระบบ ใช้ด้วยความระมัดระวัง!

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import os
import sys

# Initialize Firebase
if not firebase_admin._apps:
    if os.path.exists('serviceAccountKey.json'):
        cred = credentials.Certificate('serviceAccountKey.json')
        firebase_admin.initialize_app(cred)
    else:
        firebase_admin.initialize_app()

db = firestore.client()


def clear_all_data():
    """ลบข้อมูลทั้งหมดในระบบ (ยกเว้น users)"""
    print("\n⚠️  คำเตือน: คำสั่งนี้จะลบข้อมูลทั้งหมด!")
    print("Collections ที่จะถูกลบ:")
    print("- students (นักเรียน)")
    print("- parents (ผู้ปกครอง)")
    print("- attendance (ประวัติการเช็คอิน)")
    print("- class_logs (ประวัติการจัดการครั้งเรียน)")
    print("\n❗ Collection 'users' จะไม่ถูกลบ (เก็บข้อมูล admin)")

    confirm = input("\nพิมพ์ 'DELETE ALL' เพื่อยืนยันการลบทั้งหมด: ")

    if confirm != "DELETE ALL":
        print("❌ ยกเลิกการลบข้อมูล")
        return

    # รายการ collections ที่จะลบ
    collections_to_delete = ['students', 'parents', 'attendance', 'class_logs']

    for collection_name in collections_to_delete:
        print(f"\n🗑️  กำลังลบ collection: {collection_name}")
        delete_collection(collection_name)

    print("\n✅ ลบข้อมูลทั้งหมดเสร็จสิ้น!")


def delete_collection(collection_name):
    """ลบทุก document ใน collection"""
    docs = db.collection(collection_name).stream()
    deleted = 0

    for doc in docs:
        doc.reference.delete()
        deleted += 1
        if deleted % 10 == 0:
            print(f"   ลบแล้ว {deleted} รายการ...")

    print(f"   ✓ ลบทั้งหมด {deleted} รายการ")


def clear_specific_student():
    """ลบข้อมูลเฉพาะนักเรียนคนใดคนหนึ่ง"""
    print("\n=== ลบข้อมูลนักเรียนเฉพาะคน ===")
    student_id = input("กรุณาใส่ Student ID: ").strip()

    if not student_id:
        print("❌ ต้องระบุ Student ID")
        return

    # ตรวจสอบว่ามีนักเรียนคนนี้หรือไม่
    student_doc = db.collection('students').document(student_id).get()

    if not student_doc.exists:
        print(f"❌ ไม่พบนักเรียน ID: {student_id}")
        return

    student = student_doc.to_dict()
    student_name = f"{student.get('firstName', '')} {student.get('lastName', '')}"

    print(f"\n📋 ข้อมูลนักเรียนที่จะลบ:")
    print(f"   ชื่อ: {student_name}")
    print(f"   ชื่อเล่น: {student.get('nickname', '')}")
    print(f"   โรงเรียน: {student.get('school', '')}")

    confirm = input(f"\nยืนยันการลบนักเรียน {student_name}? (y/n): ")

    if confirm.lower() != 'y':
        print("❌ ยกเลิกการลบ")
        return

    print("\n🗑️  กำลังลบข้อมูล...")

    # 1. ลบประวัติการเช็คอิน
    attendance_docs = db.collection('attendance').where('studentId', '==', student_id).stream()
    attendance_count = 0
    for doc in attendance_docs:
        doc.reference.delete()
        attendance_count += 1
    print(f"   ✓ ลบประวัติการเช็คอิน {attendance_count} รายการ")

    # 2. ลบประวัติการจัดการครั้งเรียน
    logs_docs = db.collection('class_logs').where('studentId', '==', student_id).stream()
    logs_count = 0
    for doc in logs_docs:
        doc.reference.delete()
        logs_count += 1
    print(f"   ✓ ลบประวัติการจัดการครั้งเรียน {logs_count} รายการ")

    # 3. ลบข้อมูลนักเรียน
    db.collection('students').document(student_id).delete()
    print(f"   ✓ ลบข้อมูลนักเรียน")

    print(f"\n✅ ลบข้อมูลนักเรียน {student_name} เสร็จสิ้น!")


def reset_attendance_only():
    """ลบเฉพาะประวัติการเช็คอิน แต่คงข้อมูลนักเรียนไว้"""
    print("\n=== ลบเฉพาะประวัติการเช็คอิน ===")
    print("⚠️  คำเตือน: จะลบประวัติการเช็คอินทั้งหมด แต่คงข้อมูลนักเรียนไว้")

    confirm = input("\nพิมพ์ 'CLEAR ATTENDANCE' เพื่อยืนยัน: ")

    if confirm != "CLEAR ATTENDANCE":
        print("❌ ยกเลิกการลบ")
        return

    # ลบประวัติการเช็คอิน
    print("\n🗑️  กำลังลบประวัติการเช็คอิน...")
    delete_collection('attendance')

    # ลบประวัติการจัดการครั้งเรียน
    print("🗑️  กำลังลบประวัติการจัดการครั้งเรียน...")
    delete_collection('class_logs')

    # รีเซ็ตจำนวนครั้งเรียนของนักเรียนทุกคน
    print("\n🔄 กำลังรีเซ็ตจำนวนครั้งเรียน...")
    students = db.collection('students').stream()
    reset_count = 0

    for doc in students:
        # รีเซ็ตเป็น 8 ครั้ง (1 คอร์ส)
        doc.reference.update({
            'remainingClasses': 8
        })
        reset_count += 1

    print(f"   ✓ รีเซ็ตนักเรียน {reset_count} คน (คนละ 8 ครั้ง)")
    print("\n✅ ลบประวัติการเช็คอินและรีเซ็ตครั้งเรียนเสร็จสิ้น!")


def show_statistics():
    """แสดงสถิติข้อมูลในระบบ"""
    print("\n=== สถิติข้อมูลในระบบ ===")

    # นับจำนวน documents ในแต่ละ collection
    collections = {
        'students': 'นักเรียน',
        'parents': 'ผู้ปกครอง',
        'attendance': 'ประวัติการเช็คอิน',
        'class_logs': 'ประวัติการจัดการครั้งเรียน',
        'users': 'ผู้ใช้ระบบ'
    }

    for collection_name, thai_name in collections.items():
        count = 0
        for _ in db.collection(collection_name).stream():
            count += 1
        print(f"📊 {thai_name}: {count} รายการ")


def main():
    print("=" * 50)
    print("🗃️  ระบบจัดการข้อมูล Basketball Academy")
    print("=" * 50)

    # แสดงสถิติก่อน
    show_statistics()

    print("\n📋 เมนู:")
    print("1. ลบข้อมูลทั้งหมด (ยกเว้น users)")
    print("2. ลบข้อมูลนักเรียนเฉพาะคน")
    print("3. ลบเฉพาะประวัติการเช็คอิน (คงข้อมูลนักเรียนไว้)")
    print("4. แสดงสถิติอีกครั้ง")
    print("5. ออกจากโปรแกรม")

    choice = input("\nเลือกตัวเลือก (1-5): ").strip()

    if choice == "1":
        clear_all_data()
    elif choice == "2":
        clear_specific_student()
    elif choice == "3":
        reset_attendance_only()
    elif choice == "4":
        show_statistics()
        input("\nกด Enter เพื่อกลับไปเมนูหลัก...")
        main()
    elif choice == "5":
        print("\n👋 ออกจากโปรแกรม")
        sys.exit(0)
    else:
        print("\n❌ ตัวเลือกไม่ถูกต้อง")
        input("กด Enter เพื่อลองใหม่...")
        main()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  ยกเลิกการทำงาน")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ เกิดข้อผิดพลาด: {e}")
        sys.exit(1)