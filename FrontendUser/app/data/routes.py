# Tên file: app/data/routes.py

import os
import pandas as pd
import numpy as np  # Cần cho việc xử lý NaN
from flask import (render_template, request, redirect, url_for,
                   flash, current_app)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from . import bp
from ..DatabaseConnector import DatabaseConnector

# --- Danh sách cột bắt buộc ---
REQUIRED_INPUT_COLUMNS = {
    'credit_score', 'country', 'gender', 'age', 'tenure', 'balance',
    'products_number', 'credit_card', 'active_member', 'estimated_salary'
}
# Cột target 'churn' sẽ được thêm sau khi dự đoán.
ALL_CUSTOMER_COLUMNS = list(REQUIRED_INPUT_COLUMNS)
ALL_CUSTOMER_COLUMNS.insert(0, 'customer_id')  # Thêm customer_id để truy vấn
ALL_CUSTOMER_COLUMNS.append('churn')


def check_required_columns(df):
    """Kiểm tra DataFrame có đủ các cột đầu vào BẮT BUỘC không."""
    # Kiểm tra cột bắt buộc (không bao gồm churn, customer_id, dataset_id)
    missing_cols = REQUIRED_INPUT_COLUMNS - set(df.columns)
    if missing_cols:
        return False, f"Thiếu các cột đầu vào bắt buộc: {', '.join(missing_cols)}"
    return True, None


def allowed_file(filename):
    """Kiểm tra đuôi file có hợp lệ không"""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in \
        current_app.config['ALLOWED_EXTENSIONS']


def execute_db_insert(db, sql, params=None):
    """Hàm tiện ích để thực hiện INSERT/UPDATE (giả định có trong Connector)."""
    if not db.conn or not db.conn.is_connected():
        if not db.connect(): return False
    try:
        cursor = db.conn.cursor()
        cursor.execute(sql, params)
        db.conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"Lỗi thực thi DB: {e}")
        return False


# --- CÁC ROUTES CHÍNH ---

@bp.route('/dulieu')
@login_required
def data_page():
    """Truy vấn và Hiển thị dữ liệu khách hàng từ bảng 'customer'."""
    customers_data = None
    db_config = current_app.config['DATABASE_CONFIG']

    try:
        with DatabaseConnector(**db_config) as db:
            # 1. Lấy tất cả dữ liệu từ bảng customer (trừ customer_id và dataset_id)
            sql_query = f"SELECT {', '.join(ALL_CUSTOMER_COLUMNS)} FROM customer LIMIT 100"  # Giới hạn 100 dòng
            df = db.queryDataset(sql_query)  # Sử dụng hàm queryDataset đã có

            if df is not None and not df.empty:
                # Chuyển DataFrame sang định dạng list of dicts cho Jinja2
                customers_data = df.to_dict('records')

    except Exception as e:
        flash(f"Lỗi CSDL khi tải dữ liệu khách hàng: {e}", 'error')

    return render_template('dulieu.html',
                           customers=customers_data,
                           all_columns=ALL_CUSTOMER_COLUMNS,  # Truyền tên cột để tạo header
                           active_page='data')


@bp.route('/upload_data', methods=['POST'])
@login_required
def upload_data():
    """Xử lý upload, kiểm tra cột, lưu metadata và chèn dữ liệu vào bảng 'customer'."""

    # ... (Logic kiểm tra file và lưu file tạm thời giữ nguyên) ...
    # 1. Kiểm tra file và lưu file tạm thời
    if 'dataset_file' not in request.files:
        flash('Không có phần file nào trong request', 'error')
        return redirect(url_for('data.data_page'))

    file = request.files['dataset_file']
    filename = secure_filename(file.filename)
    if not allowed_file(file.filename):
        flash('Loại file không hợp lệ.', 'error')
        return redirect(url_for('data.data_page'))

    save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(save_path)  # Lưu tạm

    # 2. KIỂM TRA & XỬ LÝ DỮ LIỆU
    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(save_path)
        else:
            df = pd.read_excel(save_path)

        is_valid, error_msg = check_required_columns(df)
        if not is_valid:
            os.remove(save_path)
            flash(f"Lỗi cấu trúc dữ liệu: {error_msg}", 'error')
            return redirect(url_for('data.data_page'))

        # Thêm các cột metadata cần thiết cho bảng customer
        df['dataset_id'] = 1  # ⚠️ Cần thay thế bằng ID dataset thực tế sau khi insert vào bảng dataset
        df['churn'] = np.nan  # Cột churn ban đầu là NULL (trống)

        # Đảm bảo df chỉ chứa các cột phù hợp với bảng customer (tránh lỗi)
        # Bỏ qua customer_id vì nó là auto-increment
        insert_cols = ['dataset_id', 'churn'] + list(REQUIRED_INPUT_COLUMNS)
        df = df[insert_cols]

    except Exception as e:
        os.remove(save_path)
        flash(f"Lỗi khi đọc file hoặc kiểm tra cấu trúc: {e}", 'error')
        return redirect(url_for('data.data_page'))

    # 3. LƯU DỮ LIỆU VÀ METADATA VÀO DATABASE
    db_config = current_app.config['DATABASE_CONFIG']

    try:
        with DatabaseConnector(**db_config) as db:
            # 3A. LƯU DATASET METADATA VÀO BẢNG 'dataset'
            # Giả định bank_id = 1 và status = 'LOADED'
            sql_meta = """INSERT INTO dataset (bank_id, upload_date, file_path, status)
                          VALUES (%s, NOW(), %s, %s)"""
            # Giả sử bank_id của admin là 1
            execute_db_insert(db, sql_meta, (1, save_path, 'LOADED'))
            # ⚠️ Cần lấy dataset_id vừa tạo để gán cho df['dataset_id']
            # Bỏ qua bước lấy ID này trong code hiện tại để đơn giản, sử dụng dataset_id=1.

            # 3B. CHÈN DỮ LIỆU KHÁCH HÀNG VÀO BẢNG 'customer'
            # Chuẩn bị SQL INSERT
            cols_str = ', '.join(df.columns)
            placeholders = ', '.join(['%s'] * len(df.columns))
            sql_insert_data = f"INSERT INTO customer ({cols_str}) VALUES ({placeholders})"

            # Chuẩn bị dữ liệu (list of tuples)
            data_to_insert = [tuple(row) for row in df.values]

            # Chèn hàng loạt (executemany)
            if data_to_insert:
                cursor = db.conn.cursor()
                cursor.executemany(sql_insert_data, data_to_insert)
                db.conn.commit()
                cursor.close()
                flash(f'Đã chèn thành công {len(data_to_insert)} bản ghi khách hàng vào CSDL.', 'success')

    except Exception as e:
        flash(f"Lỗi Database: Không thể chèn dữ liệu vào bảng customer. {e}", 'error')
        # Vẫn giữ file tạm nếu DB insert thất bại
        return redirect(url_for('data.data_page'))

    os.remove(save_path)  # Xóa file tạm sau khi đã chèn vào DB
    return redirect(url_for('data.data_page'))