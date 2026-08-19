"""
Tests for file download validation (not file I/O).
"""

import os
import pytest


class TestDownloadValidation:
    """Test download validation logic."""

    def test_download_invalid_directory(self, client, app, db_session):
        """Test that download returns error for non-existent directory."""
        from netfshare.netfshare import Client

        with app.app_context():
            client_obj = Client(address="192.168.1.100")
            client_obj.selected_id = "testuser"
            db_session.add(client_obj)
            db_session.commit()

            response = client.get(
                "/download/nonexistent",
                environ_overrides={"REMOTE_ADDR": "192.168.1.100"},
            )

            # Should redirect with warning
            assert response.status_code == 302

    def test_download_wrong_mode(self, client, app, db_session):
        """Test that download returns error for directory not in read_only mode."""
        from netfshare.netfshare import Client, Directory

        with app.app_context():
            # Setup directory in upload mode (not read mode)
            directory = Directory(path="uploadmode")
            directory.mode = 2  # Upload only, not read
            db_session.add(directory)

            client_obj = Client(address="192.168.1.100")
            client_obj.selected_id = "testuser"
            db_session.add(client_obj)
            db_session.commit()

            response = client.get(
                "/download/uploadmode",
                environ_overrides={"REMOTE_ADDR": "192.168.1.100"},
            )

            # Should redirect because directory not in available_dirs(1)
            assert response.status_code == 302
