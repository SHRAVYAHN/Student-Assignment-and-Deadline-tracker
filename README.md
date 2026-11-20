# StudyFlow — Student Assignment & Deadline Tracker

A responsive student productivity web app built with **Python Flask, SQLite, HTML, CSS and JavaScript**.

## Features
- Student registration, secure password hashing, login and logout
- Personal dashboard with assignment totals, pending, completed and overdue counts
- Add, edit, delete and complete assignments
- Dedicated assignment list and deadline calendar anchor
- **Smart Study Planner:** add study goals by subject, date and duration; mark them complete or remove them
- **Focus Mode:** 25-minute, 50-minute and 5-minute timer presets; completed sessions are saved to the signed-in student's progress
- **Motivation & Achievement Zone:** milestone badges, completed-work totals, focus time and study streak
- Responsive lavender, purple and navy interface for desktop and mobile
- Docker support and automated Python tests

## Run locally (Windows)
1. Install Python 3.12 or newer.
2. Clone or download this repository.
3. Open Command Prompt in the project folder.
4. Install dependencies: `pip install -r requirements.txt`
5. Start the website: `python app.py`
6. Open **http://127.0.0.1:5000**, register and sign in.

SQLite tables are created automatically on startup. New planner and focus tables are added without changing existing assignment rows.

## Run tests
`python -m pytest tests -v`

## Run with Docker
```bash
docker build -t studyflow .
docker run -p 5000:5000 studyflow
```
Then open **http://localhost:5000**.

For deployment, configure a strong `SECRET_KEY` and a persistent database using `DATABASE_URL`. SQLite on an ephemeral hosting filesystem is not suitable for production persistence.

## New pages
- `/study-planner`
- `/focus-timer`
- `/achievements`

## Project structure
```text
.
├── app.py
├── models.py
├── requirements.txt
├── Dockerfile
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── assignments.html
│   ├── study_planner.html
│   ├── focus_timer.html
│   ├── achievements.html
│   └── login/register/add/edit assignment pages
├── static/style.css
└── tests/test_app.py
```
