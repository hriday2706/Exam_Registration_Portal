from datetime import datetime, date
from flask_login import UserMixin
from app import db, bcrypt

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    department = db.Column(db.String(100))
    role = db.Column(db.String(20), nullable=False, default='student')
    status = db.Column(db.String(20), nullable=False, default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return self.status not in ['deactivated', 'rejected']

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_examiner(self):
        return self.role == 'examiner'

    @property
    def is_student(self):
        return self.role == 'student'

    @property
    def is_approved_examiner(self):
        return self.role == 'examiner' and self.status == 'active'

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(20), unique=True, nullable=False)
    course_name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default='Active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    examinations = db.relationship('Examination', backref='course', cascade='all, delete-orphan', lazy=True)

class Examination(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    exam_type = db.Column(db.String(50), nullable=False, default='Viva')
    duration = db.Column(db.Integer, nullable=False, default=30)
    max_marks = db.Column(db.Integer, nullable=False, default=100)
    slot_creation_start_date = db.Column(db.Date, nullable=False)
    slot_creation_end_date = db.Column(db.Date, nullable=False)
    slot_booking_start_date = db.Column(db.Date, nullable=False)
    slot_booking_end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(30), nullable=False, default='Draft')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    rubrics = db.relationship('Rubric', backref='examination', cascade='all, delete-orphan', lazy=True)
    slots = db.relationship('Slot', backref='examination', cascade='all, delete-orphan', lazy=True)

    @property
    def is_slot_creation_open(self):
        today = date.today()
        if self.status == 'Slot Creation':
            return True
        if self.status in ['Draft', 'Booking Open'] and self.slot_creation_start_date <= today <= self.slot_creation_end_date:
            return True
        return False

    @property
    def is_slot_booking_open(self):
        today = date.today()
        if self.status == 'Booking Open':
            return True
        if self.status not in ['Closed', 'Completed'] and self.slot_booking_start_date <= today <= self.slot_booking_end_date:
            return True
        return False

class Rubric(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    examination_id = db.Column(db.Integer, db.ForeignKey('examination.id'), nullable=False)
    criterion_name = db.Column(db.String(150), nullable=False)
    max_marks = db.Column(db.Integer, nullable=False, default=10)
    weightage = db.Column(db.Float, nullable=False, default=1.0)
    description = db.Column(db.Text)

class Slot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    examination_id = db.Column(db.Integer, db.ForeignKey('examination.id'), nullable=False)
    examiner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.String(10), nullable=False)
    end_time = db.Column(db.String(10), nullable=False)
    max_capacity = db.Column(db.Integer, nullable=False, default=1)
    available_seats = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), nullable=False, default='Available')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    examiner = db.relationship('User', foreign_keys=[examiner_id], backref='examiner_slots')
    bookings = db.relationship('Booking', backref='slot', cascade='all, delete-orphan', lazy=True)

    @property
    def booked_count(self):
        return sum(1 for b in self.bookings if b.status != 'Cancelled')

    @property
    def can_be_booked(self):
        return self.status == 'Available' and self.available_seats > 0

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey('slot.id'), nullable=False)
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default='Booked')

    student = db.relationship('User', foreign_keys=[student_id], backref='student_bookings')
    evaluation = db.relationship('Evaluation', backref='booking', uselist=False, cascade='all, delete-orphan')

class Evaluation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False, unique=True)
    examiner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_marks = db.Column(db.Float, nullable=False, default=0.0)
    remarks = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default='Completed')
    evaluated_at = db.Column(db.DateTime, default=datetime.utcnow)

    examiner = db.relationship('User', foreign_keys=[examiner_id], backref='evaluations')
    scores = db.relationship('RubricScore', backref='evaluation', cascade='all, delete-orphan', lazy=True)

class RubricScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    evaluation_id = db.Column(db.Integer, db.ForeignKey('evaluation.id'), nullable=False)
    rubric_id = db.Column(db.Integer, db.ForeignKey('rubric.id'), nullable=False)
    marks_obtained = db.Column(db.Float, nullable=False, default=0.0)
    remarks = db.Column(db.String(255))
    rubric = db.relationship('Rubric')