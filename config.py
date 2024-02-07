# App settings
DEBUG = True
SECRET_KEY = 'secretdomenkey'
WTF_CSRF_ENABLED = True

# Database
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Served file refresh time
REFRESH_TIME = 120

# Logging depths
LOG_DEPTH = {
    True: 10,
    False: 20
}
