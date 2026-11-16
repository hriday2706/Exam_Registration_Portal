from functools import wraps
from datetime import datetime, date
from flask import render_template, request, redirect, url_for, flash
from flask_login import current_user, logout_user
from app import app, db
from models import User, Course, Examination, Slot, Booking, Evaluation

def student_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if not current_user.is_student:
            flash('Student access required.', 'danger')
            return redirect(url_for('index'))
        if current_user.status in ['deactivated', 'rejected']:
            logout_user()
            flash('Access denied. Account is not active.', 'danger')
            return redirect(url_for('login'))
        return function(*args, **kwargs)
    return wrapper

@app.route('/student/dashboard')
@student_required
def student_dashboard():
    all_exams = Examination.query.all()
    available_exams = [e for e in all_exams if e.is_slot_booking_open]

    active_bookings = Booking.query.filter_by(
        student_id=current_user.id,
        status='Booked'
    ).all()

    completed_evaluations = [b.evaluation for b in current_user.student_bookings if b.evaluation]

    all_open_slots = Slot.query.filter_by(status='Available').filter(Slot.available_seats > 0).count()

    return render_template(
        'student/dashboard.html',
        available_exams_count=len(available_exams),
        active_bookings_count=len(active_bookings),
        completed_evaluations_count=len(completed_evaluations),
        available_slots_count=all_open_slots,
        active_bookings=active_bookings,
        recent_results=completed_evaluations[:5]
    )

@app.route('/student/examinations')
@student_required
def student_examinations():
    search_query = request.args.get('q', '').strip()
    course_filter = request.args.get('course', '')
    type_filter = request.args.get('type', '')

    query = Examination.query

    if search_query:
        query = query.filter(Examination.name.ilike(f'%{search_query}%'))

    if course_filter:
        query = query.filter_by(course_id=int(course_filter))

    if type_filter:
        query = query.filter_by(exam_type=type_filter)

    examinations = query.order_by(Examination.slot_booking_start_date.asc()).all()
    courses = Course.query.filter_by(status='Active').all()

    my_booked_exam_ids = [
        b.slot.examination_id for b in current_user.student_bookings if b.status == 'Booked'
    ]

    return render_template(
        'student/examinations.html',
        examinations=examinations,
        courses=courses,
        search_query=search_query,
        course_filter=course_filter,
        type_filter=type_filter,
        my_booked_exam_ids=my_booked_exam_ids
    )

@app.route('/student/examinations/<int:exam_id>/slots')
@student_required
def student_slots(exam_id):
    exam = Examination.query.get_or_404(exam_id)

    already_booked = Booking.query.join(Slot).filter(
        Booking.student_id == current_user.id,
        Booking.status == 'Booked',
        Slot.examination_id == exam.id
    ).first()

    slots = Slot.query.filter_by(examination_id=exam.id).order_by(Slot.date.asc(), Slot.start_time.asc()).all()

    return render_template(
        'student/slots.html',
        exam=exam,
        slots=slots,
        already_booked=already_booked
    )

@app.route('/student/book-slot/<int:slot_id>', methods=['POST'])
@student_required
def book_slot(slot_id):
    slot = Slot.query.get_or_404(slot_id)
    exam = slot.examination

    if not exam.is_slot_booking_open:
        flash('Booking period is currently closed for this examination.', 'danger')
        return redirect(url_for('student_slots', exam_id=exam.id))

    existing_booking = Booking.query.join(Slot).filter(
        Booking.student_id == current_user.id,
        Booking.status == 'Booked',
        Slot.examination_id == exam.id
    ).first()

    if existing_booking:
        flash('You already have an active booking for this examination.', 'warning')
        return redirect(url_for('my_bookings'))

    if slot.available_seats <= 0 or slot.status != 'Available':
        flash('This slot is fully booked or unavailable.', 'danger')
        return redirect(url_for('student_slots', exam_id=exam.id))

    slot.available_seats -= 1
    if slot.available_seats <= 0:
        slot.status = 'Full'

    booking = Booking(
        student_id=current_user.id,
        slot_id=slot.id,
        status='Booked'
    )
    db.session.add(booking)
    db.session.commit()

    flash('Slot booked successfully!', 'success')
    return redirect(url_for('my_bookings'))

@app.route('/student/cancel-booking/<int:booking_id>', methods=['POST'])
@student_required
def cancel_booking(booking_id):
    booking = Booking.query.filter_by(id=booking_id, student_id=current_user.id).first_or_404()

    if booking.status != 'Booked':
        flash('This booking is not active.', 'warning')
        return redirect(url_for('my_bookings'))

    exam = booking.slot.examination
    today = date.today()
    if exam.slot_booking_end_date < today or booking.slot.date < today:
        flash('Cannot cancel booking after the booking deadline or slot date has passed.', 'danger')
        return redirect(url_for('my_bookings'))

    booking.status = 'Cancelled'
    slot = booking.slot
    slot.available_seats += 1
    if slot.status == 'Full':
        slot.status = 'Available'

    db.session.commit()
    flash('Booking cancelled successfully.', 'info')
    return redirect(url_for('my_bookings'))

@app.route('/student/my-bookings')
@student_required
def my_bookings():
    bookings = Booking.query.filter_by(
        student_id=current_user.id,
        status='Booked'
    ).order_by(Booking.booking_date.desc()).all()
    today = date.today()
    return render_template('student/my_bookings.html', bookings=bookings, today=today)

@app.route('/student/history')
@student_required
def student_history():
    bookings = Booking.query.filter_by(
        student_id=current_user.id
    ).order_by(Booking.booking_date.desc()).all()
    return render_template('student/history.html', bookings=bookings)

@app.route('/student/results')
@student_required
def student_results():
    evaluations = Evaluation.query.join(Booking).filter(
        Booking.student_id == current_user.id
    ).order_by(Evaluation.evaluated_at.desc()).all()
    return render_template('student/results.html', evaluations=evaluations)

@app.route('/student/profile', methods=['GET', 'POST'])
@student_required
def student_profile():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()

        if not name:
            flash('Name is required.', 'warning')
            return render_template('student/profile.html')

        current_user.name = name
        current_user.phone = phone
        db.session.commit()

        flash('Profile updated successfully.', 'success')
        return redirect(url_for('student_profile'))

    return render_template('student/profile.html')
