# Tên file: app/strategy/routes.py

import io
import csv
from flask import render_template, request, redirect, url_for, Response
from . import bp
# --- Dữ liệu giả lập (Sau này bạn sẽ thay bằng database) ---

MOCK_CAMPAIGN_DETAILS = {
    'chien_dich_a': {
        'id': 'chien_dich_a',
        'name': 'Chiến dịch A - Gửi Email',
        'description': 'Nội dung: Gửi email marketing cho nhóm khách hàng tiềm năng A về sản phẩm thẻ tín dụng mới. Ưu đãi giảm 5% phí thường niên.'
    },
    'chien_dich_b': {
        'id': 'chien_dich_b',
        'name': 'Chiến dịch B - Gọi điện',
        'description': 'Nội dung: Telesales gọi điện cho nhóm khách hàng B, những người có điểm tín dụng cao, để mời nâng hạng thẻ.'
    },
    'chien_dich_c': {
        'id': 'chien_dich_c',
        'name': 'Chiến dịch C - Gửi SMS',
        'description': 'Nội dung: Gửi tin nhắn SMS cho nhóm khách hàng C (đã lâu không hoạt động) về chương trình hoàn tiền mới.'
    }
}

MOCK_CUSTOMER_LISTS = {
    'chien_dich_a': [
        {'ho_lot': 'Trần Thị', 'ten': 'Bích', 'ngay_sinh': '10/05/1990', 'nu': True, 'the_tin_dung': '9876...',
         'diem_tin_dung': 650, 'trang_thai_the': 'Hoạt động', 'ghi_chu': 'Nhóm A'},
        {'ho_lot': 'Lê Văn', 'ten': 'Minh', 'ngay_sinh': '22/11/1985', 'nu': False, 'the_tin_dung': '1234...',
         'diem_tin_dung': 680, 'trang_thai_the': 'Hoạt động', 'ghi_chu': 'Nhóm A'}
    ],
    'chien_dich_b': [
        {'ho_lot': 'Nguyễn Văn', 'ten': 'A', 'ngay_sinh': '23/07/2005', 'nu': False, 'the_tin_dung': '1234...',
         'diem_tin_dung': 500, 'trang_thai_the': 'Sử dụng', 'ghi_chu': 'Nhóm B (Dữ liệu gốc)'},
        {'ho_lot': 'Phạm Thị', 'ten': 'Hà', 'ngay_sinh': '01/01/1980', 'nu': True, 'the_tin_dung': '5555...',
         'diem_tin_dung': 800, 'trang_thai_the': 'VIP', 'ghi_chu': 'Nhóm B'}
    ],
    'chien_dich_c': [
        {'ho_lot': 'Hoàng Văn', 'ten': 'Dũng', 'ngay_sinh': '15/03/1995', 'nu': False, 'the_tin_dung': '4567...',
         'diem_tin_dung': 550, 'trang_thai_the': 'Tạm khóa', 'ghi_chu': 'Nhóm C'}
    ]
}


# --- Kết thúc dữ liệu giả lập ---


@bp.route('/goiyutudong', methods=['GET', 'POST'])
def view_strategy():
    # ... (Giữ nguyên logic campaign_details, customers của bạn) ...
    campaign_details = None
    customers = None
    if request.method == 'POST':
        selected_id = request.form.get('campaign_id')
        if selected_id:
            campaign_details = MOCK_CAMPAIGN_DETAILS.get(selected_id)
            customers = MOCK_CUSTOMER_LISTS.get(selected_id)

    # Thêm 'active_page' vào cuối
    return render_template('goiytudong.html',
                           campaign_details=campaign_details,
                           customers=customers,
                           active_page='strategy')


@bp.route('/download/<campaign_id>')
def download_list(campaign_id):
    """
    Xử lý khi nhấn nút "Tải về"
    """
    # 1. Lấy dữ liệu (giống như khi nhấn "Xem")
    customers = MOCK_CUSTOMER_LISTS.get(campaign_id)

    if not customers:
        # Nếu không tìm thấy, quay về trang chính
        return redirect(url_for('strategy.view_strategy'))

    # 2. Tạo file CSV trong bộ nhớ
    output = io.StringIO()  # Tạo một file "ảo" trong RAM
    writer = csv.writer(output)

    # Ghi header
    headers = ['STT', 'Ho & Ten lot', 'Ten', 'Ngay sinh', 'Nu',
               'The tin dung', 'Diem tin dung', 'Trang thai the', 'Ghi chu']
    writer.writerow(headers)

    # Ghi dữ liệu khách hàng
    for i, customer in enumerate(customers):
        writer.writerow([
            i + 1,
            customer['ho_lot'],
            customer['ten'],
            customer['ngay_sinh'],
            'x' if customer['nu'] else '',
            customer['the_tin_dung'],
            customer['diem_tin_dung'],
            customer['trang_thai_the'],
            customer['ghi_chu']
        ])

    output.seek(0)  # Đưa con trỏ về đầu file "ảo"

    # 3. Trả file về cho người dùng
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=danh_sach_khach_hang_{campaign_id}.csv"}
    )