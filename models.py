from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()


# User Table
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    email = db.Column(db.String(120), unique=True, nullable=False)

    password = db.Column(db.String(200), nullable=False)

    assignments = db.relationship(
        'Assignment',
        backref='student',
        lazy=True,
        cascade='all, delete-orphan'
    )


# Assignment Table
class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(150), nullable=False)

    subject = db.Column(db.String(100), nullable=False)

    description = db.Column(db.Text)

    due_date = db.Column(db.Date, nullable=False)

    priority = db.Column(db.String(20), nullable=False)

    status = db.Column(db.String(20), default='Pending')

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )