# Tên file: app/data/__init__.py

from flask import Blueprint

bp = Blueprint('data', __name__)

from . import routes