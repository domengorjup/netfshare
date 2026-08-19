"""
Tests for file upload validation (not file I/O).
"""

import os
import io


class TestUploadValidation:
    """Test upload validation logic (not file I/O)."""

    def test_upload_exceeds_max_files(self, client, app, db_session, temp_shared_dir):
        """Test that upload is rejected when exceeding MAX_FILES."""
        from netfshare.netfshare import Client, Directory, ConfigBool

        with app.app_context():
            # Setup
            upload_dir = os.path.join(temp_shared_dir, "uploads")
            os.makedirs(upload_dir, exist_ok=True)

            directory = Directory(path="uploads")
            directory.mode = 2
            db_session.add(directory)

            config = ConfigBool.query.filter_by(name="require_name_id").first()
            if config:
                config.value = False
            db_session.commit()

            client_obj = Client(address="192.168.1.100")
            client_obj.selected_id = "testuser"
            db_session.add(client_obj)
            db_session.commit()

            # Create more files than MAX_FILES (default 10)
            data = {
                "file": [(io.BytesIO(b"content"), f"file{i}.txt") for i in range(15)]
            }

            response = client.post(
                "/upload/uploads",
                data=data,
                content_type="multipart/form-data",
                environ_overrides={"REMOTE_ADDR": "192.168.1.100"},
            )

            # Should redirect with error message
            assert response.status_code == 302
            # Check that flash message would be shown (Too many files)

    def test_upload_duplicate_id_blocked(
        self, client, app, db_session, temp_shared_dir
    ):
        """Test that duplicate ID is blocked when allow_multiple_uploads is False."""
        from netfshare.netfshare import Client, Directory, ConfigBool

        with app.app_context():
            # Setup
            upload_dir = os.path.join(temp_shared_dir, "uploads")
            os.makedirs(upload_dir, exist_ok=True)
            os.makedirs(
                os.path.join(upload_dir, "testuser"), exist_ok=True
            )  # Simulate existing upload

            directory = Directory(path="uploads")
            directory.mode = 2
            db_session.add(directory)

            # Disable multiple uploads
            config_multiple = ConfigBool.query.filter_by(
                name="allow_multiple_uploads"
            ).first()
            if config_multiple:
                config_multiple.value = False
            else:
                config_multiple = ConfigBool(name="allow_multiple_uploads", value=False)
                db_session.add(config_multiple)

            config_name = ConfigBool.query.filter_by(name="require_name_id").first()
            if config_name:
                config_name.value = False
            db_session.commit()

            client_obj = Client(address="192.168.1.100")
            client_obj.selected_id = "testuser"
            db_session.add(client_obj)
            db_session.commit()

            # Try to upload again
            data = {"file": (io.BytesIO(b"new content"), "new_file.txt")}

            response = client.post(
                "/upload/uploads",
                data=data,
                content_type="multipart/form-data",
                environ_overrides={"REMOTE_ADDR": "192.168.1.100"},
            )

            # Should redirect with warning
            assert response.status_code == 302
