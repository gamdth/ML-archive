# Tên file: app/auth/routes.py

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user, login_required
from . import bp
# Thêm thư viện để xử lý và kiểm tra tính an toàn của URL chuyển hướng
from urllib.parse import urlparse, urljoin


# --- MOCK DATA và USER LOADER (giữ nguyên hoặc thay thế bằng code thực tế của bạn) ---
class User:
    def __init__(self, id):
        self.id = id

    def is_active(self):
        return True

    def is_authenticated(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)


MOCK_USERS = {
    'admin@gmail.com': User('admin@gmail.com')
}


def authenticate_user(email, password):
    # Đây là nơi bạn kiểm tra CSDL thực tế.
    # Hiện tại đang dùng MOCK để mô phỏng.
    if email == 'admin@gmail.com' and password == '123':
        return 'admin@gmail.com'
    return None


# -------------------------------------------------------------------------------------

# Hàm tiện ích để xác nhận URL chuyển hướng là an toàn
def is_safe_url(target):
    # Phân tích URL mà người dùng muốn chuyển hướng đến
    target_url = urlparse(urljoin(request.host_url, target))
    # Phân tích URL của máy chủ hiện tại
    ref_url = urlparse(request.host_url)

    # Kiểm tra:
    # 1. Target phải có schema http/https
    # 2. Domain (netloc) của target phải giống domain của máy chủ hiện tại
    return target_url.scheme in ('http', 'https') and \
        ref_url.netloc == target_url.netloc


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('analysis.classify'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember_me = request.form.get('remember_me') is not None

        # 💥 SỬA LỖI: Chỉ gọi hàm xác thực MỘT LẦN 💥
        user_id = authenticate_user(email, password)  # <-- Giữ lại dòng này

        if user_id:
            user = MOCK_USERS.get(user_id) or User(user_id)
            login_user(user, remember=remember_me)

            # Xử lý chuyển hướng 'next'
            next_page = request.args.get('next')
            if next_page and is_safe_url(next_page):
                return redirect(next_page)

            # Chuyển hướng mặc định sau khi thành công
            return redirect(url_for('analysis.classify'))

        else:
            flash('Email hoặc mật khẩu không chính xác.', 'danger')

    return render_template('login.html', active_page='login')


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Bạn đã đăng xuất thành công.', 'info')
    return redirect(url_for('auth.login'))