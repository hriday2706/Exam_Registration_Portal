from datetime import date, timedelta
from app import db
from models import User, Course, Examination, Rubric, Slot, Booking, Evaluation, RubricScore

def seed_data():
    admin = User(
        username='admin',
        email='admin@emp.com',
        name='System Administrator',
        phone='9876500000',
        role='admin',
        status='active'
    )
    admin.set_password('admin123')
    db.session.add(admin)

    examiner1 = User(
        username='prof_sharma',
        email='sharma@college.edu',
        name='Prof. Rajesh Sharma',
        phone='9876543210',
        department='Computer Science',
        role='examiner',
        status='active'
    )
    examiner1.set_password('examiner123')

    examiner2 = User(
        username='dr_mehta',
        email='mehta@college.edu',
        name='Dr. Anita Mehta',
        phone='9876543211',
        department='Information Technology',
        role='examiner',
        status='pending'
    )
    examiner2.set_password('examiner123')

    student1 = User(
        username='rahul_verma',
        email='rahul@student.edu',
        name='Rahul Verma',
        phone='9123456780',
        role='student',
        status='active'
    )
    student1.set_password('student123')

    student2 = User(
        username='sneha_patel',
        email='sneha@student.edu',
        name='Sneha Patel',
        phone='9123456781',
        role='student',
        status='active'
    )
    student2.set_password('student123')

    db.session.add_all([examiner1, examiner2, student1, student2])
    db.session.flush()

    course1 = Course(
        course_code='CS101',
        course_name='Programming Fundamentals',
        description='Introduction to C and Python programming concepts, control structures, and algorithms.',
        status='Active'
    )
    course2 = Course(
        course_code='CS201',
        course_name='Data Structures and Algorithms',
        description='Study of linear and non-linear data structures, searching, sorting, and complexity analysis.',
        status='Active'
    )
    course3 = Course(
        course_code='CS301',
        course_name='Database Management Systems',
        description='Relational model, SQL querying, normalisation, and database administration.',
        status='Active'
    )

    db.session.add_all([course1, course2, course3])
    db.session.flush()

    today = date.today()

    exam1 = Examination(
        course_id=course1.id,
        name='CS101 Practical Examination',
        exam_type='Practical',
        duration=45,
        max_marks=50,
        slot_creation_start_date=today - timedelta(days=5),
        slot_creation_end_date=today + timedelta(days=5),
        slot_booking_start_date=today - timedelta(days=2),
        slot_booking_end_date=today + timedelta(days=5),
        status='Booking Open'
    )

    exam2 = Examination(
        course_id=course2.id,
        name='CS201 Viva Examination',
        exam_type='Viva',
        duration=30,
        max_marks=100,
        slot_creation_start_date=today,
        slot_creation_end_date=today + timedelta(days=7),
        slot_booking_start_date=today + timedelta(days=3),
        slot_booking_end_date=today + timedelta(days=10),
        status='Slot Creation'
    )

    exam3 = Examination(
        course_id=course3.id,
        name='CS301 Project Demo',
        exam_type='Project Demo',
        duration=60,
        max_marks=100,
        slot_creation_start_date=today + timedelta(days=5),
        slot_creation_end_date=today + timedelta(days=12),
        slot_booking_start_date=today + timedelta(days=10),
        slot_booking_end_date=today + timedelta(days=20),
        status='Draft'
    )

    db.session.add_all([exam1, exam2, exam3])
    db.session.flush()

    rubric1 = Rubric(
        examination_id=exam1.id,
        criterion_name='Code Implementation & Syntax',
        max_marks=20,
        weightage=1.0,
        description='Correct syntax and logic implementation'
    )
    rubric2 = Rubric(
        examination_id=exam1.id,
        criterion_name='Testing & Edge Cases',
        max_marks=15,
        weightage=1.0,
        description='Handling corner cases and test coverage'
    )
    rubric3 = Rubric(
        examination_id=exam1.id,
        criterion_name='Code Style & Modularity',
        max_marks=15,
        weightage=1.0,
        description='Proper variable naming and function modularity'
    )

    rubric4 = Rubric(
        examination_id=exam2.id,
        criterion_name='Theoretical Understanding',
        max_marks=40,
        weightage=1.0,
        description='Core understanding of trees, graphs, and dynamic programming'
    )
    rubric5 = Rubric(
        examination_id=exam2.id,
        criterion_name='Problem Solving & Complexity',
        max_marks=40,
        weightage=1.0,
        description='Optimal time and space complexity analysis'
    )
    rubric6 = Rubric(
        examination_id=exam2.id,
        criterion_name='Communication & Presentation',
        max_marks=20,
        weightage=1.0,
        description='Clarity of technical explanations'
    )

    db.session.add_all([rubric1, rubric2, rubric3, rubric4, rubric5, rubric6])
    db.session.flush()

    slot1 = Slot(
        examination_id=exam1.id,
        examiner_id=examiner1.id,
        date=today + timedelta(days=1),
        start_time='10:00',
        end_time='11:00',
        max_capacity=3,
        available_seats=2,
        status='Available'
    )

    slot2 = Slot(
        examination_id=exam1.id,
        examiner_id=examiner1.id,
        date=today + timedelta(days=1),
        start_time='11:30',
        end_time='12:30',
        max_capacity=2,
        available_seats=2,
        status='Available'
    )

    slot3 = Slot(
        examination_id=exam1.id,
        examiner_id=examiner1.id,
        date=today - timedelta(days=1),
        start_time='14:00',
        end_time='15:00',
        max_capacity=1,
        available_seats=0,
        status='Full'
    )

    db.session.add_all([slot1, slot2, slot3])
    db.session.flush()

    booking1 = Booking(
        student_id=student1.id,
        slot_id=slot1.id,
        status='Booked'
    )

    booking2 = Booking(
        student_id=student2.id,
        slot_id=slot3.id,
        status='Completed'
    )

    db.session.add_all([booking1, booking2])
    db.session.flush()

    evaluation = Evaluation(
        booking_id=booking2.id,
        examiner_id=examiner1.id,
        total_marks=44.0,
        remarks='Excellent code implementation and handled all edge cases well.',
        status='Completed'
    )
    db.session.add(evaluation)
    db.session.flush()

    rs1 = RubricScore(
        evaluation_id=evaluation.id,
        rubric_id=rubric1.id,
        marks_obtained=18.0,
        remarks='Very clean logic'
    )
    rs2 = RubricScore(
        evaluation_id=evaluation.id,
        rubric_id=rubric2.id,
        marks_obtained=13.0,
        remarks='Good test coverage'
    )
    rs3 = RubricScore(
        evaluation_id=evaluation.id,
        rubric_id=rubric3.id,
        marks_obtained=13.0,
        remarks='Neat variable naming'
    )

    db.session.add_all([rs1, rs2, rs3])
    db.session.commit()
