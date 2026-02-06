"""
Tests for ping handling in manage_session.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


class TestPingHandling:
    """Test the ping functionality in manage_session view."""

    def test_ping_success_updates_timestamp(self, client, app, db_session):
        """Test that successful ping updates last_seen."""
        from netfshare.netfshare import Client, Directory, db

        with app.app_context():
            # Create test client with old timestamp
            client_obj = Client(address="192.168.1.100")
            old_time = datetime.now() - timedelta(minutes=5)
            client_obj.last_seen = old_time
            client_obj.socket_connected = False
            db_session.add(client_obj)
            db_session.commit()

            # Mock successful ping
            mock_response = MagicMock()
            mock_response.success.return_value = True

            with patch("netfshare.netfshare.ping", return_value=mock_response):
                with patch("flask.request.remote_addr", "127.0.0.1"):
                    response = client.get("/manage_session")

                    # Refresh client from DB
                    db_session.refresh(client_obj)

                    # Should have updated timestamp
                    assert client_obj.last_seen > old_time

    def test_ping_permission_error_caught(self, client, app, db_session):
        """Test that PermissionError is caught gracefully."""
        from netfshare.netfshare import Client, db

        with app.app_context():
            # Create test client
            client_obj = Client(address="192.168.1.100")
            old_time = datetime.now() - timedelta(minutes=5)
            client_obj.last_seen = old_time
            client_obj.socket_connected = False
            db_session.add(client_obj)
            db_session.commit()

            # Mock ping raising PermissionError
            with patch(
                "netfshare.netfshare.ping",
                side_effect=PermissionError("Operation not permitted"),
            ):
                with patch("flask.request.remote_addr", "127.0.0.1"):
                    # Should not raise exception
                    response = client.get("/manage_session")
                    assert response.status_code == 200

                    # Refresh client from DB
                    db_session.refresh(client_obj)

                    # Timestamp should NOT be updated (ping failed and socket not connected)
                    # Allow small time difference due to test execution
                    time_diff = abs((client_obj.last_seen - old_time).total_seconds())
                    assert time_diff < 1  # Should be essentially unchanged

    def test_socket_connected_fallback(self, client, app, db_session):
        """Test that socket_connected works as fallback when ping fails."""
        from netfshare.netfshare import Client, db

        with app.app_context():
            # Create test client with socket connected but old timestamp
            client_obj = Client(address="192.168.1.100")
            old_time = datetime.now() - timedelta(minutes=5)
            client_obj.last_seen = old_time
            client_obj.socket_connected = True  # Socket is connected
            db_session.add(client_obj)
            db_session.commit()

            # Mock ping raising PermissionError
            with patch(
                "netfshare.netfshare.ping",
                side_effect=PermissionError("Operation not permitted"),
            ):
                with patch("flask.request.remote_addr", "127.0.0.1"):
                    response = client.get("/manage_session")

                    # Refresh client from DB
                    db_session.refresh(client_obj)

                    # Timestamp should be updated because socket_connected is True
                    assert client_obj.last_seen > old_time

    def test_both_fail_marks_inactive(self, client, app, db_session):
        """Test that client is marked inactive when both ping and socket fail."""
        from netfshare.netfshare import Client

        with app.app_context():
            # Create test client with old timestamp and socket disconnected
            client_obj = Client(address="192.168.1.100")
            old_time = datetime.now() - timedelta(minutes=5)
            client_obj.last_seen = old_time
            client_obj.socket_connected = False
            db_session.add(client_obj)
            db_session.commit()

            # Mock failed ping (not PermissionError, just failed ping)
            mock_response = MagicMock()
            mock_response.success.return_value = False

            with patch("netfshare.netfshare.ping", return_value=mock_response):
                with patch("flask.request.remote_addr", "127.0.0.1"):
                    response = client.get("/manage_session")

                    # Check that client is now inactive
                    assert client_obj.active is False

    def test_manage_session_shows_client_list(self, client, app, db_session):
        """Test that manage_session displays the list of clients."""
        from netfshare.netfshare import Client

        with app.app_context():
            # Create test clients
            for i in range(3):
                client_obj = Client(address=f"192.168.1.{100 + i}")
                client_obj.selected_id = f"user{i}"
                db_session.add(client_obj)
            db_session.commit()

            with patch("flask.request.remote_addr", "127.0.0.1"):
                response = client.get("/manage_session")

                assert response.status_code == 200
                # Should contain client IDs
                assert b"user0" in response.data
                assert b"user1" in response.data
                assert b"user2" in response.data

    def test_manage_session_shows_uploads_downloads(self, client, app, db_session):
        """Test that manage_session displays uploads and downloads."""
        from netfshare.netfshare import Client, Directory, Upload, Download

        with app.app_context():
            # Create test data
            client_obj = Client(address="192.168.1.100")
            client_obj.selected_id = "testuser"
            directory = Directory(path="test_dir")
            db_session.add(client_obj)
            db_session.add(directory)
            db_session.commit()

            # Create upload and download records
            upload = Upload(
                client_id=client_obj.id, directory_id=directory.id, files_count=3
            )
            download = Download(client_id=client_obj.id, directory_id=directory.id)
            db_session.add(upload)
            db_session.add(download)
            db_session.commit()

            with patch("flask.request.remote_addr", "127.0.0.1"):
                response = client.get("/manage_session")

                assert response.status_code == 200
                # Should contain upload/download info
                assert b"testuser" in response.data
