import os
from datetime import timedelta


class Config:
    SECRET_KEY = "your_random_secret_key"
    DATABASE_URL = os.path.abspath("database.db")
    DEBUG = True
    UPLOAD_FOLDER = os.path.join(os.getcwd(), "static", "static_upload")
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
