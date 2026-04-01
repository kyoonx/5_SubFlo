from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.loca.lt']

# Database for the development server
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        # put the DB in project-root/data/db.sqlite3
        'NAME': BASE_DIR / 'data' / 'db.sqlite3',
    }
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '[{levelname}] {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'subscriptions': {          # catches all loggers in the subscriptions app
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
