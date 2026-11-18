# StudyFlow — Student Assignment & Deadline Tracker

A responsive student productivity web app built with **Python Flask, SQLite, HTML, CSS and JavaScript**.

## Features
- Student registration and secure password hashing
- Login and logout
- Personal dashboard with total, pending, completed and overdue assignment counts
- Add, edit, delete and complete assignments
- Assignment subject, deadline and priority tracking
- Progress indicator based on completed assignments
- 25-minute focus timer with pause, resume and reset
- Responsive lavender-themed interface for desktop and mobile
- Docker support and automated Python tests

## Run locally (Windows)

1. Install Python 3.12 or newer.
2. Download or clone this repository.
3. Open Command Prompt in the project folder.
4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Start the website:

   ```bash
   python app.py
   ```

6. Open **http://127.0.0.1:5000** in your browser.
7. Register a new account, sign in, and add your assignments.

The SQLite database is created automatically when the app starts.

## Run with Docker

```bash
docker build -t studyflow .
docker run -p 5000:5000 studyflow
```

Then open **http://localhost:5000**.

For deployment, set a strong `SECRET_KEY` environment variable and configure `DATABASE_URL` for your database.

## Run tests

```bash
pytest
```

## Project structure

```text
.
├── app.py
├── models.py
├── requirements.txt
├── Dockerfile
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── add_assignment.html
│   └── edit_assignment.html
├── static/
│   └── style.css
└── tests/
    └── test_app.py
```
