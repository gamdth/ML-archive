# Tên file: app/__init__.py
import os
from flask import Flask
from flask_login import LoginManager, UserMixin

# 1. KHỞI TẠO FLASK-LOGIN
login_manager = LoginManager()
login_manager.login_view = 'auth.login'  # Chỉ định endpoint đăng nhập
login_manager.login_message = 'Vui lòng đăng nhập để truy cập trang này.'
login_manager.login_message_category = 'info'


# 2. USER CLASS ĐƠN GIẢN
# Flask-Login yêu cầu user object phải kế thừa UserMixin
class User(UserMixin):
    def __init__(self, id):
        self.id = id

    def get_id(self):
        return str(self.id)

    # Có thể thêm các thuộc tính khác như email, password_hash nếu dùng DB


# 3. MOCK DATABASE (Sử dụng admin như đã thỏa thuận)
MOCK_USERS = {
    # 💥 SỬA ID: Phải là email để khớp với hàm authenticate_user 💥
    'admin@gmail.com': User('admin@gmail.com')
}
def create_app(config_class):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.secret_key = app.config['SECRET_KEY']

    # 4. KHỞI TẠO EXTENSION
    login_manager.init_app(app)  # Khởi tạo Flask-Login

    # 5. USER LOADER
    # Hàm này được gọi để tải User object từ user ID được lưu trong session/cookie
    @login_manager.user_loader
    def load_user(user_id):
        # Trong ví dụ này, user_id là 'admin'
        return MOCK_USERS.get(user_id)

    # --- Đăng ký Blueprints (Giữ nguyên) ---

    from .main import bp as main_bp
    app.register_blueprint(main_bp)

    from .data import bp as data_bp
    app.register_blueprint(data_bp)

    from .strategy import bp as strategy_bp
    app.register_blueprint(strategy_bp)

    from .auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from .analysis import bp as analysis_bp
    app.register_blueprint(analysis_bp)

    from .stats import bp as stats_bp
    app.register_blueprint(stats_bp)

    from .optimize import bp as optimize_bp
    app.register_blueprint(optimize_bp)

    return app