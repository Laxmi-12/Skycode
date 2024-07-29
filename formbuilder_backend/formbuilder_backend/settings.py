"""
using Django 4.2.5.
Project - Skycode - formbuilder_backend
Total Apps - 2 (form_generator & custom_components)
"""

import logging  # Log file creation(added in end of this file)
import os
from pathlib import Path

# BASE_DIR = Path(__file__).resolve().parent.parent  # Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # modified by laxmi praba

SECRET_KEY = 'django-insecure-_zw7k@8s@nj%f+7n@_uobzuqwg1hc9_@*ayid=k&aee-0_ysw3'  # SECURITY WARNING: keep the
# secret key used in production secret!

# live url
BASE_URL = 'http://192.168.0.107:8000'
# BASE_URL = 'http://192.168.1.6:8000'
# BASE_URL = 'http://192.168.1.9:8000'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True  # False

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'form_generator',     # added by mohan
    'custom_components',  # added by mohan
    'rest_framework',     # added by mohan
    'corsheaders',        # added by mohan
    'rest_framework.authtoken',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # added by mohan
]

# CSRF settings
CSRF_COOKIE_NAME = 'csrftoken'
CSRF_COOKIE_HTTPONLY = False  # Set to True if you want the CSRF cookie to be accessible only via HTTP(S) and not JavaScript
CSRF_COOKIE_SECURE = False  # Set to True if you want the CSRF cookie to be sent only over HTTPS


REST_FRAMEWORK = {  # added by mohan
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
        # 'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
}

# Configure session storage
SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # added by laxmi Praba
# Allow insecure transport for local development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS

CORS_ORIGIN_ALLOW_ALL = True   # added by mohan
CORS_ALLOW_CREDENTIALS = True  # added by mohan

ROOT_URLCONF = 'formbuilder_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]
WSGI_APPLICATION = 'formbuilder_backend.wsgi.application'

# Google Drive Authentication starts - added by Praba

GOOGLE_OAUTH2_CLIENT_ID = '1005976585380-n7nqmsb80t67apg2bfjdrr6pak95icee.apps.googleusercontent.com'
GOOGLE_OAUTH2_CLIENT_SECRET = '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'
GOOGLE_OAUTH2_SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Add the path to your service account key file
SERVICE_ACCOUNT_KEY_FILE = os.path.join(BASE_DIR, 'credentials/service_accounts.json')  # credentials from google
# drive and stored in credentials folder

# Redirect URI after authentication
GOOGLE_OAUTH2_REDIRECT_URI = 'http://localhost:8000/api/oauth2callback/'
# Google Drive Authentication ends

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

AUTH_PASSWORD_VALIDATORS = [  # Password validation
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'  # Internationalization
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_USE_TLS = True
EMAIL_PORT = 587
EMAIL_HOST_USER = 'lowcodesky2024@gmail.com'
EMAIL_HOST_PASSWORD = 'xplp bgrf nmzp wikc'

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename':  os.path.join(BASE_DIR, ''),
            'formatter': 'verbose',
        },
    # 'console': {
    #         'class': 'logging.StreamHandler',
    #         'level': 'DEBUG',
    #     },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'custom_components': {  # Replace 'myapp' with your actual app name
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

