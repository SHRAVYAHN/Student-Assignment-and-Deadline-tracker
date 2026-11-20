import os
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
from app import app, db
from models import User, Assignment, StudyTask, FocusSession

def setup_function():
    app.config["TESTING"] = True
    with app.app_context():
        db.drop_all()
        db.create_all()

def teardown_function():
    with app.app_context():
        db.session.remove()
        db.drop_all()

def create_logged_in_student(client):
    client.post("/register", data={"name": "Test Student", "email": "test@example.com", "password": "Student@123"})
    client.post("/login", data={"email": "test@example.com", "password": "Student@123"})

def test_home_page():
    with app.test_client() as client:
        assert client.get("/").status_code == 302

def test_registration():
    with app.test_client() as client:
        response = client.post("/register", data={"name": "Test Student", "email": "test@example.com", "password": "Student@123"}, follow_redirects=True)
        assert response.status_code == 200
        with app.app_context():
            assert User.query.filter_by(email="test@example.com").first() is not None

def test_login_and_dashboard():
    with app.test_client() as client:
        create_logged_in_student(client)
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert b"Welcome" in response.data
        assert b"Study Planner" in response.data

def test_add_assignment():
    with app.test_client() as client:
        create_logged_in_student(client)
        response = client.post("/add-assignment", data={"title": "Java Inheritance", "subject": "Java", "description": "Complete Java assignment", "due_date": "2026-12-20", "priority": "High"}, follow_redirects=True)
        assert response.status_code == 200
        with app.app_context():
            assignment = Assignment.query.filter_by(title="Java Inheritance").first()
            assert assignment is not None and assignment.status == "Pending"

def test_edit_assignment():
    with app.test_client() as client:
        create_logged_in_student(client)
        client.post("/add-assignment", data={"title": "Old Title", "subject": "Java", "description": "Test", "due_date": "2026-12-20", "priority": "Medium"})
        with app.app_context():
            assignment_id = Assignment.query.filter_by(title="Old Title").first().id
        response = client.post(f"/edit-assignment/{assignment_id}", data={"title": "Updated Title", "subject": "Java", "description": "Updated test", "due_date": "2026-12-25", "priority": "High"}, follow_redirects=True)
        assert response.status_code == 200
        with app.app_context():
            assert db.session.get(Assignment, assignment_id).title == "Updated Title"

def test_complete_and_delete_assignment():
    with app.test_client() as client:
        create_logged_in_student(client)
        client.post("/add-assignment", data={"title": "Python Assignment", "subject": "Python", "description": "Test completion", "due_date": "2026-12-20", "priority": "High"})
        with app.app_context():
            assignment_id = Assignment.query.filter_by(title="Python Assignment").first().id
        assert client.post(f"/complete-assignment/{assignment_id}").status_code == 302
        with app.app_context():
            assert db.session.get(Assignment, assignment_id).status == "Completed"
        assert client.post(f"/delete-assignment/{assignment_id}").status_code == 302

def test_study_planner_create_complete_and_delete():
    with app.test_client() as client:
        create_logged_in_student(client)
        assert client.get("/study-planner").status_code == 200
        response = client.post("/study-planner", data={"title": "Revise linked lists", "subject": "DSA", "planned_date": "2026-11-21", "duration_minutes": "45"}, follow_redirects=True)
        assert response.status_code == 200
        with app.app_context():
            task = StudyTask.query.filter_by(title="Revise linked lists").first()
            assert task is not None and task.duration_minutes == 45
            task_id = task.id
        assert client.post(f"/study-task/{task_id}/complete").status_code == 302
        with app.app_context():
            assert db.session.get(StudyTask, task_id).status == "Completed"
        assert client.post(f"/study-task/{task_id}/delete").status_code == 302

def test_focus_session_is_saved_and_achievements_render():
    with app.test_client() as client:
        create_logged_in_student(client)
        assert client.get("/focus-timer").status_code == 200
        response = client.post("/focus-session", json={"minutes": 25})
        assert response.status_code == 200
        assert response.get_json()["total_minutes"] == 25
        with app.app_context():
            assert FocusSession.query.count() == 1
        achievements = client.get("/achievements")
        assert achievements.status_code == 200
        assert b"Focus Starter" in achievements.data

def test_focus_session_validation():
    with app.test_client() as client:
        create_logged_in_student(client)
        response = client.post("/focus-session", json={"minutes": 0})
        assert response.status_code == 400
