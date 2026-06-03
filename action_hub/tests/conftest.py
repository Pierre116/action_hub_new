import os
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

import pytest

from actionhub import create_app
from actionhub.middleware.db import init_db
from seed_data import seed_admin, seed_reference_data

def build_test_app() -> tuple:
    temp_dir = tempfile.mkdtemp(prefix="actionhub_test_")
    db_path = Path(temp_dir) / "test_actionhub.db"

    os.environ["ACTIONHUB_ENV"] = "development"
    os.environ["DATABASE"] = str(db_path)
    app = create_app()
    app.config.update(TESTING=True, DATABASE=str(db_path))
    # Explicitly register workflow blueprint to ensure all workflow routes are present in tests
    try:
        from actionhub.workflow.routes import workflow_bp
        # Only register if not already present
        if 'workflow' not in app.blueprints:
            app.register_blueprint(workflow_bp)
    except Exception as e:
        print(f"[DEBUG] Could not register workflow_bp: {e}")

    with app.app_context():
        init_db()
        seed_reference_data()
        seed_admin()

        # Shared test connection for fixtures that create setup rows directly.
        db_conn = sqlite3.connect(str(db_path))
        db_conn.row_factory = sqlite3.Row
        app.config["db_conn"] = db_conn

    return app, str(db_path)


class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.app, self.temp_dir = build_test_app()
        self.client = self.app.test_client()

    def tearDown(self):
        db_conn = self.app.config.get("db_conn")
        if db_conn is not None:
            db_conn.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def login_admin(self):
        response = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "Admin@2026"},
        )
        self.assertEqual(response.status_code, 200)
        token = response.get_json()["data"]["access_token"]
        self.client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        return response

    def login_user(self):
        # Log in as a non-admin user (assume user 'user1' with password 'User@2026' exists in seed data)
        response = self.client.post(
            "/api/auth/login",
            json={"username": "user1", "password": "User@2026"},
        )
        self.assertEqual(response.status_code, 200)
        token = response.get_json()["data"]["access_token"]
        self.client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        return response

    def get_db(self):
        # Return a DB connection to the current test DB with row_factory
        db_path = self.app.config["DATABASE"]
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def json_dumps(self, obj):
        import json
        return json.dumps(obj)


@pytest.fixture
def logged_in_user():
    """Fixture that logs in as admin and returns the test client."""
    app, temp_dir = build_test_app()
    client = app.test_client()
    # Login as admin
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "Admin@2026"},
    )
    token = response.get_json()["data"]["access_token"]
    client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    yield client
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def db():
    """Provide a database connection for tests."""
    app, db_path = build_test_app()
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    yield connection
    connection.close()
