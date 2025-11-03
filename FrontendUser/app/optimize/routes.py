# optimize/routes.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from .ml_logic import train_and_save_new_run
from ..DatabaseConnector import DATABASE_CONFIG

# Tạo Blueprint cho module optimize
optimize_bp = Blueprint('optimize', __name__, url_prefix='/optimize')

# --- Giả định: Các config và Connector đã được setup ở nơi khác ---
# Để đơn giản, ta sẽ dùng lại config đã định nghĩa

# Giả định: Bạn đã có một nơi để lưu trữ cấu hình CSDL
# Ví dụ: app.config['DATABASE_CONFIG']
# Ta sẽ dùng lại định nghĩa từ script trước:


# (Bạn cần điều chỉnh import này để phù hợp với cấu trúc ứng dụng Flask thực tế của bạn)


@optimize_bp.route('/retrain', methods=['GET', 'POST'])
# Route này xử lý việc kích hoạt quá trình tái huấn luyện
def retrain_model():
    """
    Hiển thị giao diện chọn Dataset và Model, và kích hoạt tái huấn luyện.
    """
    # 1. KIỂM TRA ĐĂNG NHẬP
    if 'bank_id' not in session:
        flash('Vui lòng đăng nhập để sử dụng chức năng này.', 'danger')
        return redirect(url_for('auth.login'))

    bank_id = session.get('bank_id')

    # 2. Xử lý yêu cầu POST (Kích hoạt Huấn luyện)
    if request.method == 'POST':
        # Lấy các tham số cần thiết từ form/người dùng
        # Giả định form có trường 'dataset_id' (từ danh sách Dataset đã upload)
        dataset_id_str = request.form.get('dataset_id')

        try:
            dataset_id = int(dataset_id_str)
        except (TypeError, ValueError):
            flash('ID Dataset không hợp lệ. Vui lòng chọn lại.', 'warning')
            return redirect(url_for('optimize.retrain_model'))

        # Lấy model_id gốc (Model Gốc/Mẫu)
        # Giả định: Người dùng chọn model gốc (Ví dụ: ID 1)
        base_model_id = request.form.get('base_model_id', 1)

        # --- KÍCH HOẠT LOGIC ML ---
        success, run_id = train_and_save_new_run(
            db_config=DATABASE_CONFIG,
            bank_id=bank_id,
            dataset_id=dataset_id,
            base_model_id=int(base_model_id)
        )

        if success:
            flash(f'Tái huấn luyện hoàn tất! Phiên Run ID: {run_id}. Model F1-Score đã được cập nhật.', 'success')
            # Chuyển hướng đến trang quản lý lịch sử huấn luyện
            return redirect(url_for('main.dashboard'))
        else:
            flash('Lỗi xảy ra trong quá trình tái huấn luyện. Vui lòng kiểm tra log.', 'danger')
            return redirect(url_for('optimize.retrain_model'))

    # 3. Xử lý yêu cầu GET (Hiển thị Form)
    # Tải danh sách các Dataset đã được xử lý (status='Processed') của Bank này
    # Ta cần một hàm CSDL để thực hiện việc này (ví dụ: db_connector.get_processed_datasets)

    datasets = []  # Tạm thời để trống. Bạn cần điền logic CSDL vào đây.

    return render_template('optimize/toiuu.html', datasets=datasets)


# Giả định: Bạn cũng có thể cần một route để xem lịch sử Training Run
@optimize_bp.route('/history')
def training_history():
    # Logic để tải và hiển thị danh sách các bản ghi từ bảng training_run
    # ...
    return render_template('optimize/training_history.html')