"""
Django settings for smarttailor project.

Generated by 'django-admin startproject' using Django 5.1.3.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
import environ
# Initialize environment variables
env = environ.Env(
    DEBUG=(bool, False)
)
# Read the `.env` file
environ.Env.read_env()

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-99!92^)83vf7=(cm5hx&^gs5%i6)77pt0c9+6#$m3pkwk-4111'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True



CSRF_TRUSTED_ORIGINS = [
    "https://smart-tailor-frnt.onrender.com",
    env('SHOPIFY_APP_URL_FRNT')
]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'recommendations', 
    'analytics',
    'shopifyauthenticate',
    'corsheaders',
    
]


ALLOWED_HOSTS = ['smart-tailor.onrender.com', 
                 '127.0.0.1',
                 'localhost', 
                 env('ALLOWED_HOST1'),
                 env('ALLOWED_HOST2')
                 ]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'shopifyauthenticate.middleware.ShopifyAuthMiddleware',
]

MIDDLEWARE.insert(0, 'corsheaders.middleware.CorsMiddleware')

ROOT_URLCONF = 'smarttailor.urls'

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

WSGI_APPLICATION = 'smarttailor.wsgi.application'



# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': env('DB_PORT'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
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


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

import os
STATIC_URL = '/static/'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'recommendations', 'static'),
]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')


# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
# Allow specific origins
CORS_ALLOWED_ORIGINS = [
    "https://smart-tailor-frnt.onrender.com",
    "http://localhost:3000",  # For local development
    env('SHOPIFY_APP_URL'),
    env('SHOPIFY_APP_URL_FRNT')   
]





CORS_ALLOW_METHODS = [
    'GET',
    'POST',
    'PUT',
    'DELETE',
    'OPTIONS',
]

CORS_ALLOW_HEADERS = [
    'content-type',
    'authorization',
    'x-csrftoken',  # Add any other headers you may need
    'ngrok-skip-browser-warning'
]

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# Or allow all origins (not recommended for production)
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True



SHOPIFY_API_KEY=env('SHOPIFY_API_KEY')
SHOPIFY_API_SECRET=env('SHOPIFY_API_SECRET')


USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# SHOPIFY_APP_URL="https://smart-tailor.onrender.com"
SHOPIFY_APP_URL=env('SHOPIFY_APP_URL')
SHOPIFY_APP_URL_FRNT=env('SHOPIFY_APP_URL_FRNT')




# Celery Configuration
CELERY_BROKER_URL = env('CELERY_BROKER_URL') # URL for Redis broker
CELERY_ACCEPT_CONTENT = ['json']  # Task serialization format
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_BACKEND = env('CELERY_BROKER_URL')  # Optional: for storing task results
CELERY_TIMEZONE = 'UTC'