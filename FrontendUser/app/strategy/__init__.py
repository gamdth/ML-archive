# Tên file: app/strategy/__init__.py

from flask import Blueprint

bp = Blueprint('strategy', __name__)

from . import routes