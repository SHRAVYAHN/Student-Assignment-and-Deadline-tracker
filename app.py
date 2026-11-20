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


def _deadline_dna_schedule(assignments, study_tasks, today, capacity_hours, shifted_id=None, delay_days=0, selected_effort=None):
    """Build a transparent 14-day, capacity-based what-if schedule."""
    horizon = 14
    fixed = [0.0 for _ in range(horizon + 1)]
    remaining = [capacity_hours for _ in range(horizon + 1)]
    jobs = []
    for task in study_tasks:
        day_index = (task.planned_date - today).days
        if 0 <= day_index <= horizon and task.status != 'Completed':
            fixed[day_index] += task.duration_minutes / 60.0
    for item in assignments:
        if item.status == 'Completed':
            continue
        due = item.due_date + (timedelta(days=delay_days) if item.id == shifted_id else timedelta())
        due_index = max(0, min(horizon, (due - today).days))
        default_effort = {'High': 4.0, 'Medium': 3.0, 'Low': 2.0}.get(item.priority, 2.0)
        effort = selected_effort if item.id == shifted_id and selected_effort is not None else default_effort
        jobs.append((due_index, item.id, effort))
    loads = fixed[:]
    for due_index, _, effort in sorted(jobs, key=lambda job: (job[0], job[1])):
        left = effort
        for day_index in range(due_index, -1, -1):
            place = min(left, remaining[day_index])
            loads[day_index] += place
            remaining[day_index] -= place
            left -= place
            if left <= 0.0001:
                break
        if left > 0:
            loads[0] += left
    overload = [max(0.0, value - capacity_hours) for value in loads]
    return {
        'loads': [round(value, 2) for value in loads],
        'overload_hours': round(sum(overload), 2),
        'overloaded_days': sum(1 for value in overload if value > 0.0001),
        'peak_hours': round(max(loads), 2),
    }


@app.route('/deadline-dna')
@login_required
def deadline_dna():
    assignments = Assignment.query.filter_by(user_id=current_user.id).filter(Assignment.status != 'Completed').order_by(Assignment.due_date.asc()).all()
    study_tasks = StudyTask.query.filter_by(user_id=current_user.id).filter(StudyTask.status != 'Completed').all()
    return render_template('deadline_dna.html', assignments=assignments, today=date.today(),
                           effort_defaults={'High': 4, 'Medium': 3, 'Low': 2})


@app.route('/deadline-dna/simulate', methods=['POST'])
@login_required
def simulate_deadline_ripple():
    data = request.get_json(silent=True) or {}
    try:
        assignment_id = int(data.get('assignment_id', 0))
        delay_days = int(data.get('delay_days', 0))
        capacity_hours = float(data.get('capacity_hours', 4))
        effort_hours = float(data.get('effort_hours', 3))
    except (TypeError, ValueError):
        return jsonify({'ok': False, 'message': 'Please enter valid simulation values.'}), 400
    if delay_days < 0 or delay_days > 14 or not (1 <= capacity_hours <= 16) or not (0.5 <= effort_hours <= 16):
        return jsonify({'ok': False, 'message': 'Use a delay from 0–14 days, daily capacity from 1–16 hours and effort from 0.5–16 hours.'}), 400
    selected = Assignment.query.filter_by(id=assignment_id, user_id=current_user.id).filter(Assignment.status != 'Completed').first()
    if selected is None:
        return jsonify({'ok': False, 'message': 'That assignment is no longer available. Refresh the page and try again.'}), 404
    assignments = Assignment.query.filter_by(user_id=current_user.id).filter(Assignment.status != 'Completed').all()
    study_tasks = StudyTask.query.filter_by(user_id=current_user.id).filter(StudyTask.status != 'Completed').all()
    today = date.today()
    before = _deadline_dna_schedule(assignments, study_tasks, today, capacity_hours)
    after = _deadline_dna_schedule(assignments, study_tasks, today, capacity_hours,
                                   shifted_id=selected.id, delay_days=delay_days,
                                   selected_effort=effort_hours)
    delta = round(after['overload_hours'] - before['overload_hours'], 2)
    if delay_days == 0:
        headline = 'Your current workload forecast'
        advice = 'No deadline was moved. Use this as your baseline and compare a possible change.'
    elif delta > 0:
        headline = 'This delay creates extra pressure'
        advice = f'The change adds {delta:g} overload hours. Try protecting a study block earlier in the week or reducing another commitment before postponing.'
    elif delta < 0:
        headline = 'The later date creates breathing room'
        advice = f'The simulation reduces overloaded work by {abs(delta):g} hours. Keep the newly freed time reserved for this assignment.'
    else:
        headline = 'The pressure moves, but does not disappear'
        advice = 'The total overload stays about the same. Check which days become busier and plan a buffer before the revised deadline.'
    labels = [(today + timedelta(days=i)).strftime('%a, %d %b') for i in range(15)]
    return jsonify({
        'ok': True, 'assignment': selected.title, 'original_due': selected.due_date.isoformat(),
        'simulated_due': (selected.due_date + timedelta(days=delay_days)).isoformat(),
        'delay_days': delay_days, 'capacity_hours': capacity_hours,
        'before': before, 'after': after, 'overload_delta': delta,
        'headline': headline, 'advice': advice, 'labels': labels,
        'method_note': 'Planning estimate, not a prediction of grades or guaranteed completion. Assignment effort is estimated from priority unless adjusted here; your planned study sessions count as fixed workload.'
    })


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
