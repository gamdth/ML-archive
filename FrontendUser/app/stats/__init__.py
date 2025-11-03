# Tên file: app/stats/__init__.py

from flask import Blueprint

bp = Blueprint('stats', __name__)

from . import routes