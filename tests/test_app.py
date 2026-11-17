import os

# Use a separate temporary database for testing
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app import app, db
from models import User, Assignment


# Prepare a fresh database for every test
def setup_function():
    app.config["TESTING"] = True

    with app.app_context():
        db.drop_all()
        db.create_all()


def teardown_function():
    with app.app_context():
        db.session.remove()
        db.drop_all()


# Helper function: register and login a student
def create_logged_in_student(client):

    client.post(
        "/register",
        data={
            "name": "Test Student",
            "email": "test@example.com",
            "password": "Student@123"
        }
    )

    client.post(
        "/login",
        data={
            "email": "test@example.com",
            "password": "Student@123"
        }
    )


# Test 1: Home page
def test_home_page():

    with app.test_client() as client:
        response = client.get("/")

        assert response.status_code == 302


# Test 2: Student registration
def test_registration():

    with app.test_client() as client:

        response = client.post(
            "/register",
            data={
                "name": "Test Student",
                "email": "test@example.com",
                "password": "Student@123"
            },
            follow_redirects=True
        )

        assert response.status_code == 200

        with app.app_context():
            user = User.query.filter_by(
                email="test@example.com"
            ).first()

            assert user is not None


# Test 3: Student login
def test_login():

    with app.test_client() as client:

        create_logged_in_student(client)

        response = client.get("/dashboard")

        assert response.status_code == 200
        assert b"Welcome" in response.data


# Test 4: Add assignment
def test_add_assignment():

    with app.test_client() as client:

        create_logged_in_student(client)

        response = client.post(
            "/add-assignment",
            data={
                "title": "Java Inheritance",
                "subject": "Java",
                "description": "Complete Java assignment",
                "due_date": "2026-12-20",
                "priority": "High"
            },
            follow_redirects=True
        )

        assert response.status_code == 200

        with app.app_context():
            assignment = Assignment.query.filter_by(
                title="Java Inheritance"
            ).first()

            assert assignment is not None
            assert assignment.status == "Pending"


# Test 5: Edit assignment
def test_edit_assignment():

    with app.test_client() as client:

        create_logged_in_student(client)

        client.post(
            "/add-assignment",
            data={
                "title": "Old Title",
                "subject": "Java",
                "description": "Test",
                "due_date": "2026-12-20",
                "priority": "Medium"
            }
        )

        with app.app_context():
            assignment = Assignment.query.filter_by(
                title="Old Title"
            ).first()

            assignment_id = assignment.id

        response = client.post(
            f"/edit-assignment/{assignment_id}",
            data={
                "title": "Updated Title",
                "subject": "Java",
                "description": "Updated test",
                "due_date": "2026-12-25",
                "priority": "High"
            },
            follow_redirects=True
        )

        assert response.status_code == 200

        with app.app_context():
            updated = db.session.get(
                Assignment, assignment_id
            )

            assert updated.title == "Updated Title"

# Test 6: Complete assignment
def test_complete_assignment():

    with app.test_client() as client:

        create_logged_in_student(client)

        client.post(
            "/add-assignment",
            data={
                "title": "Python Assignment",
                "subject": "Python",
                "description": "Test completion",
                "due_date": "2026-12-20",
                "priority": "High"
            }
        )

        with app.app_context():
            assignment = Assignment.query.filter_by(
                title="Python Assignment"
            ).first()

            assignment_id = assignment.id

        response = client.post(
            f"/complete-assignment/{assignment_id}"
        )

        assert response.status_code == 302

        with app.app_context():
            assignment = db.session.get(
                Assignment, assignment_id
            )

            assert assignment.status == "Completed"
            
# Test 7: Delete assignment
def test_delete_assignment():

    with app.test_client() as client:

        create_logged_in_student(client)

        client.post(
            "/add-assignment",
            data={
                "title": "Delete Test",
                "subject": "Java",
                "description": "Delete this assignment",
                "due_date": "2026-12-20",
                "priority": "Low"
            }
        )

        with app.app_context():
            assignment = Assignment.query.filter_by(
                title="Delete Test"
            ).first()

            assignment_id = assignment.id

        response = client.post(
            f"/delete-assignment/{assignment_id}"
        )

        assert response.status_code == 302

        with app.app_context():
            deleted = db.session.get(
                Assignment, assignment_id
            )

            assert deleted is None