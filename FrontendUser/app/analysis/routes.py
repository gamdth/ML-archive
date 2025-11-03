# Tên file: app/analysis/routes.py

from flask import render_template, request
from flask_login import login_required  # Chỉ cần import login_required

from . import bp  # Import tương đối

# --- Dữ liệu giả lập ---
MOCK_ALL_CUSTOMERS = [
    {'stt': 1, 'ho_lot': 'Trần Thị', 'ten': 'Bích', 'ngay_sinh': '10/05/1990', 'nu': True, 'the_tin_dung': '9876...',
     'diem_tin_dung': 650, 'trang_thai_the': 'Hoạt động', 'ghi_chu': 'Nhóm A'},
    {'stt': 2, 'ho_lot': 'Lê Văn', 'ten': 'Minh', 'ngay_sinh': '22/11/1985', 'nu': False, 'the_tin_dung': '1234...',
     'diem_tin_dung': 680, 'trang_thai_the': 'Hoạt động', 'ghi_chu': 'Nhóm A'},
    {'stt': 3, 'ho_lot': 'Nguyễn Văn', 'ten': 'A', 'ngay_sinh': '23/07/2005', 'nu': False, 'the_tin_dung': '1234...',
     'diem_tin_dung': 500, 'trang_thai_the': 'Sử dụng', 'ghi_chu': 'Nhóm B'},
    {'stt': 4, 'ho_lot': 'Phạm Thị', 'ten': 'Hà', 'ngay_sinh': '01/01/1980', 'nu': True, 'the_tin_dung': '5555...',
     'diem_tin_dung': 800, 'trang_thai_the': 'VIP', 'ghi_chu': 'Nhóm B'},
    {'stt': 5, 'ho_lot': 'Hoàng Văn', 'ten': 'Dũng', 'ngay_sinh': '15/03/1995', 'nu': False, 'the_tin_dung': '4567...',
     'diem_tin_dung': 550, 'trang_thai_the': 'Tạm khóa', 'ghi_chu': 'Nhóm C'},
    {'stt': 6, 'ho_lot': 'Đặng Thanh', 'ten': 'Phong', 'ngay_sinh': '30/10/2000', 'nu': False,
     'the_tin_dung': '1122...', 'diem_tin_dung': 720, 'trang_thai_the': 'Hoạt động', 'ghi_chu': 'Mới'},
]


# --- Kết thúc dữ liệu giả lập ---


@bp.route('/phanloai', methods=['GET', 'POST'])
@login_required  # Giữ nguyên cơ chế bảo mật của Flask-Login
def classify():
    """
    Hiển thị trang (GET)
    Xử lý tìm kiếm (POST)
    """

    # 💥 XÓA BỎ KHỐI KIỂM TRA SESSION THỪA THÃI VÀ DƯỚI ĐÂY LÀ LOGIC CHÍNH 💥

    customers_list = MOCK_ALL_CUSTOMERS
    search_term = ""

    if request.method == 'POST':
        # 1. Lấy nội dung tìm kiếm từ form
        search_term = request.form.get('search_query', '').lower()

        if search_term:
            # 2. Lọc danh sách khách hàng
            customers_list = [
                customer for customer in MOCK_ALL_CUSTOMERS
                if search_term in customer['ho_lot'].lower() or \
                   search_term in customer['ten'].lower() or \
                   search_term in customer['the_tin_dung']
            ]

    # 3. Render lại trang với danh sách đã lọc (hoặc đầy đủ)
    return render_template('phanloai.html',
                           customers=customers_list,
                           search_term=search_term,  # Gửi lại từ khóa tìm kiếm để hiển thị
                           active_page='analysis')  # Báo cho sidebar biết trang nào active