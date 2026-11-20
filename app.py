import os
from datetime import date, datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Assignment, StudyTask, FocusSession

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'local-development-key-change-before-deployment')
database_url = os.environ.get('DATABASE_URL', 'sqlite:///assignments.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


with app.app_context():
    db.create_all()


@app.route('/')
def home():
    return redirect(url_for('dashboard' if current_user.is_authenticated else 'login'))


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
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please login.', 'error')
            return redirect(url_for('login'))
        db.session.add(User(name=name, email=email, password=generate_password_hash(password)))
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


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


@app.route('/dashboard')
@login_required
def dashboard():
    assignments = Assignment.query.filter_by(user_id=current_user.id).order_by(Assignment.due_date.asc()).all()
    total = len(assignments)
    pending = sum(1 for item in assignments if item.status == 'Pending')
    completed = sum(1 for item in assignments if item.status == 'Completed')
    overdue = sum(1 for item in assignments if item.status != 'Completed' and item.due_date < date.today())
    return render_template('dashboard.html', assignments=assignments, total=total, pending=pending,
                           completed=completed, overdue=overdue)


@app.route('/assignments')
@login_required
def assignments():
    all_assignments = Assignment.query.filter_by(user_id=current_user.id).order_by(Assignment.due_date.asc()).all()
    return render_template('assignments.html', assignments=all_assignments)


@app.route('/study-planner', methods=['GET', 'POST'])
@login_required
def study_planner():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        subject = request.form.get('subject', '').strip()
        planned_date_text = request.form.get('planned_date', '')
        duration_text = request.form.get('duration_minutes', '30')
        if not title or not subject or not planned_date_text:
            flash('Add a task, subject and study date.', 'error')
            return redirect(url_for('study_planner'))
        try:
            planned_date = date.fromisoformat(planned_date_text)
            duration = int(duration_text)
            if duration < 5 or duration > 300:
                raise ValueError
        except ValueError:
            flash('Choose a valid date and a duration between 5 and 300 minutes.', 'error')
            return redirect(url_for('study_planner'))
        db.session.add(StudyTask(title=title, subject=subject, planned_date=planned_date,
                                 duration_minutes=duration, user_id=current_user.id))
        db.session.commit()
        flash('Study session added to your plan!', 'success')
        return redirect(url_for('study_planner'))
    tasks = StudyTask.query.filter_by(user_id=current_user.id).order_by(StudyTask.planned_date.asc()).all()
    today = date.today()
    return render_template('study_planner.html', tasks=tasks, today=today,
                           planned_count=sum(1 for task in tasks if task.status == 'Planned'),
                           completed_count=sum(1 for task in tasks if task.status == 'Completed'))


@app.route('/study-task/<int:task_id>/complete', methods=['POST'])
@login_required
def complete_study_task(task_id):
    task = StudyTask.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    task.status = 'Completed'
    db.session.commit()
    flash('Study goal completed. Nice work!', 'success')
    return redirect(url_for('study_planner'))


@app.route('/study-task/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_study_task(task_id):
    task = StudyTask.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    db.session.delete(task)
    db.session.commit()
    flash('Study goal removed.', 'success')
    return redirect(url_for('study_planner'))


@app.route('/focus-timer')
@login_required
def focus_timer():
    sessions = FocusSession.query.filter_by(user_id=current_user.id).all()
    today = date.today()
    today_minutes = sum(s.minutes for s in sessions if s.completed_at.date() == today)
    total_minutes = sum(s.minutes for s in sessions)
    return render_template('focus_timer.html', today_minutes=today_minutes, total_minutes=total_minutes,
                           session_count=len(sessions))


@app.route('/focus-session', methods=['POST'])
@login_required
def save_focus_session():
    data = request.get_json(silent=True) or request.form
    try:
        minutes = int(data.get('minutes', 0))
    except (TypeError, ValueError):
        return jsonify({'ok': False, 'message': 'Invalid session length.'}), 400
    if minutes < 1 or minutes > 180:
        return jsonify({'ok': False, 'message': 'Session must be between 1 and 180 minutes.'}), 400
    db.session.add(FocusSession(minutes=minutes, completed_at=datetime.utcnow(), user_id=current_user.id))
    db.session.commit()
    total = db.session.query(db.func.coalesce(db.func.sum(FocusSession.minutes), 0)).filter_by(user_id=current_user.id).scalar()
    return jsonify({'ok': True, 'total_minutes': int(total)})


@app.route('/achievements')
@login_required
def achievements():
    assignments = Assignment.query.filter_by(user_id=current_user.id).all()
    study_tasks = StudyTask.query.filter_by(user_id=current_user.id).all()
    sessions = FocusSession.query.filter_by(user_id=current_user.id).all()
    completed_assignments = sum(1 for item in assignments if item.status == 'Completed')
    completed_study_tasks = sum(1 for item in study_tasks if item.status == 'Completed')
    focus_minutes = sum(item.minutes for item in sessions)
    active_dates = {item.completed_at.date() for item in sessions}
    active_dates.update(item.planned_date for item in study_tasks if item.status == 'Completed')
    active_dates.update(item.due_date for item in assignments if item.status == 'Completed')
    streak = 0
    cursor = date.today()
    if cursor not in active_dates:
        cursor -= timedelta(days=1)
    while cursor in active_dates:
        streak += 1
        cursor -= timedelta(days=1)
    badges = [
        {'name': 'First Step', 'detail': 'Complete your first assignment', 'icon': '🌱', 'earned': completed_assignments >= 1},
        {'name': 'Task Tamer', 'detail': 'Complete 5 assignments', 'icon': '🏅', 'earned': completed_assignments >= 5},
        {'name': 'Study Planner', 'detail': 'Complete 3 planned study goals', 'icon': '📚', 'earned': completed_study_tasks >= 3},
        {'name': 'Focus Starter', 'detail': 'Log your first focus session', 'icon': '⏱️', 'earned': focus_minutes >= 1},
        {'name': 'Deep Focus', 'detail': 'Reach 5 focused hours', 'icon': '🧠', 'earned': focus_minutes >= 300},
        {'name': 'Consistency', 'detail': 'Build a 3-day study streak', 'icon': '🔥', 'earned': streak >= 3},
    ]
    earned_count = sum(1 for badge in badges if badge['earned'])
    return render_template('achievements.html', badges=badges, earned_count=earned_count,
                           badge_count=len(badges), completed_assignments=completed_assignments,
                           completed_study_tasks=completed_study_tasks, focus_minutes=focus_minutes,
                           streak=streak)


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
        db.session.add(Assignment(title=title, subject=subject, description=description, due_date=due_date,
                                  priority=priority, status='Pending', user_id=current_user.id))
        db.session.commit()
        flash('Assignment added successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_assignment.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have logged out successfully.', 'success')
    return redirect(url_for('login'))


@app.route('/edit-assignment/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
def edit_assignment(assignment_id):
    assignment = Assignment.query.filter_by(id=assignment_id, user_id=current_user.id).first_or_404()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        subject = request.form.get('subject', '').strip()
        description = request.form.get('description', '').strip()
        due_date_text = request.form.get('due_date', '')
        priority = request.form.get('priority', '')
        if not title or not subject or not due_date_text:
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('edit_assignment', assignment_id=assignment.id))
        if priority not in ['High', 'Medium', 'Low']:
            flash('Invalid priority.', 'error')
            return redirect(url_for('edit_assignment', assignment_id=assignment.id))
        try:
            due_date = date.fromisoformat(due_date_text)
        except ValueError:
            flash('Invalid due date.', 'error')
            return redirect(url_for('edit_assignment', assignment_id=assignment.id))
        assignment.title, assignment.subject, assignment.description = title, subject, description
        assignment.due_date, assignment.priority = due_date, priority
        db.session.commit()
        flash('Assignment updated successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('edit_assignment.html', assignment=assignment)


@app.route('/delete-assignment/<int:assignment_id>', methods=['POST'])
@login_required
def delete_assignment(assignment_id):
    assignment = Assignment.query.filter_by(id=assignment_id, user_id=current_user.id).first_or_404()
    db.session.delete(assignment)
    db.session.commit()
    flash('Assignment deleted successfully!', 'success')
    return redirect(url_for('dashboard'))


@app.route('/complete-assignment/<int:assignment_id>', methods=['POST'])
@login_required
def complete_assignment(assignment_id):
    assignment = Assignment.query.filter_by(id=assignment_id, user_id=current_user.id).first_or_404()
    assignment.status = 'Completed'
    db.session.commit()
    flash('Assignment marked as completed!', 'success')
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
