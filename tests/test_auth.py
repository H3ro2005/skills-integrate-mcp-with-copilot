import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException, Request, Response

from src.app import (
    LoginCredentials,
    SESSION_COOKIE,
    app,
    create_teacher_session,
    login,
    require_teacher,
    verify_teacher_session,
)


class TeacherAuthTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(
            os.environ,
            {
                "TEACHER_CREDENTIALS_JSON": (
                    '{"teacher":"correct-password","another-teacher":"other-password"}'
                ),
                "SESSION_SECRET": "test-session-secret-with-sufficient-entropy",
                "COOKIE_SECURE": "false",
            },
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def make_request(self, cookie=None):
        headers = []
        if cookie:
            headers.append((b"cookie", f"{SESSION_COOKIE}={cookie}".encode()))
        return Request(
            {
                "type": "http",
                "http_version": "1.1",
                "method": "GET",
                "scheme": "http",
                "path": "/",
                "query_string": b"",
                "headers": headers,
                "server": ("testserver", 80),
                "client": ("testclient", 50000),
            }
        )

    def test_signed_session_must_be_valid_and_unexpired(self):
        token = create_teacher_session("teacher", os.environ["SESSION_SECRET"], now=100)

        self.assertTrue(
            verify_teacher_session(
                token,
                "teacher",
                os.environ["SESSION_SECRET"],
                now=101,
            )
        )
        self.assertFalse(
            verify_teacher_session(
                token + "tampered",
                "teacher",
                os.environ["SESSION_SECRET"],
                now=101,
            )
        )
        self.assertFalse(
            verify_teacher_session(
                token,
                "teacher",
                os.environ["SESSION_SECRET"],
                now=100 + 8 * 60 * 60,
            )
        )

    def test_teacher_dependency_rejects_missing_session(self):
        with self.assertRaises(HTTPException) as error:
            require_teacher(self.make_request())

        self.assertEqual(error.exception.status_code, 401)

    def test_teacher_dependency_accepts_valid_session(self):
        token = create_teacher_session("teacher", os.environ["SESSION_SECRET"])

        self.assertEqual(require_teacher(self.make_request(token)), "teacher")

    def test_teacher_dependency_accepts_each_configured_teacher(self):
        token = create_teacher_session(
            "another-teacher",
            os.environ["SESSION_SECRET"],
        )

        self.assertEqual(
            require_teacher(self.make_request(token)),
            "another-teacher",
        )

    def test_login_sets_http_only_strict_cookie(self):
        response = Response()

        login(
            LoginCredentials(username="teacher", password="correct-password"),
            response,
        )

        cookie = response.headers["set-cookie"].lower()
        self.assertIn(f"{SESSION_COOKIE}=", cookie)
        self.assertIn("httponly", cookie)
        self.assertIn("samesite=strict", cookie)
        self.assertIn(f"max-age={8 * 60 * 60}", cookie)

    def test_login_rejects_invalid_password(self):
        with self.assertRaises(HTTPException) as error:
            login(
                LoginCredentials(username="teacher", password="incorrect"),
                Response(),
            )

        self.assertEqual(error.exception.status_code, 401)

    def test_signup_and_unregister_routes_require_teacher_dependency(self):
        protected_paths = {
            "/activities/{activity_name}/signup",
            "/activities/{activity_name}/unregister",
        }
        found_paths = set()
        for route in app.routes:
            if getattr(route, "path", None) in protected_paths:
                found_paths.add(route.path)
                dependencies = [dependency.call for dependency in route.dependant.dependencies]
                self.assertIn(require_teacher, dependencies)
        self.assertEqual(found_paths, protected_paths)


if __name__ == "__main__":
    unittest.main()
