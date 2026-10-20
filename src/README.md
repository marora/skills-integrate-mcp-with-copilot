# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Teacher-only sign up and unregister actions
- Public read-only activity and participant lists
- Teacher login backed by PBKDF2 password hashes and signed session cookies

## Getting Started

1. From the repository root, install the dependencies:

   ```
   pip install -r requirements.txt
   ```

2. From the repository root, run the application:

   ```
   uvicorn src.app:app --reload
   ```

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## Configure teacher access

Create a password hash for each assigned teacher password:

```bash
python scripts/hash_teacher_password.py
```

The script prompts for a username and password, then prints a JSON object
containing the password hash. Set `TEACHER_PASSWORD_HASHES` to a JSON object
mapping each teacher username to its generated hash. Store this value in your
deployment's secret manager; do not commit credentials or hashes to the
repository.

Set `SESSION_SECRET_KEY` to a persistent, randomly generated secret of at
least 32 bytes. For local HTTP development only, set
`SESSION_COOKIE_SECURE=false`; the secure-cookie default is enabled and should
remain enabled when serving the application over HTTPS. Teacher sessions last
up to eight hours and are invalidated when the teacher logs out.

If teacher credentials are not configured, the site remains available in
read-only mode and management endpoints return an explicit configuration error.

## Run tests

Install the development dependencies and run the authentication tests:

```bash
pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| GET    | `/auth/status`                                                    | Report whether teacher login is configured and authenticated         |
| POST   | `/auth/login`                                                     | Log in with a teacher username and password                          |
| POST   | `/auth/logout`                                                    | Log out the current teacher                                          |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Teacher-only sign up for an activity                                 |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Teacher-only unregister from an activity                           |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

Activity and registration data is currently stored in memory, which means it
will be reset when the server restarts. Teacher credentials are configured
separately using password hashes and environment secrets.
