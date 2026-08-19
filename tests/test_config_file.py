"""
Tests for local config file creation.
"""

import json
import os
import shutil
import sys
import tempfile


class TestLocalConfigFile:
    """Test local config file handling."""

    def test_missing_config_file_is_created_with_defaults(self):
        original_cwd = os.getcwd()
        temp_dir = tempfile.mkdtemp()

        try:
            os.chdir(temp_dir)

            modules_to_remove = [
                mod for mod in sys.modules.keys() if mod.startswith("netfshare")
            ]
            for mod in modules_to_remove:
                del sys.modules[mod]

            from netfshare.netfshare import local_config

            assert os.path.isfile(local_config)

            with open(local_config) as f:
                config_data = json.load(f)

            assert config_data["PORT"] == 5000
            assert config_data["MAX_FILES"] == 10
            assert config_data["LANGUAGES"] == ["en", "sl"]
        finally:
            os.chdir(original_cwd)
            shutil.rmtree(temp_dir, ignore_errors=True)
