"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import os
import secrets
import warnings
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware import Middleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from src.auth import load_teacher_password_hashes, verify_teacher_password


def _session_secret() -> str:
    secret = os.environ.get("SESSION_SECRET_KEY")
    if secret:
        if len(secret.encode("utf-8")) < 32:
            raise RuntimeError("SESSION_SECRET_KEY must contain at least 32 bytes")
        return secret

    warnings.warn(
        "SESSION_SECRET_KEY is not set; teacher sessions will be invalidated on restart. "
        "Set a persistent random secret before deployment.",
        stacklevel=2,
    )
    return secrets.token_urlsafe(32)


def _cookie_is_secure() -> bool:
    value = os.environ.get("SESSION_COOKIE_SECURE", "true").lower()
    if value not in {"true", "false"}:
        raise RuntimeError("SESSION_COOKIE_SECURE must be 'true' or 'false'")
    return value == "true"


teacher_password_hashes = load_teacher_password_hashes()

app = FastAPI(
    title="Mergington High School API",
    description="API for viewing and signing up for extracurricular activities",
    middleware=[
        Middleware(
            SessionMiddleware,
            secret_key=_session_secret(),
            session_cookie="teacher_session",
            max_age=8 * 60 * 60,
            same_site="strict",
            https_only=_cookie_is_secure(),
        )
    ],
)

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")


class LoginRequest(BaseModel):
    username: str
    password: str


def require_teacher(request: Request) -> str:
    if not teacher_password_hashes:
        raise HTTPException(
            status_code=503,
            detail="Teacher authentication is not configured",
        )

    username = request.session.get("teacher")
    if not isinstance(username, str) or username not in teacher_password_hashes:
        raise HTTPException(status_code=401, detail="Teacher login required")
    return username


# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.get("/auth/status")
def get_auth_status(request: Request):
    username = request.session.get("teacher")
    authenticated = isinstance(username, str) and username in teacher_password_hashes
    return {
        "configured": bool(teacher_password_hashes),
        "authenticated": authenticated,
        "username": username if authenticated else None,
    }


@app.post("/auth/login")
def login(credentials: LoginRequest, request: Request):
    if not teacher_password_hashes:
        raise HTTPException(
            status_code=503,
            detail="Teacher authentication is not configured",
        )

    if not verify_teacher_password(
        credentials.username,
        credentials.password,
        teacher_password_hashes,
    ):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    request.session.clear()
    request.session["teacher"] = credentials.username
    return {"message": "Logged in as teacher"}


@app.post("/auth/logout")
def logout(request: Request, _: str = Depends(require_teacher)):
    request.session.clear()
    return {"message": "Logged out"}


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str,
    email: str,
    _: str = Depends(require_teacher),
):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str,
    email: str,
    _: str = Depends(require_teacher),
):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
