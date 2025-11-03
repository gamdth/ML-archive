# Tên file: app/stats/routes.py

from flask import render_template, request
from . import bp  # Import tương đối

# --- Dữ liệu giả lập (Sau này bạn sẽ thay bằng database/pandas) ---
MOCK_DATA_AGE = {
    'labels': ['Dưới 25', '25-35', '36-45', 'Trên 45'],
    'data': [30, 55, 25, 15]
}
MOCK_DATA_SCORE = {
    'labels': ['Dưới 500', '500-650', '651-750', 'Trên 750'],
    'data': [10, 45, 50, 20]
}


# --- Kết thúc dữ liệu giả lập ---


@bp.route('/thongke', methods=['GET', 'POST'])
def view_stats():
    """
    Hiển thị trang (GET)
    Xử lý khi nhấn nút "Thống kê" (POST)
    """

    # Biến để gửi sang template
    chart_data = None
    chart_labels = None
    chart_type = 'bar'  # Mặc định là biểu đồ cột
    selected_var = ''  # Để 'select' nhớ lựa chọn

    if request.method == 'POST':
        # 1. Lấy lựa chọn từ form
        variable = request.form.get('variable_select')
        chart_type = request.form.get('chart_type_select', 'bar')
        selected_var = variable

        # 2. Xử lý logic (giả lập)
        if variable == 'age':
            chart_labels = MOCK_DATA_AGE['labels']
            chart_data = MOCK_DATA_AGE['data']
        elif variable == 'score':
            chart_labels = MOCK_DATA_SCORE['labels']
            chart_data = MOCK_DATA_SCORE['data']

        # (Nếu không chọn gì, chart_data sẽ vẫn là None)

    # 3. Render lại trang
    return render_template('thongke.html',
                           active_page='stats',  # Cho sidebar
                           chart_data=chart_data,
                           chart_labels=chart_labels,
                           chart_type=chart_type,
                           selected_var=selected_var,
                           selected_type=chart_type
                           )