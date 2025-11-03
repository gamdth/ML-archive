# Tên file: app/optimize/__init__.py

from flask import Blueprint

bp = Blueprint('optimize', __name__)

from . import routes