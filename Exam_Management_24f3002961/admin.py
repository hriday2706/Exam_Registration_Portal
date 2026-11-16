from functools import wraps
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash
from flask_login import current_user, logout_user
from app import app, db
from models import User, Course, Examination, Rubric, Slot, Booking

def admin_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if not current_user.is_admin:
            flash('Admin access required.', 'danger')
            return redirect(url_for('index'))
        if current_user.status != 'active':
            logout_user()
            flash('Access denied. Account is inactive.', 'danger')
            return redirect(url_for('login'))
        return function(*args, **kwargs)
    return wrapper

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    total_courses = Course.query.count()
    total_examinations = Examination.query.count()
    total_examiners = User.query.filter_by(role='examiner').count()
    total_students = User.query.filter_by(role='student').count()
    total_slots = Slot.query.count()
    total_bookings = Booking.query.count()
    recent_bookings = Booking.query.order_by(Booking.booking_date.desc()).limit(5).all()

    return render_template(
        'admin/dashboard.html',
        total_courses=total_courses,
        total_examinations=total_examinations,
        total_examiners=total_examiners,
        total_students=total_students,
        total_slots=total_slots,
        total_bookings=total_bookings,
        recent_bookings=recent_bookings
    )

@app.route('/admin/courses')
@admin_required
def admin_courses():
    courses = Course.query.order_by(Course.course_code.asc()).all()
    return render_template('admin/courses.html', courses=courses)

@app.route('/admin/courses/new', methods=['GET', 'POST'])
@admin_required
def new_course():
    if request.method == 'POST':
        course_code = request.form.get('course_code', '').strip().upper()
        course_name = request.form.get('course_name', '').strip()
        description = request.form.get('description', '').strip()
        status = request.form.get('status', 'Active')

        if not course_code or not course_name:
            flash('Course Code and Course Name are required.', 'warning')
            return render_template('admin/course_form.html', action='Create', course=None)

        if Course.query.filter_by(course_code=course_code).first():
            flash('Course Code already exists.', 'danger')
            return render_template('admin/course_form.html', action='Create', course=None)

        course = Course(
            course_code=course_code,
            course_name=course_name,
            description=description,
            status=status
        )
        db.session.add(course)
        db.session.commit()

        flash('Course created successfully.', 'success')
        return redirect(url_for('admin_courses'))

    return render_template('admin/course_form.html', action='Create', course=None)

@app.route('/admin/courses/edit/<int:course_id>', methods=['GET', 'POST'])
@admin_required
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)

    if request.method == 'POST':
        course_code = request.form.get('course_code', '').strip().upper()
        course_name = request.form.get('course_name', '').strip()
        description = request.form.get('description', '').strip()
        status = request.form.get('status', 'Active')

        if not course_code or not course_name:
            flash('Course Code and Course Name are required.', 'warning')
            return render_template('admin/course_form.html', action='Edit', course=course)

        existing = Course.query.filter_by(course_code=course_code).first()
        if existing and existing.id != course.id:
            flash('Course Code already exists on another course.', 'danger')
            return render_template('admin/course_form.html', action='Edit', course=course)

        course.course_code = course_code
        course.course_name = course_name
        course.description = description
        course.status = status
        db.session.commit()

        flash('Course updated successfully.', 'success')
        return redirect(url_for('admin_courses'))

    return render_template('admin/course_form.html', action='Edit', course=course)

@app.route('/admin/courses/delete/<int:course_id>', methods=['POST'])
@admin_required
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    db.session.delete(course)
    db.session.commit()
    flash('Course deleted successfully.', 'info')
    return redirect(url_for('admin_courses'))

@app.route('/admin/examinations')
@admin_required
def admin_examinations():
    examinations = Examination.query.order_by(Examination.created_at.desc()).all()
    return render_template('admin/examinations.html', examinations=examinations)

@app.route('/admin/examinations/new', methods=['GET', 'POST'])
@admin_required
def new_examination():
    courses = Course.query.filter_by(status='Active').all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        course_id = request.form.get('course_id')
        exam_type = request.form.get('exam_type', 'Viva')
        duration = request.form.get('duration', 30)
        max_marks = request.form.get('max_marks', 100)
        slot_creation_start = request.form.get('slot_creation_start_date')
        slot_creation_end = request.form.get('slot_creation_end_date')
        slot_booking_start = request.form.get('slot_booking_start_date')
        slot_booking_end = request.form.get('slot_booking_end_date')
        status = request.form.get('status', 'Draft')

        if not name or not course_id or not slot_creation_start or not slot_creation_end or not slot_booking_start or not slot_booking_end:
            flash('All examination fields and dates are required.', 'warning')
            return render_template('admin/exam_form.html', action='Create', exam=None, courses=courses)

        try:
            exam = Examination(
                name=name,
                course_id=int(course_id),
                exam_type=exam_type,
                duration=int(duration),
                max_marks=int(max_marks),
                slot_creation_start_date=datetime.strptime(slot_creation_start, '%Y-%m-%d').date(),
                slot_creation_end_date=datetime.strptime(slot_creation_end, '%Y-%m-%d').date(),
                slot_booking_start_date=datetime.strptime(slot_booking_start, '%Y-%m-%d').date(),
                slot_booking_end_date=datetime.strptime(slot_booking_end, '%Y-%m-%d').date(),
                status=status
            )
            db.session.add(exam)
            db.session.commit()
            flash('Examination created successfully.', 'success')
            return redirect(url_for('admin_examinations'))
        except Exception as e:
            flash('Error creating examination: ' + str(e), 'danger')
            return render_template('admin/exam_form.html', action='Create', exam=None, courses=courses)

    return render_template('admin/exam_form.html', action='Create', exam=None, courses=courses)

@app.route('/admin/examinations/edit/<int:exam_id>', methods=['GET', 'POST'])
@admin_required
def edit_examination(exam_id):
    exam = Examination.query.get_or_404(exam_id)
    courses = Course.query.filter_by(status='Active').all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        course_id = request.form.get('course_id')
        exam_type = request.form.get('exam_type', 'Viva')
        duration = request.form.get('duration', 30)
        max_marks = request.form.get('max_marks', 100)
        slot_creation_start = request.form.get('slot_creation_start_date')
        slot_creation_end = request.form.get('slot_creation_end_date')
        slot_booking_start = request.form.get('slot_booking_start_date')
        slot_booking_end = request.form.get('slot_booking_end_date')
        status = request.form.get('status', 'Draft')

        if not name or not course_id or not slot_creation_start or not slot_creation_end or not slot_booking_start or not slot_booking_end:
            flash('All examination fields and dates are required.', 'warning')
            return render_template('admin/exam_form.html', action='Edit', exam=exam, courses=courses)

        try:
            exam.name = name
            exam.course_id = int(course_id)
            exam.exam_type = exam_type
            exam.duration = int(duration)
            exam.max_marks = int(max_marks)
            exam.slot_creation_start_date = datetime.strptime(slot_creation_start, '%Y-%m-%d').date()
            exam.slot_creation_end_date = datetime.strptime(slot_creation_end, '%Y-%m-%d').date()
            exam.slot_booking_start_date = datetime.strptime(slot_booking_start, '%Y-%m-%d').date()
            exam.slot_booking_end_date = datetime.strptime(slot_booking_end, '%Y-%m-%d').date()
            exam.status = status
            db.session.commit()
            flash('Examination updated successfully.', 'success')
            return redirect(url_for('admin_examinations'))
        except Exception as e:
            flash('Error updating examination: ' + str(e), 'danger')
            return render_template('admin/exam_form.html', action='Edit', exam=exam, courses=courses)

    return render_template('admin/exam_form.html', action='Edit', exam=exam, courses=courses)

@app.route('/admin/examinations/delete/<int:exam_id>', methods=['POST'])
@admin_required
def delete_examination(exam_id):
    exam = Examination.query.get_or_404(exam_id)
    db.session.delete(exam)
    db.session.commit()
    flash('Examination deleted successfully.', 'info')
    return redirect(url_for('admin_examinations'))

@app.route('/admin/examinations/<int:exam_id>/status', methods=['POST'])
@admin_required
def update_examination_status(exam_id):
    exam = Examination.query.get_or_404(exam_id)
    new_status = request.form.get('status')
    if new_status in ['Draft', 'Slot Creation', 'Booking Open', 'Closed', 'Completed']:
        exam.status = new_status
        db.session.commit()
        flash(f'Examination status changed to {new_status}.', 'success')
    return redirect(url_for('admin_examinations'))

@app.route('/admin/examinations/<int:exam_id>/rubrics')
@admin_required
def admin_rubrics(exam_id):
    exam = Examination.query.get_or_404(exam_id)
    rubrics = Rubric.query.filter_by(examination_id=exam_id).all()
    return render_template('admin/rubrics.html', exam=exam, rubrics=rubrics)

@app.route('/admin/examinations/<int:exam_id>/rubrics/new', methods=['GET', 'POST'])
@admin_required
def new_rubric(exam_id):
    exam = Examination.query.get_or_404(exam_id)

    if request.method == 'POST':
        criterion_name = request.form.get('criterion_name', '').strip()
        max_marks = request.form.get('max_marks', 10)
        weightage = request.form.get('weightage', 1.0)
        description = request.form.get('description', '').strip()

        if not criterion_name:
            flash('Criterion name is required.', 'warning')
            return render_template('admin/rubric_form.html', action='Create', exam=exam, rubric=None)

        rubric = Rubric(
            examination_id=exam.id,
            criterion_name=criterion_name,
            max_marks=int(max_marks),
            weightage=float(weightage),
            description=description
        )
        db.session.add(rubric)
        db.session.commit()
        flash('Rubric criterion added successfully.', 'success')
        return redirect(url_for('admin_rubrics', exam_id=exam.id))

    return render_template('admin/rubric_form.html', action='Create', exam=exam, rubric=None)

@app.route('/admin/rubrics/edit/<int:rubric_id>', methods=['GET', 'POST'])
@admin_required
def edit_rubric(rubric_id):
    rubric = Rubric.query.get_or_404(rubric_id)
    exam = rubric.examination

    if request.method == 'POST':
        criterion_name = request.form.get('criterion_name', '').strip()
        max_marks = request.form.get('max_marks', 10)
        weightage = request.form.get('weightage', 1.0)
        description = request.form.get('description', '').strip()

        if not criterion_name:
            flash('Criterion name is required.', 'warning')
            return render_template('admin/rubric_form.html', action='Edit', exam=exam, rubric=rubric)

        rubric.criterion_name = criterion_name
        rubric.max_marks = int(max_marks)
        rubric.weightage = float(weightage)
        rubric.description = description
        db.session.commit()
        flash('Rubric criterion updated successfully.', 'success')
        return redirect(url_for('admin_rubrics', exam_id=exam.id))

    return render_template('admin/rubric_form.html', action='Edit', exam=exam, rubric=rubric)

@app.route('/admin/rubrics/delete/<int:rubric_id>', methods=['POST'])
@admin_required
def delete_rubric(rubric_id):
    rubric = Rubric.query.get_or_404(rubric_id)
    exam_id = rubric.examination_id
    db.session.delete(rubric)
    db.session.commit()
    flash('Rubric criterion deleted successfully.', 'info')
    return redirect(url_for('admin_rubrics', exam_id=exam_id))

@app.route('/admin/examiners')
@admin_required
def admin_examiners():
    examiners = User.query.filter_by(role='examiner').order_by(User.name.asc()).all()
    return render_template('admin/examiners.html', examiners=examiners)

@app.route('/admin/examiners/<int:user_id>/status/<string:action>', methods=['POST'])
@admin_required
def update_examiner_status(user_id, action):
    examiner = User.query.filter_by(id=user_id, role='examiner').first_or_404()
    if action == 'approve' or action == 'activate':
        examiner.status = 'active'
        flash(f'Examiner {examiner.name} approved/activated successfully.', 'success')
    elif action == 'reject':
        examiner.status = 'rejected'
        flash(f'Examiner {examiner.name} registration rejected.', 'warning')
    elif action == 'deactivate':
        examiner.status = 'deactivated'
        flash(f'Examiner {examiner.name} account deactivated.', 'secondary')
    db.session.commit()
    return redirect(url_for('admin_examiners'))

@app.route('/admin/students')
@admin_required
def admin_students():
    students = User.query.filter_by(role='student').order_by(User.name.asc()).all()
    return render_template('admin/students.html', students=students)

@app.route('/admin/slots')
@admin_required
def admin_slots():
    slots = Slot.query.order_by(Slot.date.desc(), Slot.start_time.asc()).all()
    return render_template('admin/slots.html', slots=slots)

@app.route('/admin/slots/<int:slot_id>/change-examiner', methods=['GET', 'POST'])
@admin_required
def change_slot_examiner(slot_id):
    slot = Slot.query.get_or_404(slot_id)
    examiners = User.query.filter_by(role='examiner', status='active').all()

    if request.method == 'POST':
        new_examiner_id = request.form.get('examiner_id')
        if not new_examiner_id:
            flash('Please select an examiner.', 'warning')
            return render_template('admin/change_examiner.html', slot=slot, examiners=examiners)

        new_examiner = User.query.get(int(new_examiner_id))
        if new_examiner:
            slot.examiner_id = new_examiner.id
            db.session.commit()
            flash(f'Examiner successfully changed to {new_examiner.name}.', 'success')
            return redirect(url_for('admin_slots'))

    return render_template('admin/change_examiner.html', slot=slot, examiners=examiners)

@app.route('/admin/bookings')
@admin_required
def admin_bookings():
    bookings = Booking.query.order_by(Booking.booking_date.desc()).all()
    return render_template('admin/bookings.html', bookings=bookings)

@app.route('/admin/bookings/<int:booking_id>/reschedule', methods=['GET', 'POST'])
@admin_required
def reschedule_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    current_slot = booking.slot
    exam = current_slot.examination
    available_slots = Slot.query.filter(
        Slot.examination_id == exam.id,
        Slot.id != current_slot.id,
        Slot.status == 'Available',
        Slot.available_seats > 0
    ).all()

    if request.method == 'POST':
        new_slot_id = request.form.get('new_slot_id')
        if not new_slot_id:
            flash('Please select a new slot.', 'warning')
            return render_template('admin/reschedule_booking.html', booking=booking, available_slots=available_slots)

        new_slot = Slot.query.get_or_404(int(new_slot_id))
        if new_slot.available_seats <= 0 or new_slot.status != 'Available':
            flash('Selected slot does not have available seats.', 'danger')
            return render_template('admin/reschedule_booking.html', booking=booking, available_slots=available_slots)

        current_slot.available_seats += 1
        if current_slot.status == 'Full':
            current_slot.status = 'Available'

        new_slot.available_seats -= 1
        if new_slot.available_seats <= 0:
            new_slot.status = 'Full'

        booking.slot_id = new_slot.id
        booking.status = 'Booked'
        db.session.commit()

        flash(f'Booking for student {booking.student.name} rescheduled successfully.', 'success')
        return redirect(url_for('admin_bookings'))

    return render_template('admin/reschedule_booking.html', booking=booking, available_slots=available_slots)

@app.route('/admin/search')
@admin_required
def admin_search():
    query = request.args.get('q', '').strip()
    category = request.args.get('category', 'all')

    students = []
    examiners = []
    examinations = []
    bookings = []

    if query:
        search_pattern = f'%{query}%'

        if category in ['all', 'students']:
            students = User.query.filter(
                User.role == 'student',
                (User.name.ilike(search_pattern) | User.username.ilike(search_pattern) | User.email.ilike(search_pattern) | (User.id == (int(query) if query.isdigit() else -1)))
            ).all()

        if category in ['all', 'examiners']:
            examiners = User.query.filter(
                User.role == 'examiner',
                (User.name.ilike(search_pattern) | User.username.ilike(search_pattern) | User.email.ilike(search_pattern) | User.department.ilike(search_pattern) | (User.id == (int(query) if query.isdigit() else -1)))
            ).all()

        if category in ['all', 'examinations']:
            examinations = Examination.query.filter(
                (Examination.name.ilike(search_pattern) | (Examination.id == (int(query) if query.isdigit() else -1)))
            ).all()

        if category in ['all', 'bookings']:
            if query.isdigit():
                bookings = Booking.query.filter_by(id=int(query)).all()
            else:
                bookings = Booking.query.join(User, Booking.student_id == User.id).filter(
                    User.name.ilike(search_pattern)
                ).all()

    return render_template(
        'admin/search.html',
        query=query,
        category=category,
        students=students,
        examiners=examiners,
        examinations=examinations,
        bookings=bookings
    )
