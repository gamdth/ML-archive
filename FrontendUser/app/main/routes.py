# Tên file: app/main/routes.py (KHÔI PHỤC VỀ TRANG GỐC CHUYỂN HƯỚNG ĐẾN LOGIN)

from flask import redirect, url_for
from flask_login import current_user  # Chỉ cần current_user để kiểm tra
from . import bp


@bp.route('/')
def index():
    """
    Xử lý đường dẫn gốc. Luôn chuyển hướng người dùng chưa đăng nhập về login.
    """
    if current_user.is_authenticated:
        # Nếu đã đăng nhập, chuyển hướng đến trang Phân loại khách hàng (trang làm việc mặc định)
        return redirect(url_for('analysis.classify'))

    # Nếu chưa đăng nhập, chuyển hướng đến trang Login
    return redirect(url_for('auth.login'))