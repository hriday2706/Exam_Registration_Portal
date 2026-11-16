from functools import wraps
from datetime import datetime, date
from flask import render_template, request, redirect, url_for, flash
from flask_login import current_user, logout_user
from app import app, db
from models import User, Examination, Rubric, Slot, Booking, Evaluation, RubricScore

def examiner_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if not current_user.is_examiner:
            flash('Examiner access required.', 'danger')
            return redirect(url_for('index'))
        if current_user.status in ['deactivated', 'rejected']:
            logout_user()
            flash('Access denied. Account is not active.', 'danger')
            return redirect(url_for('login'))
        if current_user.status != 'active':
            return redirect(url_for('examiner_pending'))
        return function(*args, **kwargs)
    return wrapper

@app.route('/examiner/dashboard')
@examiner_required
def examiner_dashboard():
    my_slots = Slot.query.filter_by(examiner_id=current_user.id).all()
    slot_ids = [s.id for s in my_slots]

    my_bookings = Booking.query.filter(Booking.slot_id.in_(slot_ids)).all() if slot_ids else []
    total_booked_students = sum(1 for b in my_bookings if b.status != 'Cancelled')

    pending_evaluations_count = 0
    for b in my_bookings:
        if b.status != 'Cancelled' and not b.evaluation:
            pending_evaluations_count += 1

    open_exams = Examination.query.filter(
        Examination.status.in_(['Draft', 'Slot Creation'])
    ).all()
    available_for_slots = [e for e in open_exams if e.is_slot_creation_open]

    recent_slots = Slot.query.filter_by(examiner_id=current_user.id).order_by(Slot.date.desc(), Slot.start_time.desc()).limit(5).all()

    return render_template(
        'examiner/dashboard.html',
        total_slots=len(my_slots),
        total_booked_students=total_booked_students,
        pending_evaluations=pending_evaluations_count,
        available_exams_count=len(available_for_slots),
        recent_slots=recent_slots
    )

@app.route('/examiner/examinations')
@examiner_required
def examiner_examinations():
    examinations = Examination.query.order_by(Examination.slot_creation_end_date.asc()).all()
    return render_template('examiner/examinations.html', examinations=examinations)

@app.route('/examiner/slots')
@examiner_required
def examiner_slots():
    slots = Slot.query.filter_by(examiner_id=current_user.id).order_by(Slot.date.desc(), Slot.start_time.asc()).all()
    return render_template('examiner/slots.html', slots=slots)

@app.route('/examiner/slots/new', methods=['GET', 'POST'])
@examiner_required
def new_slot():
    examinations = Examination.query.filter(
        Examination.status.in_(['Draft', 'Slot Creation', 'Booking Open'])
    ).all()
    eligible_exams = [e for e in examinations if e.is_slot_creation_open]

    if request.method == 'POST':
        exam_id = request.form.get('examination_id')
        slot_date = request.form.get('date')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        capacity = request.form.get('max_capacity', 1)

        if not exam_id or not slot_date or not start_time or not end_time or not capacity:
            flash('All slot fields are required.', 'warning')
            return render_template('examiner/slot_form.html', action='Create', slot=None, examinations=eligible_exams)

        exam = Examination.query.get_or_404(int(exam_id))
        if not exam.is_slot_creation_open:
            flash('Slot creation period is closed for this examination.', 'danger')
            return render_template('examiner/slot_form.html', action='Create', slot=None, examinations=eligible_exams)

        slot = Slot(
            examination_id=exam.id,
            examiner_id=current_user.id,
            date=datetime.strptime(slot_date, '%Y-%m-%d').date(),
            start_time=start_time,
            end_time=end_time,
            max_capacity=int(capacity),
            available_seats=int(capacity),
            status='Available'
        )
        db.session.add(slot)
        db.session.commit()
        flash('Examination slot created successfully.', 'success')
        return redirect(url_for('examiner_slots'))

    return render_template('examiner/slot_form.html', action='Create', slot=None, examinations=eligible_exams)

@app.route('/examiner/slots/edit/<int:slot_id>', methods=['GET', 'POST'])
@examiner_required
def edit_slot(slot_id):
    slot = Slot.query.filter_by(id=slot_id, examiner_id=current_user.id).first_or_404()

    if slot.booked_count > 0:
        flash('Cannot edit slot because students have already booked it.', 'danger')
        return redirect(url_for('examiner_slots'))

    exam = slot.examination
    if exam.is_slot_booking_open:
        flash('Cannot update slot after booking has started.', 'danger')
        return redirect(url_for('examiner_slots'))

    if request.method == 'POST':
        slot_date = request.form.get('date')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        capacity = request.form.get('max_capacity', 1)

        if not slot_date or not start_time or not end_time or not capacity:
            flash('All slot fields are required.', 'warning')
            return render_template('examiner/slot_form.html', action='Edit', slot=slot, examinations=[exam])

        slot.date = datetime.strptime(slot_date, '%Y-%m-%d').date()
        slot.start_time = start_time
        slot.end_time = end_time
        slot.max_capacity = int(capacity)
        slot.available_seats = int(capacity)
        db.session.commit()

        flash('Slot updated successfully.', 'success')
        return redirect(url_for('examiner_slots'))

    return render_template('examiner/slot_form.html', action='Edit', slot=slot, examinations=[exam])

@app.route('/examiner/slots/delete/<int:slot_id>', methods=['POST'])
@examiner_required
def delete_slot(slot_id):
    slot = Slot.query.filter_by(id=slot_id, examiner_id=current_user.id).first_or_404()
    if slot.booked_count > 0:
        flash('Cannot delete slot with existing bookings.', 'danger')
        return redirect(url_for('examiner_slots'))

    db.session.delete(slot)
    db.session.commit()
    flash('Slot deleted successfully.', 'info')
    return redirect(url_for('examiner_slots'))

@app.route('/examiner/students')
@examiner_required
def examiner_students():
    my_slots = Slot.query.filter_by(examiner_id=current_user.id).all()
    slot_ids = [s.id for s in my_slots]
    bookings = Booking.query.filter(Booking.slot_id.in_(slot_ids)).order_by(Booking.booking_date.desc()).all() if slot_ids else []
    return render_template('examiner/students.html', bookings=bookings)

@app.route('/examiner/evaluate/<int:booking_id>', methods=['GET', 'POST'])
@examiner_required
def evaluate_student(booking_id):
    booking = Booking.query.get_or_404(booking_id)

    if booking.slot.examiner_id != current_user.id:
        flash('You can only evaluate students booked in your own slots.', 'danger')
        return redirect(url_for('examiner_students'))

    exam = booking.slot.examination
    rubrics = Rubric.query.filter_by(examination_id=exam.id).all()
    existing_evaluation = Evaluation.query.filter_by(booking_id=booking.id).first()

    if request.method == 'POST':
        overall_remarks = request.form.get('remarks', '').strip()
        total_marks = 0.0

        if not existing_evaluation:
            evaluation = Evaluation(
                booking_id=booking.id,
                examiner_id=current_user.id,
                total_marks=0.0,
                remarks=overall_remarks,
                status='Completed'
            )
            db.session.add(evaluation)
            db.session.flush()
        else:
            evaluation = existing_evaluation
            evaluation.remarks = overall_remarks
            evaluation.status = 'Completed'
            RubricScore.query.filter_by(evaluation_id=evaluation.id).delete()

        if rubrics:
            for r in rubrics:
                score_val = request.form.get(f'rubric_marks_{r.id}', 0)
                criterion_remarks = request.form.get(f'rubric_remarks_{r.id}', '').strip()
                try:
                    marks = float(score_val)
                except ValueError:
                    marks = 0.0
                if marks > r.max_marks:
                    marks = float(r.max_marks)
                if marks < 0:
                    marks = 0.0

                total_marks += marks
                rs = RubricScore(
                    evaluation_id=evaluation.id,
                    rubric_id=r.id,
                    marks_obtained=marks,
                    remarks=criterion_remarks
                )
                db.session.add(rs)
        else:
            manual_marks = request.form.get('total_marks', 0)
            try:
                total_marks = float(manual_marks)
            except ValueError:
                total_marks = 0.0

        evaluation.total_marks = total_marks
        booking.status = 'Completed'
        db.session.commit()

        flash(f'Evaluation submitted successfully for {booking.student.name}. Total marks: {total_marks}', 'success')
        return redirect(url_for('examiner_students'))

    return render_template(
        'examiner/evaluate.html',
        booking=booking,
        exam=exam,
        rubrics=rubrics,
        evaluation=existing_evaluation
    )

@app.route('/examiner/profile', methods=['GET', 'POST'])
@examiner_required
def examiner_profile():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        department = request.form.get('department', '').strip()

        if not name:
            flash('Name is required.', 'warning')
            return render_template('examiner/profile.html')

        current_user.name = name
        current_user.phone = phone
        current_user.department = department
        db.session.commit()

        flash('Profile updated successfully.', 'success')
        return redirect(url_for('examiner_profile'))

    return render_template('examiner/profile.html')
