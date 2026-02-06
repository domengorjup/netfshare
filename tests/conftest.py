"""
Pytest configuration and fixtures for netfshare tests.
"""

import os
import sys
import tempfile
import shutil
import importlib
from datetime import datetime, timedelta

import pytest

# Add parent directory to path to import netfshare
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def app():
    """Create and configure a test Flask application with in-memory database."""
    # Store original cwd
    original_cwd = os.getcwd()

    # Create temp directory
    temp_dir = tempfile.mkdtemp()

    # Change to temp directory so netfshare uses it as SHARED_DIRECTORY
    os.chdir(temp_dir)

    # Remove netfshare modules from cache to force reimport with new cwd
    modules_to_remove = [
        mod for mod in sys.modules.keys() if mod.startswith("netfshare")
    ]
    for mod in modules_to_remove:
        del sys.modules[mod]

    # Import after changing directory
    from netfshare.netfshare import (
        app as flask_app,
        db,
        ConfigBool,
        Message,
        add_shared_folders,
    )

    # Configure app for testing
    flask_app.config["TESTING"] = True
    flask_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    flask_app.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF for testing
    flask_app.config["SECRET_KEY"] = "test-secret-key"

    # Create test client
    with flask_app.app_context():
        db.create_all()

        # Initialize default settings (same as main app)
        if not ConfigBool.query.filter(
            ConfigBool.name == "allow_multiple_uploads"
        ).first():
            db.session.add(
                ConfigBool(
                    name="allow_multiple_uploads",
                    value=flask_app.config.get("ALLOW_MULTIPLE_UPLOADS", False),
                    description="Allow multiple user uploads to the same directory. Replaces existing files.",
                )
            )

        if not ConfigBool.query.filter(ConfigBool.name == "require_name_id").first():
            db.session.add(
                ConfigBool(
                    name="require_name_id",
                    value=flask_app.config.get("REQUIRE_NAME_ID", True),
                    description="Require clients to id by providing their name along with their ID.",
                )
            )

        if not Message.query.filter(Message.name == "default_message").first():
            db.session.add(
                Message(
                    name="default_message",
                    message="",
                    description="Default message, visible to all users.",
                    category="info",
                )
            )

        db.session.commit()

        yield flask_app
        db.session.remove()
        db.drop_all()

    # Restore original cwd
    os.chdir(original_cwd)

    # Clean up temp directory
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a test CLI runner for the app."""
    return app.test_cli_runner()


@pytest.fixture
def db_session(app):
    """Provide a database session for tests."""
    from netfshare.netfshare import db

    with app.app_context():
        yield db.session


@pytest.fixture
def temp_shared_dir():
    """Create a temporary directory for file operations."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_request_remote_addr():
    """Fixture to mock request.remote_addr for admin tests."""
    import unittest.mock

    def _mock(addr):
        return unittest.mock.patch("flask.request.remote_addr", addr)

    return _mock
