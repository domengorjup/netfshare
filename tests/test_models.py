"""
Tests for database models.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch


class TestClientModel:
    """Test the Client model behavior."""

    def test_client_active_recent(self, app, db_session):
        """Test that client is active if last_seen < 15 seconds ago."""
        from netfshare.netfshare import Client

        with app.app_context():
            client = Client(address="192.168.1.1")
            client.last_seen = datetime.now() - timedelta(seconds=10)
            db_session.add(client)
            db_session.commit()

            assert client.active is True

    def test_client_active_socket_connected(self, app, db_session):
        """Test that client is active if socket_connected is True."""
        from netfshare.netfshare import Client

        with app.app_context():
            client = Client(address="192.168.1.1")
            client.last_seen = datetime.now() - timedelta(minutes=5)  # Old timestamp
            client.socket_connected = True
            db_session.add(client)
            db_session.commit()

            assert client.active is True

    def test_client_inactive(self, app, db_session):
        """Test that client is inactive when both conditions fail."""
        from netfshare.netfshare import Client

        with app.app_context():
            client = Client(address="192.168.1.1")
            client.last_seen = datetime.now() - timedelta(
                minutes=5
            )  # More than 15 seconds
            client.socket_connected = False
            db_session.add(client)
            db_session.commit()

            assert client.active is False

    def test_client_active_property_updates_last_seen(self, app, db_session):
        """Test that setting active=True updates last_seen."""
        from netfshare.netfshare import Client

        with app.app_context():
            client = Client(address="192.168.1.1")
            old_time = datetime.now() - timedelta(minutes=5)
            client.last_seen = old_time
            db_session.add(client)
            db_session.commit()

            # Set active to True
            client.active = True
            db_session.commit()

            assert client.last_seen > old_time

    def test_client_repr_with_name(self, app, db_session):
        """Test Client string representation with name."""
        from netfshare.netfshare import Client

        with app.app_context():
            client = Client(address="192.168.1.1")
            client.selected_name = "John Doe"
            client.selected_id = "12345"
            db_session.add(client)
            db_session.commit()

            repr_str = repr(client)
            assert "John Doe" in repr_str
            assert "12345" in repr_str
            assert "192.168.1.1" in repr_str

    def test_client_repr_without_name(self, app, db_session):
        """Test Client string representation without name."""
        from netfshare.netfshare import Client

        with app.app_context():
            client = Client(address="192.168.1.1")
            client.selected_id = "12345"
            db_session.add(client)
            db_session.commit()

            repr_str = repr(client)
            assert "12345" in repr_str
            assert "192.168.1.1" in repr_str


class TestDirectoryModel:
    """Test the Directory model behavior."""

    def test_directory_default_mode(self, app, db_session):
        """Test that Directory defaults to mode 0 (Not shared)."""
        from netfshare.netfshare import Directory

        with app.app_context():
            directory = Directory(path="test_dir")
            db_session.add(directory)
            db_session.commit()

            assert directory.mode == 0

    def test_directory_repr(self, app, db_session):
        """Test Directory string representation."""
        from netfshare.netfshare import Directory

        with app.app_context():
            directory = Directory(path="test_dir")
            directory.mode = 1
            db_session.add(directory)
            db_session.commit()

            repr_str = repr(directory)
            assert "test_dir" in repr_str
            assert "1" in repr_str


class TestDownloadModel:
    """Test the Download model."""

    def test_download_creation(self, app, db_session):
        """Test Download record creation."""
        from netfshare.netfshare import Client, Directory, Download

        with app.app_context():
            client = Client(address="192.168.1.1")
            directory = Directory(path="test_dir")
            db_session.add(client)
            db_session.add(directory)
            db_session.commit()

            download = Download(client_id=client.id, directory_id=directory.id)
            db_session.add(download)
            db_session.commit()

            assert download.client_id == client.id
            assert download.directory_id == directory.id
            assert download.download_time is not None


class TestUploadModel:
    """Test the Upload model."""

    def test_upload_creation(self, app, db_session):
        """Test Upload record creation."""
        from netfshare.netfshare import Client, Directory, Upload

        with app.app_context():
            client = Client(address="192.168.1.1")
            directory = Directory(path="test_dir")
            db_session.add(client)
            db_session.add(directory)
            db_session.commit()

            upload = Upload(
                client_id=client.id, directory_id=directory.id, files_count=5
            )
            db_session.add(upload)
            db_session.commit()

            assert upload.client_id == client.id
            assert upload.directory_id == directory.id
            assert upload.files_count == 5
            assert upload.upload_time is not None
