from .base import *

DEBUG = False

# Replace it with your name:
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Database for the development server
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        # put the DB in project-root/data/db.sqlite3
        'NAME': BASE_DIR / 'data' / 'db.sqlite3',
    }
}
