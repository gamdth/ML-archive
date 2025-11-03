# Tên file: config.py

import os

class Config:
    # Cài đặt Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'fund'

    DATABASE_CONFIG = {
        "server": os.environ.get('DB_SERVER') or "localhost",
        "port": 3306,
        "database": os.environ.get('DB_NAME') or "bank",
        "username": os.environ.get('DB_USER') or "root",
        "password": os.environ.get('DB_PASSWORD') or "@Obama123"
    }

    ADMIN_USER = "admin@gmail.com"
    ADMIN_PASS = "123"