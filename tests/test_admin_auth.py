import hashlib
import os
import unittest

from fastapi.testclient import TestClient

os.environ["SESSION_SECRET_KEY"] = "test-session-secret-with-at-least-32-bytes"
os.environ["SESSION_COOKIE_SECURE"] = "false"

from src import app as app_module
from src.auth import PBKDF2_ITERATIONS


def make_password_hash(password: str) -> str:
    salt = bytes.fromhex("0123456789abcdef0123456789abcdef")
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


class TeacherAuthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_activities = {
            name: {**activity, "participants": list(activity["participants"])}
            for name, activity in app_module.activities.items()
        }
        self.original_credentials = app_module.teacher_password_hashes
        app_module.teacher_password_hashes = {
            "teacher": make_password_hash("a sufficiently long test password")
        }
        self.client = TestClient(app_module.app, base_url="http://testserver")

    def tearDown(self) -> None:
        self.client.close()
        app_module.activities.clear()
        app_module.activities.update(self.original_activities)
        app_module.teacher_password_hashes = self.original_credentials

    def test_students_can_view_activities_and_participants(self) -> None:
        response = self.client.get("/activities")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Chess Club", response.json())
        self.assertIn("michael@mergington.edu", response.json()["Chess Club"]["participants"])

    def test_signup_and_unregister_require_teacher_login(self) -> None:
        signup = self.client.post(
            "/activities/Chess Club/signup",
            params={"email": "new.student@mergington.edu"},
        )
        unregister = self.client.delete(
            "/activities/Chess Club/unregister",
            params={"email": "michael@mergington.edu"},
        )

        self.assertEqual(signup.status_code, 401)
        self.assertEqual(unregister.status_code, 401)

    def test_teacher_can_login_manage_participants_and_logout(self) -> None:
        login = self.client.post(
            "/auth/login",
            json={"username": "teacher", "password": "a sufficiently long test password"},
        )
        self.assertEqual(login.status_code, 200)
        self.assertTrue(self.client.get("/auth/status").json()["authenticated"])

        signup = self.client.post(
            "/activities/Chess Club/signup",
            params={"email": "new.student@mergington.edu"},
        )
        self.assertEqual(signup.status_code, 200)

        unregister = self.client.delete(
            "/activities/Chess Club/unregister",
            params={"email": "new.student@mergington.edu"},
        )
        self.assertEqual(unregister.status_code, 200)

        logout = self.client.post("/auth/logout")
        self.assertEqual(logout.status_code, 200)
        self.assertFalse(self.client.get("/auth/status").json()["authenticated"])
        denied = self.client.post(
            "/activities/Chess Club/signup",
            params={"email": "new.student@mergington.edu"},
        )
        self.assertEqual(denied.status_code, 401)

    def test_invalid_credentials_do_not_create_a_session(self) -> None:
        response = self.client.post(
            "/auth/login",
            json={"username": "teacher", "password": "incorrect password"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertFalse(self.client.get("/auth/status").json()["authenticated"])

    def test_management_is_disabled_when_credentials_are_unconfigured(self) -> None:
        app_module.teacher_password_hashes = {}

        login = self.client.post(
            "/auth/login",
            json={"username": "teacher", "password": "any password"},
        )
        signup = self.client.post(
            "/activities/Chess Club/signup",
            params={"email": "new.student@mergington.edu"},
        )

        self.assertEqual(login.status_code, 503)
        self.assertEqual(signup.status_code, 503)


if __name__ == "__main__":
    unittest.main()
