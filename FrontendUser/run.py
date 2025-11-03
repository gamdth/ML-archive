# Tên file: run.py
import os
from app import create_app
from config import Config

app = create_app(config_class=Config)

try:
    upload_folder = app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
except KeyError:
    print("Cảnh báo: Không tìm thấy UPLOAD_FOLDER trong config.")

if __name__ == '__main__':
    app.run(debug=True)