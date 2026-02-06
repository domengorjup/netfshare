"""
Tests for file download validation (not file I/O).
"""

import os
import pytest
from unittest.mock import patch


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

            with patch("flask.request.remote_addr", "192.168.1.100"):
                response = client.get("/download/nonexistent")

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

            with patch("flask.request.remote_addr", "192.168.1.100"):
                response = client.get("/download/uploadmode")

                # Should redirect because directory not in available_dirs(1)
                assert response.status_code == 302
