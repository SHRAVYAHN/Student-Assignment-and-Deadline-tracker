import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date

from models import db, User,Assignment

app = Flask(__name__)

# Application configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'local-development-key-change-before-deployment')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'sqlite:///assignments.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Database connection
db.init_app(app)

# Login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# Create database tables
with app.app_context():
    db.create_all()


# Home page
@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    return redirect(url_for('login'))


# Registration page
@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not name or not email or not password:
            flash('Please fill in all fields.', 'error')
            return redirect(url_for('register'))

        if len(password) < 8:
            flash('Password must contain at least 8 characters.', 'error')
            return redirect(url_for('register'))

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash('Email already registered. Please login.', 'error')
            return redirect(url_for('login'))

        hashed_password = generate_password_hash(password)

        new_user = User(
            name=name,
            email=email,
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')

        return redirect(url_for('login'))

    return render_template('register.html')


# Login page
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):

            login_user(user)

            flash('Login successful!', 'success')

            return redirect(url_for('dashboard'))

        flash('Invalid email or password.', 'error')

    return render_template('login.html')


# Dashboard placeholder
@app.route('/dashboard')
@login_required
def dashboard():

    assignments = Assignment.query.filter_by(
        user_id=current_user.id
    ).order_by(Assignment.due_date.asc()).all()

    total = len(assignments)

    pending = sum(
        1 for a in assignments if a.status == 'Pending'
    )

    completed = sum(
        1 for a in assignments if a.status == 'Completed'
    )

    overdue = sum(
        1 for a in assignments
        if a.status != 'Completed' and a.due_date < date.today()
    )

    return render_template(
        'dashboard.html',
        assignments=assignments,
        total=total,
        pending=pending,
        completed=completed,
        overdue=overdue
    )
    

# Separate page showing every assignment for the signed-in student
@app.route('/assignments')
@login_required
def assignments():
    all_assignments = Assignment.query.filter_by(
        user_id=current_user.id
    ).order_by(Assignment.due_date.asc()).all()
    return render_template('assignments.html', assignments=all_assignments)


# Dedicated focus timer page
@app.route('/focus-timer')
@login_required
def focus_timer():
    return render_template('focus_timer.html')


#Assignment

@app.route('/add-assignment', methods=['GET', 'POST'])
@login_required
def add_assignment():

    if request.method == 'POST':

        title = request.form.get('title', '').strip()
        subject = request.form.get('subject', '').strip()
        description = request.form.get('description', '').strip()
        due_date_text = request.form.get('due_date', '')
        priority = request.form.get('priority', '')

        if not title or not subject or not due_date_text:
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('add_assignment'))

        if priority not in ['High', 'Medium', 'Low']:
            flash('Please select a valid priority.', 'error')
            return redirect(url_for('add_assignment'))

        try:
            due_date = date.fromisoformat(due_date_text)
        except ValueError:
            flash('Please enter a valid deadline.', 'error')
            return redirect(url_for('add_assignment'))

        new_assignment = Assignment(
            title=title,
            subject=subject,
            description=description,
            due_date=due_date,
            priority=priority,
            status='Pending',
            user_id=current_user.id
        )

        db.session.add(new_assignment)
        db.session.commit()

        flash('Assignment added successfully!', 'success')

        return redirect(url_for('dashboard'))

    return render_template('add_assignment.html')

# Logout
@app.route('/logout')
@login_required
def logout():

    logout_user()

    flash('You have logged out successfully.', 'success')

    return redirect(url_for('login'))

# Edit assignment
@app.route('/edit-assignment/<int:assignment_id>',
           methods=['GET', 'POST'])
@login_required
def edit_assignment(assignment_id):

    assignment = Assignment.query.filter_by(
        id=assignment_id,
        user_id=current_user.id
    ).first_or_404()

    if request.method == 'POST':

        title = request.form.get('title', '').strip()
        subject = request.form.get('subject', '').strip()
        description = request.form.get('description', '').strip()
        due_date_text = request.form.get('due_date', '')
        priority = request.form.get('priority', '')

        if not title or not subject or not due_date_text:
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for(
                'edit_assignment', assignment_id=assignment.id
            ))

        if priority not in ['High', 'Medium', 'Low']:
            flash('Invalid priority.', 'error')
            return redirect(url_for(
                'edit_assignment', assignment_id=assignment.id
            ))

        try:
            due_date = date.fromisoformat(due_date_text)
        except ValueError:
            flash('Invalid due date.', 'error')
            return redirect(url_for(
                'edit_assignment', assignment_id=assignment.id
            ))

        assignment.title = title
        assignment.subject = subject
        assignment.description = description
        assignment.due_date = due_date
        assignment.priority = priority

        db.session.commit()

        flash('Assignment updated successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template(
        'edit_assignment.html',
        assignment=assignment
    )


# Delete assignment
@app.route('/delete-assignment/<int:assignment_id>',
           methods=['POST'])
@login_required
def delete_assignment(assignment_id):

    assignment = Assignment.query.filter_by(
        id=assignment_id,
        user_id=current_user.id
    ).first_or_404()

    db.session.delete(assignment)
    db.session.commit()

    flash('Assignment deleted successfully!', 'success')

    return redirect(url_for('dashboard'))


# Mark assignment as completed
@app.route('/complete-assignment/<int:assignment_id>',
           methods=['POST'])
@login_required
def complete_assignment(assignment_id):

    assignment = Assignment.query.filter_by(
        id=assignment_id,
        user_id=current_user.id
    ).first_or_404()

    assignment.status = 'Completed'

    db.session.commit()

    flash('Assignment marked as completed!', 'success')

    return redirect(url_for('dashboard'))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
