"""
Tests for admin authentication functionality.
"""

import pytest
from unittest.mock import patch


class TestCheckAdmin:
    """Test the check_admin function with different IP addresses."""

    def test_check_admin_loopback_ipv4(self, app):
        """Test that 127.0.0.1 is recognized as admin."""
        from netfshare.netfshare import check_admin
        from flask import request

        with app.test_request_context():
            with patch.object(request, "remote_addr", "127.0.0.1"):
                assert check_admin(request) is True

    def test_check_admin_loopback_ipv6(self, app):
        """Test that ::1 is recognized as admin."""
        from netfshare.netfshare import check_admin
        from flask import request

        with app.test_request_context():
            with patch.object(request, "remote_addr", "::1"):
                assert check_admin(request) is True

    def test_check_admin_loopback_all_127(self, app):
        """Test that any 127.x.x.x address is recognized as admin."""
        from netfshare.netfshare import check_admin
        from flask import request

        with app.test_request_context():
            for addr in ["127.0.0.1", "127.0.0.2", "127.1.2.3", "127.255.255.255"]:
                with patch.object(request, "remote_addr", addr):
                    assert check_admin(request) is True, f"Failed for {addr}"

    def test_check_admin_non_loopback(self, app):
        """Test that non-loopback addresses are not admin."""
        from netfshare.netfshare import check_admin
        from flask import request

        with app.test_request_context():
            for addr in ["192.168.1.1", "10.0.0.1", "172.16.0.1", "8.8.8.8"]:
                with patch.object(request, "remote_addr", addr):
                    assert check_admin(request) is False, f"Failed for {addr}"


class TestAdminViewProtection:
    """Test that admin routes work properly (loopback access)."""

    def test_admin_view_allows_loopback(self, client, app):
        """Test that /admin is accessible from loopback."""
        from netfshare.netfshare import Directory, db

        with app.app_context():
            # Create a test directory
            test_dir = Directory(path="test_dir")
            db.session.add(test_dir)
            db.session.commit()

        response = client.get("/admin", environ_overrides={"REMOTE_ADDR": "127.0.0.1"})
        # Should not redirect, should show admin page
        assert response.status_code == 200

    def test_manage_session_allows_loopback(self, client):
        """Test that /manage_session is accessible from loopback."""
        response = client.get(
            "/manage_session", environ_overrides={"REMOTE_ADDR": "127.0.0.1"}
        )
        assert response.status_code == 200

    def test_reset_session_allows_loopback(self, client):
        """Test that /reset_session is accessible from loopback."""
        response = client.get(
            "/reset_session", environ_overrides={"REMOTE_ADDR": "127.0.0.1"}
        )
        # Should redirect after successful reset
        assert response.status_code == 302
