# App settings
DEBUG = True
SECRET_KEY = 'secretkkkey'
WTF_CSRF_ENABLED = True

# Database
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Served file refresh time
REFRESH_TIME = 120

SHARE_MODES = {
    0: 'Not shared',
    1: 'Read only',
    2: 'Upload_only'
}

EXCLUDE_DIRNAMES = ['.git', '.netfshare', '__pycache__', 'venv']

# Maximum number of files to upload at once
MAX_FILES = 10

# Localization
LANGUAGES = ['en', 'sl']
