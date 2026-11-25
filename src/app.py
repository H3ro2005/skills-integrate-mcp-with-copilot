"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pathlib import Path

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

SESSION_COOKIE = "teacher_session"
SESSION_TTL_SECONDS = 8 * 60 * 60


class LoginCredentials(BaseModel):
    username: str
    password: str


def _get_teacher_settings():
    raw_credentials = os.getenv("TEACHER_CREDENTIALS_JSON")
    session_secret = os.getenv("SESSION_SECRET")

    if not raw_credentials or not session_secret:
        raise HTTPException(
            status_code=503,
            detail="Teacher authentication is not configured",
        )

    try:
        teacher_credentials = json.loads(raw_credentials)
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=503,
            detail="TEACHER_CREDENTIALS_JSON must be a JSON object",
        ) from error

    if (
        not isinstance(teacher_credentials, dict)
        or not teacher_credentials
        or any(
            not isinstance(username, str)
            or not username
            or not isinstance(password, str)
            or not password
            for username, password in teacher_credentials.items()
        )
    ):
        raise HTTPException(
            status_code=503,
            detail="TEACHER_CREDENTIALS_JSON must map usernames to passwords",
        )

    if len(session_secret.encode("utf-8")) < 32:
        raise HTTPException(
            status_code=503,
            detail="SESSION_SECRET must contain at least 32 bytes",
        )

    return teacher_credentials, session_secret


def create_teacher_session(username: str, session_secret: str, now: Optional[int] = None) -> str:
    issued_at = int(time.time()) if now is None else now
    payload = json.dumps(
        {"username": username, "expires_at": issued_at + SESSION_TTL_SECONDS},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    signature = hmac.new(
        session_secret.encode("utf-8"),
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return f"{encoded_payload}.{signature}"


def verify_teacher_session(
    token: str,
    expected_username: str,
    session_secret: str,
    now: Optional[int] = None,
) -> bool:
    try:
        encoded_payload, signature = token.rsplit(".", 1)
        expected_signature = hmac.new(
            session_secret.encode("utf-8"),
            encoded_payload.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_signature):
            return False

        payload_bytes = base64.urlsafe_b64decode(
            encoded_payload + "=" * (-len(encoded_payload) % 4)
        )
        payload = json.loads(payload_bytes)
        if not isinstance(payload, dict):
            return False
        current_time = int(time.time()) if now is None else now
        return (
            payload.get("username") == expected_username
            and isinstance(payload.get("expires_at"), int)
            and payload["expires_at"] > current_time
        )
    except (ValueError, TypeError, json.JSONDecodeError):
        return False


def require_teacher(request: Request) -> str:
    teacher_credentials, session_secret = _get_teacher_settings()
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        for username in teacher_credentials:
            if verify_teacher_session(token, username, session_secret):
                return username
    raise HTTPException(status_code=401, detail="Teacher login required")


# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

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


@app.post("/auth/login")
def login(credentials: LoginCredentials, response: Response):
    teacher_credentials, session_secret = _get_teacher_settings()
    password = teacher_credentials.get(credentials.username)
    if not (
        password
        and hmac.compare_digest(
            credentials.password.encode("utf-8"),
            password.encode("utf-8"),
        )
    ):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    response.set_cookie(
        key=SESSION_COOKIE,
        value=create_teacher_session(credentials.username, session_secret),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "false").strip().lower() == "true",
        samesite="strict",
        path="/",
    )
    return {"message": "Logged in"}


@app.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(
        key=SESSION_COOKIE,
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "false").strip().lower() == "true",
        samesite="strict",
        path="/",
    )
    return {"message": "Logged out"}


@app.get("/auth/status")
def auth_status(request: Request):
    teacher_credentials, session_secret = _get_teacher_settings()
    token = request.cookies.get(SESSION_COOKIE)
    authenticated = bool(
        token
        and any(
            verify_teacher_session(token, username, session_secret)
            for username in teacher_credentials
        )
    )
    return {"authenticated": authenticated}


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str,
    email: str,
    _teacher: str = Depends(require_teacher),
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
    _teacher: str = Depends(require_teacher),
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
