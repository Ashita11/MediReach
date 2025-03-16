import os
from MediReach.settings import *

SECRET_KEY = 'django-insecure-)zw1skt5v0-*4v4iurlrsz3+54^zn=(cl0j5x(3#+birr-23e0'
DEBUG = True

DATABASES['default']['NAME'] = "MediReach"
DATABASES['default']['USER'] = "root"
DATABASES['default']['PASSWORD'] = "Ashita123"



# SECRET_KEY = 'django-insecure-)zw1skt5v0-*4v4iurlrsz3+54^zn=(cl0j5x(3#+birr-23e0'

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': 'MediReach',
#         'USER': 'root',
#         'PASSWORD': '',
#         'HOST': 'localhost',
#         'PORT': '3306',
#     }
# }