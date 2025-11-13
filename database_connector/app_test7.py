import csv
import os
import json
import io
import base64
import traceback
import joblib
import numpy as np
import openai
import pandas as pd
import seaborn as sns
import matplotlib
import matplotlib.pyplot as plt
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, make_response, session, flash, jsonify
import mysql.connector
from mysql.connector import Error

# Thư viện ML
from sklearn.preprocessing import FunctionTransformer, StandardScaler, OneHotEncoder
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import f1_score, roc_auc_score, classification_report, confusion_matrix, ConfusionMatrixDisplay
import xgboost as xgb

# (SỬA LỖI IMPORT)
from plotter import plot_eda_scatter_base64, plot_eda_box_base64

# Cấu hình Matplotlib để chạy trên server (không hiển thị GUI)
matplotlib.use('Agg')

# =============================================================================
# PHẦN 1: CẤU HÌNH VÀ KHỞI TẠO APP
# =============================================================================

basedir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(basedir, 'templates')
static_dir = os.path.join(basedir, 'static')
data_dir = os.path.join(basedir, 'data')
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

# --- (MỚI) THÊM LẠI KHỐI NÀY ---
# FILES (CSV)
USER_CSV_FILE = os.path.join(basedir, 'QLND.csv')
DATA_CSV_FILE = os.path.join(basedir, 'QLDL.csv')
ACTIVITY_CSV_FILE = os.path.join(basedir, 'QLHD.csv') # <-- Đây là biến bị thiếu
CAMPAIGN_CSV_FILE = os.path.join(basedir, 'QLCD.csv')

# FILE JSON
USERS_JSON_FILE = os.path.join(data_dir, 'data.json')

# Cấu hình CSDL (ĐÃ SỬA 'user')
DATABASE_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "database": "bank",
    "user": "root",
    "password": "@Obama123"
}

# (SỬA LỖI BẢO MẬT) - Dùng Biến Môi trường
# ---------------------------------------------------------------------------
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("\n" + "="*50)
    print("CẢNH BÁO: Không tìm thấy 'OPENAI_API_KEY' trong biến môi trường.")
    print("Tính năng tư vấn AI (LLM) sẽ không hoạt động.")
    print("="*50 + "\n")
# ---------------------------------------------------------------------------

# Admin Cố Định
ADMIN_EMAIL = "admin@gmail.com"
ADMIN_PASSWORD = "123"

# Cấu hình Flask App
basedir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(basedir, 'templates')
static_dir = os.path.join(basedir, 'static')
data_dir = os.path.join(basedir, 'data')  # Thư mục lưu CSV
model_dir = os.path.join(basedir, 'saved_models')  # Thư mục lưu .joblib
os.makedirs(data_dir, exist_ok=True)
os.makedirs(model_dir, exist_ok=True)

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.secret_key = "super-secret-key-cho-session"


# =============================================================================
# PHẦN 1.5: (MỚI) LOGIC TƯ VẤN AI (LLM - OPENAI)
# =============================================================================

def get_strategy_from_openai(segment_name_vietnamese, segment_stats, bank_name="Ngân hàng"):
    """
    Hàm này gọi OpenAI API để lấy tư vấn chiến lược.
    """
    if not OPENAI_API_KEY:
        print("Lỗi: Thiếu OPENAI_API_KEY. Không thể gọi API.")
        # Trả về lỗi dạng Markdown để frontend có thể hiển thị
        return """
        **Lỗi: Tính năng tư vấn AI chưa được cấu hình.**

        Vui lòng liên hệ Administrator để cung cấp API Key cho hệ thống.
        """

    try:
        # Khởi tạo client
        client = openai.OpenAI(api_key=OPENAI_API_KEY)

        # --- Xây dựng PROMPT (Đây là phần quan trọng nhất) ---

        # Chuyển đổi segment_stats thành văn bản dễ đọc
        stats_text = f"""
        - Tổng số khách hàng trong nhóm: {segment_stats.get('count', 'N/A')}
        - Tỷ lệ dự đoán rời bỏ trung bình: {segment_stats.get('avg_churn', 0):.2f}%
        - Số dư trung bình: ${segment_stats.get('avg_balance', 0):,.2f}
        - Điểm tín dụng trung bình: {segment_stats.get('avg_credit_score', 0):.0f}
        - Tuổi trung bình: {segment_stats.get('avg_age', 0):.0f} tuổi
        """

        # 1. System Prompt: Định nghĩa vai trò của AI
        system_prompt = f"""
        Bạn là một chuyên gia tư vấn chiến lược giữ chân khách hàng (Customer Retention Strategist) 
        làm việc cho {bank_name}. 
        Nhiệm vụ của bạn là cung cấp các chiến dịch marketing hoặc chăm sóc khách hàng 
        cụ thể, sáng tạo, và thực tế. 
        Hãy sử dụng giọng điệu chuyên nghiệp, thuyết phục và trả lời bằng Tiếng Việt.
        """

        # 2. User Prompt: Đưa ra yêu cầu cụ thể
        user_prompt = f"""
        Tôi cần 3 chiến dịch cụ thể để nhắm vào nhóm khách hàng sau:

        **Tên nhóm:** {segment_name_vietnamese}
        **Thông tin tóm tắt về nhóm:**
        {stats_text}

        Hãy đề xuất 3 chiến dịch. Với mỗi chiến dịch, vui lòng trình bày rõ ràng:
        1.  **Tên/Tiêu đề chiến dịch:** (Ngắn gọn, hấp dẫn)
        2.  **Mục tiêu chính:** (Ví dụ: Tăng tương tác, giảm 10% churn, bán chéo sản phẩm...)
        3.  **Lý do & Cách tiếp cận:** (Giải thích ngắn gọn tại sao chiến dịch này hiệu quả với đặc điểm nhóm này?)
        4.  **Nội dung mẫu (Email/SMS/Thông báo):** (Chỉ 1 ví dụ ngắn cho mỗi chiến dịch)

        Hãy định dạng câu trả lời bằng Markdown để hiển thị đẹp trên web. 
        Bắt đầu thẳng vào chiến dịch đầu tiên.
        """

        print(f"Đang gọi OpenAI API cho nhóm: {segment_name_vietnamese}...")

        # 3. Gọi API
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Có thể đổi sang "gpt-4" để có kết quả tốt hơn
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7  # Tăng tính sáng tạo một chút
        )

        response_content = completion.choices[0].message.content
        print("OpenAI trả lời thành công.")
        return response_content

    except openai.AuthenticationError:
        print("Lỗi OpenAI: Sai API Key.")
        return "Lỗi: Cấu hình API Key không chính xác. Vui lòng liên hệ Admin."
    except openai.RateLimitError:
        print("Lỗi OpenAI: Hết quota hoặc API bị quá tải.")
        return "Lỗi: API AI đang bận hoặc đã đạt giới hạn. Vui lòng thử lại sau ít phút."
    except Exception as e:
        print(f"LỖI không xác định khi gọi OpenAI: {e}")
        traceback.print_exc()
        return f"Lỗi server khi đang xử lý tư vấn AI: {e}"

# =============================================================================
# PHẦN 2: LOGIC ML & DB (Gộp từ train_and_predict.py và plotter.py)
# =============================================================================

# --- Class DatabaseConnector (từ train_and_predict.py) ---
class DatabaseConnector:
    """Quản lý kết nối CSDL MySQL"""

    def __init__(self, **kwargs):
        self.config = kwargs
        self.conn = None

    def connect(self):
        try:
            self.conn = mysql.connector.connect(**self.config)
            return self.conn
        except mysql.connector.Error as e:
            print(f"LỖI KẾT NỐI MYSQL: {e}")
            self.conn = None
            return None

    def disConnect(self):
        if self.conn and self.conn.is_connected():
            self.conn.close()

    def queryDataset(self, sql, params=None):
        if not self.conn or not self.conn.is_connected():
            if not self.connect(): return None
        try:
            df = pd.read_sql(sql, self.conn, params=params)
            return df
        except Exception as e:
            print(f"Lỗi khi truy vấn queryDataset: {e}")
            return None

    def execute_query(self, sql, params=None, fetch_last_id=False):
        if not self.conn or not self.conn.is_connected():
            if not self.connect(): return None if fetch_last_id else False
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, params)
            self.conn.commit()
            last_id = cursor.lastrowid if fetch_last_id else None
            cursor.close()
            return last_id if fetch_last_id else True
        except mysql.connector.Error as e:
            print(f"Lỗi khi thực thi execute_query: {e}")
            self.conn.rollback()
            return None if fetch_last_id else False
        except Exception as e:
            print(f"Lỗi không xác định trong execute_query: {e}")
            return None if fetch_last_id else False

    def __enter__(self):
        if self.connect():
            return self
        else:
            raise IOError("Không thể kết nối CSDL")

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disConnect()


# --- Các hàm xử lý dữ liệu (từ train_and_predict.py) ---
def add_custom_features(df_in):
    """ Hàm tạo đặc trưng """
    df = df_in.copy()
    epsilon = 1e-6
    df['Balance_per_Salary'] = df['balance'] / (df['estimated_salary'] + epsilon)
    df['CreditScore_per_Tenure'] = df['credit_score'] / (df['tenure'] + 1.0)
    df['Balance_per_Age'] = df['balance'] / (df['age'] + epsilon)
    df['Active_HasCard'] = df['active_member'] * df['credit_card']
    df['Products_per_Tenure'] = df['products_number'] / (df['tenure'] + 1.0)
    return df


def fetch_training_data(db_connector, dataset_id_to_train):
    """ Tải dữ liệu từ CSDL (chỉ lấy các cột cần thiết) """
    print(f"Đang tải dữ liệu huấn luyện từ CSDL cho dataset_id = {dataset_id_to_train}...")
    sql_query = """
    SELECT 
        credit_score, country, gender, age, tenure, balance, 
        products_number, credit_card, active_member, estimated_salary, 
        churn 
    FROM Customer
    WHERE dataset_id = %s 
    """
    params = (dataset_id_to_train,)
    df = db_connector.queryDataset(sql_query, params)
    if df is None or df.empty:
        print(f"Lỗi: Không tìm thấy dữ liệu cho dataset_id = {dataset_id_to_train}.")
        return None
    print(f"Tải thành công {len(df)} dòng dữ liệu.")
    return df


# --- Hàm Huấn luyện (từ train_and_predict.py) ---
def train_churn_model(df):
    """ Hàm huấn luyện chính (trả về model và dữ liệu test) """
    print("\nBắt đầu quá trình huấn luyện mô hình (GridSearchCV + Feature Engineering)...")
    features = ['credit_score', 'country', 'gender', 'age', 'tenure', 'balance',
                'products_number', 'credit_card', 'active_member', 'estimated_salary']
    target = 'churn'
    X = df[features]
    y = df[target]

    numeric_features = [
        'credit_score', 'age', 'tenure', 'balance', 'products_number', 'estimated_salary',
        'Balance_per_Salary', 'CreditScore_per_Tenure', 'Balance_per_Age',
        'Active_HasCard', 'Products_per_Tenure'
    ]
    categorical_features = ['country', 'gender']

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), numeric_features),
            ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
        ],
        remainder='passthrough'
    )

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()

    model = xgb.XGBClassifier(use_label_encoder=False, eval_metric='logloss', random_state=42)
    full_pipeline = Pipeline(steps=[
        ('feature_engineering', FunctionTransformer(add_custom_features, validate=False)),
        ('preprocessor', preprocessor),
        ('model', model)
    ])
    param_grid = {
        'model__max_depth': [6, 8],  # Giảm số lượng để chạy nhanh hơn
        'model__learning_rate': [0.1, 0.12],
        'model__n_estimators': [100, 125],
        'model__scale_pos_weight': [scale_pos_weight]
    }
    grid_search = GridSearchCV(estimator=full_pipeline, param_grid=param_grid, scoring='f1', cv=3, n_jobs=-1,
                               verbose=1)  # cv=3
    grid_search.fit(X_train, y_train)

    best_model_pipeline = grid_search.best_estimator_
    y_pred = best_model_pipeline.predict(X_test)
    f1 = f1_score(y_test, y_pred)
    auc = roc_auc_score(y_test, best_model_pipeline.predict_proba(X_test)[:, 1])
    print(f"Huấn luyện xong. F1: {f1:.4f}, AUC: {auc:.4f}")

    return best_model_pipeline, f1, auc, X_test, y_test


# --- Hàm lưu trữ (MỚI - Sửa để lưu vào training_run) ---
# (Nằm trong app.py)
def save_model_artifact_and_db_record(bank_id, dataset_id, model_pipeline, f1, auc):
    """
    (ĐÃ SỬA) Lưu file .joblib VÀ lưu bản ghi vào 'training_run'.
    """
    run_id = None
    artifact_path = None
    try:
        # (SỬA LỖI Ở ĐÂY)
        # Giả định model gốc (XGBoost) có ID=3 (dựa trên CSDL của bạn)
        BASE_MODEL_ID = 3

        with DatabaseConnector(**DATABASE_CONFIG) as db:
            # 1. Tạo bản ghi training_run (trạng thái 'Pending') để lấy run_id
            sql_insert_run = """
            INSERT INTO training_run (bank_id, dataset_id, model_id, run_date, status)
            VALUES (%s, %s, %s, %s, %s)
            """
            run_id = db.execute_query(sql_insert_run,
                                      (bank_id, dataset_id, BASE_MODEL_ID, datetime.now(), 'Pending'),
                                      fetch_last_id=True)

            if not run_id:
                raise Exception("Không thể tạo bản ghi training_run ban đầu.")

            # (Các bước 2 và 3 giữ nguyên)
            # 2. Lưu file artifact .joblib...
            artifact_filename = f"model_run_{run_id}.joblib"
            artifact_path = os.path.join(model_dir, artifact_filename).replace("\\", "/")
            joblib.dump(model_pipeline, artifact_path)
            print(f"Đã lưu artifact vào: {artifact_path}")

            # 3. Cập nhật bản ghi training_run...
            sql_update_run = """
            UPDATE training_run 
            SET performance_metric = %s, full_report_path = %s, status = %s
            WHERE run_id = %s
            """
            db.execute_query(sql_update_run, (auc, artifact_path, 'Completed', run_id))

            print(f"Đã cập nhật training_run ID: {run_id} với kết quả.")
            return run_id

    except Exception as e:
        print(f"LỖI nghiêm trọng khi lưu model/bản ghi DB: {e}")
        traceback.print_exc()
        if run_id:
            try:
                with DatabaseConnector(**DATABASE_CONFIG) as db:
                    db.execute_query("DELETE FROM training_run WHERE run_id = %s", (run_id,))
            except:
                pass
        return None


# --- Các hàm vẽ biểu đồ (từ plotter.py) ---
def plot_to_base64(fig):
    """Hàm helper: Chuyển Matplotlib figure thành Base64."""
    img_buffer = io.BytesIO()
    fig.savefig(img_buffer, format='png', bbox_inches='tight')
    plt.close(fig)
    img_buffer.seek(0)
    return base64.b64encode(img_buffer.getvalue()).decode('utf-8')


def plot_feature_importance_base64(model_pipeline):
    """Vẽ Feature Importance và trả về Base64."""
    try:
        xgb_model = model_pipeline.named_steps['model']
        preprocessor = model_pipeline.named_steps['preprocessor']

        # Cố gắng lấy tên đặc trưng
        try:
            feature_names = preprocessor.get_feature_names_out()
        except Exception:
            # Cách dự phòng (nếu get_feature_names_out thất bại)
            num_features = preprocessor.transformers_[0][2]
            cat_features_raw = preprocessor.named_transformers_['cat'].get_feature_names_out()
            feature_names = np.concatenate([num_features, cat_features_raw])

        importances = xgb_model.feature_importances_
        df = pd.DataFrame({'Feature': feature_names, 'Importance': importances})
        df = df.sort_values(by='Importance', ascending=False)
        df['Feature'] = df['Feature'].str.replace('num__', '').str.replace('cat__', '')

        fig, ax = plt.subplots(figsize=(10, 8))
        sns.barplot(x='Importance', y='Feature', data=df.head(15), color="#3498db", ax=ax)
        ax.set_title('Top 15 Đặc trưng Quan trọng nhất')
        return plot_to_base64(fig)
    except Exception as e:
        print(f"Lỗi vẽ Feature Importance: {e}")
        return None


def plot_confusion_matrix_base64(model_pipeline, X_test, y_test):
    """Vẽ Ma trận Nhầm lẫn và trả về Base64."""
    try:
        y_pred = model_pipeline.predict(X_test)
        cm = confusion_matrix(y_test, y_pred)
        fig, ax = plt.subplots(figsize=(8, 6))
        disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=['Ở lại (0)', 'Rời bỏ (1)'])
        disp.plot(ax=ax, cmap='Blues', colorbar=False)
        ax.set_title('Ma trận Nhầm lẫn (Hiệu suất)')
        return plot_to_base64(fig)
    except Exception as e:
        print(f"Lỗi vẽ Confusion Matrix: {e}")
        return None


# =============================================================================
# PHẦN 3: ROUTES CỐT LÕI (Login, Logout, Home)
# =============================================================================

# --- Hàm tiện ích (Sửa lại để dùng DatabaseConnector) ---
def get_admin_user_details():
    return {"email": ADMIN_EMAIL, "role": "Admin", "name": "Administrator"}


def get_bank_user_from_db(email, password):
    """Tìm người dùng ngân hàng trong bảng Bank."""
    with DatabaseConnector(**DATABASE_CONFIG) as db:
        query = "SELECT bank_id, bank_name, account_username, account_password FROM Bank WHERE account_username = %s"
        df = db.queryDataset(query, (email,))
        if df is None or df.empty:
            return None

        bank_user = df.iloc[0]
        # (Trong thực tế: dùng check_password_hash)
        if bank_user['account_password'] == password:
            return {
                "bank_id": int(bank_user['bank_id']),
                "email": bank_user['account_username'],
                "name": bank_user['bank_name'],
                "role": "BankUser"
            }
        return None


# --- Routes ---
@app.route("/")
def home():
    return redirect(url_for('login'))


@app.route("/login", methods=["GET", "POST"])
def login():
    message = ""
    saved_email = request.cookies.get("email")
    saved_password = request.cookies.get("password")

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        remember = request.form.get("remember")
        user_data = None

        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            user_data = get_admin_user_details()
        else:
            bank_user = get_bank_user_from_db(email, password)
            if bank_user:
                user_data = bank_user

        if user_data:
            session["user"] = user_data
            resp = make_response(redirect(url_for("success")))
            if remember:
                resp.set_cookie("email", email, max_age=60 * 60 * 24 * 7)
                resp.set_cookie("password", password, max_age=60 * 60 * 24 * 7)
            else:
                resp.delete_cookie("email")
                resp.delete_cookie("password")
            return resp
        else:
            message = "Sai email hoặc mật khẩu!"
            return render_template("login.html", message=message, saved_email=saved_email,
                                   saved_password=saved_password)
    return render_template("login.html", message=message, saved_email=saved_email, saved_password=saved_password)


@app.route("/logout")
def logout():
    session.pop('user', None)
    resp = make_response(redirect(url_for('login')))
    resp.delete_cookie("email")
    resp.delete_cookie("password")
    flash("Bạn đã đăng xuất.", "info")
    return resp


@app.route("/success")
def success():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("success.html")


@app.route("/go_home", methods=["POST"])
def go_home():
    if "user" not in session:
        return redirect(url_for("login"))
    user_role = session["user"].get("role")
    if user_role == "Admin":
        return redirect(url_for("tongquan"))
    elif user_role == "BankUser":
        return redirect(url_for("uhome_page"))
    else:
        return redirect(url_for("logout"))


# =============================================================================
# PHẦN 4: ROUTES TRANG CHỦ (Admin vs User)
# =============================================================================

@app.route("/home")
def home_page():
    """TRANG CHỦ CỦA ADMIN (Route /home)"""
    if "user" not in session or session["user"].get("role") != "Admin":
        return redirect(url_for("login"))
    return redirect(url_for("tongquan"))


@app.route("/Uhome")
def uhome_page():
    """TRANG CHỦ CỦA BANKUSER (Route /Uhome)"""
    if "user" not in session or session["user"].get("role") != "BankUser":
        return redirect(url_for("login"))
    return render_template("Uhome.html")


# =============================================================================
# PHẦN 5: ROUTES CỦA ADMIN (Dùng DatabaseConnector)
# =============================================================================

@app.route("/quanlinguoidung1")
def quanlinguoidung1():
    """ADMIN: Quản lý Bank."""
    if "user" not in session or session["user"].get("role") != "Admin":
        return redirect(url_for("login"))

    banks_df = None
    with DatabaseConnector(**DATABASE_CONFIG) as db:
        query = "SELECT bank_id, bank_name, bank_code, contact_person, email, account_username FROM Bank"
        banks_df = db.queryDataset(query)

    banks = banks_df.to_dict('records') if banks_df is not None else []
    return render_template("quanlinguoidung1.html", users=banks)


# (Đảm bảo bạn đã import: request, DatabaseConnector, flash, redirect, url_for, session)
# (Bạn cũng cần 'from werkzeug.security import generate_password_hash' nếu muốn băm mật khẩu)

@app.route("/add_user", methods=["POST"])
def add_user():
    """
    (SỬA) ADMIN: Thêm Bank (User) mới.
    Đọc dữ liệu từ form modal đã được sửa.
    """
    if "user" not in session or session["user"].get("role") != "Admin":
        return redirect(url_for("login"))

    if request.method == "POST":
        # (SỬA) Đọc các trường mới từ form
        bank_name = request.form.get("bank_name")
        bank_code = request.form.get("bank_code")
        contact_person = request.form.get("contact_person")
        email = request.form.get("email")
        username = request.form.get("account_username")
        password = request.form.get("account_password")

        # (Nên băm mật khẩu ở đây trước khi lưu)
        # password_hash = generate_password_hash(password)

        try:
            with DatabaseConnector(**DATABASE_CONFIG) as db:
                query = """
                INSERT INTO Bank (bank_name, bank_code, contact_person, email, account_username, account_password)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                # (Thay 'password' bằng 'password_hash' nếu bạn băm mật khẩu)
                if db.execute_query(query, (bank_name, bank_code, contact_person, email, username, password)):
                    flash("Thêm ngân hàng (user) thành công!", "success")
                else:
                    flash("Lỗi khi thêm ngân hàng.", "error")
        except Error as e:
            # Lỗi (ví dụ: trùng bank_code hoặc account_username)
            flash(f"Lỗi CSDL: {e.msg}", "error")
        except Exception as e:
            flash(f"Lỗi không xác định: {e}", "error")

    return redirect(url_for('quanlinguoidung1'))


@app.route("/quanlihoatdong")
def quanlihoatdong():
    """ADMIN: Quản lý hoạt động (Theo luồng)."""
    if "user" not in session or session["user"].get("role") != "Admin":
        return redirect(url_for("login"))

    # Logic đọc file CSV (vì bạn giữ lại logic CSV)
    activity_list = []
    try:
        with open(ACTIVITY_CSV_FILE, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            activity_list = list(reader)
    except FileNotFoundError:
        print(f"LỖI: Không tìm thấy file {ACTIVITY_CSV_FILE}.")

    return render_template("quanlihoatdong.html", activities=activity_list)


# =============================================================================
# PHẦN 6: ROUTES DÙNG CHUNG (Admin/User)
# =============================================================================

# (Đảm bảo bạn đã import: request, DatabaseConnector, flash, redirect, url_for, session, render_template)

@app.route("/quanlidulieu")
def quanlidulieu():
    """
    (ĐÃ SỬA) Route này CHỈ DÀNH CHO ADMIN.
    Hiển thị TẤT CẢ các dataset từ tất cả các ngân hàng.
    """
    if "user" not in session or session["user"].get("role") != "Admin":
        flash("Bạn không có quyền truy cập trang này.", "error")
        return redirect(url_for("login"))

    data_list = []
    try:
        with DatabaseConnector(**DATABASE_CONFIG) as db:
            # Admin thấy tất cả
            query = """
            SELECT d.dataset_id, b.bank_name, d.upload_date, d.file_path, d.status
            FROM Dataset d 
            JOIN Bank b ON d.bank_id = b.bank_id
            ORDER BY d.upload_date DESC
            """
            df = db.queryDataset(query)
            if df is not None:
                data_list = df.to_dict('records')

    except Exception as e:
        flash(f"Lỗi tải danh sách dữ liệu: {e}", "error")

    # Truyền 'data_list' vào template, HTML sẽ gọi nó là 'data'
    return render_template("quanlidulieu.html", data=data_list)


# (Đảm bảo bạn đã import: request, DatabaseConnector, flash, redirect, url_for, session, render_template)

@app.route("/quanlicacchiendich")
def quanlicacchiendich():
    """
    (SỬA) ADMIN: Trang này giờ sẽ hiển thị danh sách các Model Gốc (ml_model).
    """
    if "user" not in session or session["user"].get("role") != "Admin":
        flash("Bạn không có quyền truy cập trang này.", "error")
        return redirect(url_for("login"))

    models_list = []
    try:
        with DatabaseConnector(**DATABASE_CONFIG) as db:
            # (MỚI) Truy vấn bảng ml_model
            query = "SELECT model_id, model_name, description, created_date, status FROM ml_model"
            df_models = db.queryDataset(query)

            if df_models is not None:
                models_list = df_models.to_dict('records')

    except Exception as e:
        print(f"Lỗi khi tải danh sách model: {e}")
        flash(f"Lỗi tải dữ liệu: {e}", "error")

    # (SỬA) Gửi 'models_list' vào template (HTML sẽ gọi nó là 'models')
    return render_template("quanlicacchiendich.html", models=models_list)


# --- Routes Tiện ích ---
@app.route("/forgetpassword")
def forgetpassword():
    return render_template("forgetpassword.html")


@app.route("/go_login", methods=["POST"])
def go_login():
    return redirect(url_for("login"))


@app.route("/gioithieu")
def gioithieu():
    return render_template("gioithieu.html")


@app.route("/thongbao")
def thongbao():
    return render_template("thongbao.html")


# (Đảm bảo bạn đã import: request, DatabaseConnector, flash, redirect, url_for, session, render_template)

@app.route("/tongquan")
def tongquan():
    """
    (ĐÃ SỬA) Trang tổng quan của ADMIN.
    Truy vấn CSDL để lấy các số liệu thống kê chung.
    """
    if "user" not in session or session["user"].get("role") != "Admin":
        flash("Bạn không có quyền truy cập trang này.", "error")
        return redirect(url_for("login"))

    stats = {
        'total_users': 0,
        'total_datasets': 0,
        'total_runs': 0,
        'total_predictions': 0
    }

    try:
        with DatabaseConnector(**DATABASE_CONFIG) as db:
            # 1. Đếm tổng số User (Bank)
            df_users = db.queryDataset("SELECT COUNT(*) as total FROM Bank")
            if df_users is not None:
                stats['total_users'] = int(df_users.iloc[0]['total'])

            # 2. Đếm tổng số bản ghi dữ liệu (Dataset)
            df_datasets = db.queryDataset("SELECT COUNT(*) as total FROM Dataset")
            if df_datasets is not None:
                stats['total_datasets'] = int(df_datasets.iloc[0]['total'])

            # 3. Đếm tổng số chiến dịch hoạt động (Training Runs)
            df_runs = db.queryDataset("SELECT COUNT(*) as total FROM training_run WHERE status = 'Completed'")
            if df_runs is not None:
                stats['total_runs'] = int(df_runs.iloc[0]['total'])

            # 4. Đếm tổng số chiến dịch được gợi ý (Mock data, vì CSDL không có)
            # (Bạn có thể thay bằng cách đếm số dự đoán)
            df_preds = db.queryDataset("SELECT COUNT(DISTINCT run_id) as total FROM prediction_result")
            if df_preds is not None:
                stats['total_predictions'] = int(df_preds.iloc[0]['total'])

    except Exception as e:
        print(f"Lỗi khi tải dữ liệu Tổng quan: {e}")
        flash(f"Lỗi tải dữ liệu: {e}", "error")

    # Truyền 'stats' vào template
    return render_template("tongquan.html", stats=stats)


# (Đảm bảo bạn đã import: request, DatabaseConnector, flash, redirect, url_for, session, render_template)

@app.route("/caidat")
def caidat():
    """
    (ĐÃ SỬA) Hiển thị trang Cài đặt (với thông tin User).
    Sẽ lấy dữ liệu chi tiết của user (Admin hoặc Bank) từ CSDL.
    """
    if "user" not in session:
        return redirect(url_for("login"))

    user_data = session["user"]
    role = user_data.get("role")
    user_details = {}  # Dùng biến này để truyền vào template

    try:
        if role == "Admin":
            # Dữ liệu của Admin là tĩnh (lấy từ session)
            user_details = user_data
            # Thêm các trường giả (để HTML không bị lỗi nếu dùng chung)
            user_details['bank_name'] = user_data.get('name')
            user_details['bank_code'] = 'N/A (Admin)'
            user_details['contact_person'] = user_data.get('name')
            user_details['email'] = user_data.get('email')
            user_details['account_username'] = user_data.get('email')

        elif role == "BankUser":
            # Dữ liệu của BankUser phải được tải từ CSDL
            bank_id = user_data.get("bank_id")
            with DatabaseConnector(**DATABASE_CONFIG) as db:
                query = "SELECT * FROM Bank WHERE bank_id = %s"
                df_user = db.queryDataset(query, (bank_id,))

                if df_user is not None and not df_user.empty:
                    user_details = df_user.iloc[0].to_dict()
                    user_details['role'] = role  # Thêm role (vì nó không có trong CSDL)
                else:
                    flash("Không thể tải chi tiết thông tin.", "error")
                    user_details = user_data  # Dùng tạm data trong session

        else:
            flash("Vai trò người dùng không xác định.", "error")
            return redirect(url_for("logout"))

    except Exception as e:
        print(f"Lỗi khi tải dữ liệu cho trang Cài đặt: {e}")
        flash(f"Lỗi tải dữ liệu: {e}", "error")
        user_details = user_data  # Dùng tạm

    # Truyền 'user_details' (chứa đầy đủ thông tin) vào template
    return render_template("caidat.html", user_details=user_details)


@app.route("/thongtincanhan")
def thongtincanhan():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("thongtincanhan.html", user=session["user"])


# =============================================================================
# PHẦN 7: ROUTES NGHIỆP VỤ ML CỦA BANKUSER
# =============================================================================

@app.route("/Uquanlidulieu")
def Uquanlidulieu():
    """USER: Trang quản lý dữ liệu (file riêng)"""
    if "user" not in session or session["user"].get("role") != "BankUser":
        return redirect(url_for("login"))
    return render_template("Uquanlidulieu.html")


@app.route("/Uquanlidulieu2")
def Uquanlidulieu2():
    """USER: Trang quản lý dữ liệu 2 (Chỉnh sửa)"""
    if "user" not in session or session["user"].get("role") != "BankUser":
        return redirect(url_for("login"))
    return render_template("Uquanlidulieu2.html")


# (Đảm bảo bạn đã import: request, joblib, os, DatabaseConnector,
# fetch_training_data, train_test_split, và các hàm plot_*_base64)

# (Đảm bảo bạn đã import: request, joblib, os, DatabaseConnector,
# fetch_training_data, train_test_split, và các hàm plot_*_base64)

@app.route("/Uthongke", methods=["POST", "GET"])
def Uthongke():
    """
    (ĐÃ SỬA) USER: Trang thống kê.
    Chỉ tạo biểu đồ NẾU CÓ lựa chọn.
    """
    if "user" not in session or session["user"].get("role") != "BankUser":
        flash("Bạn không có quyền truy cập trang này.", "error")  # Thêm flash message
        return redirect(url_for("login"))

    bank_id = session['user']['bank_id']
    latest_run_data = None
    plot_base64 = None

    # (SỬA LỖI) Lấy lựa chọn. Mặc định là None (không vẽ gì cả).
    selected_chart = request.args.get('chart_type')

    try:
        with DatabaseConnector(**DATABASE_CONFIG) as db:
            # 1. Truy vấn lần chạy MỚI NHẤT
            query = """
            SELECT r.*, m.model_name, d.file_path as dataset_file_path, d.dataset_id
            FROM training_run r
            JOIN ml_model m ON r.model_id = m.model_id
            JOIN dataset d ON r.dataset_id = d.dataset_id
            WHERE r.bank_id = %s AND r.status = 'Completed'
            ORDER BY r.run_date DESC
            LIMIT 1
            """
            df_run = db.queryDataset(query, (bank_id,))

            if df_run is None or df_run.empty:
                flash("Không tìm thấy model đã huấn luyện (Completed) nào.", "warning")
                return render_template("Uthongke.html", run_data=None, selected_chart=selected_chart)

            latest_run_data = df_run.iloc[0].to_dict()
            artifact_path = latest_run_data.get('full_report_path')
            dataset_id = latest_run_data.get('dataset_id')

            if not artifact_path or not os.path.exists(artifact_path):
                raise Exception(f"Không tìm thấy file artifact: {artifact_path}")

            # (MỚI) Chỉ chạy logic nặng nếu user đã chọn biểu đồ
            if selected_chart:
                # 2. Tải model và data
                model_pipeline = joblib.load(artifact_path)
                df_data = fetch_training_data(db, dataset_id)
                if df_data is None:
                    raise Exception(f"Không thể tải lại dataset_id: {dataset_id}")

                # 3. Tái tạo lại X_test, y_test
                features = ['credit_score', 'country', 'gender', 'age', 'tenure', 'balance',
                            'products_number', 'credit_card', 'active_member', 'estimated_salary']
                target = 'churn'
                X = df_data[features]
                y = df_data[target]
                _, X_test, _, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

                print(f"Uthongke: Đang tạo biểu đồ '{selected_chart}'...")

                # 4. Tạo biểu đồ được chọn
                if selected_chart == 'feature_importance':
                    plot_base64 = plot_feature_importance_base64(model_pipeline)
                elif selected_chart == 'confusion_matrix':
                    plot_base64 = plot_confusion_matrix_base64(model_pipeline, X_test, y_test)
                elif selected_chart == 'scatter_eda':
                    plot_base64 = plot_eda_scatter_base64(df_data, 'age', 'balance')
                elif selected_chart == 'box_eda':
                    plot_base64 = plot_eda_box_base64(df_data, 'balance')

    except Exception as e:
        flash(f"Lỗi nghiêm trọng khi tải thống kê: {e}", "error")
        traceback.print_exc()

    return render_template(
        "Uthongke.html",
        run_data=latest_run_data,
        plot_data=plot_base64,
        selected_chart=selected_chart
    )


# (Đảm bảo bạn đã import: request, DatabaseConnector, flash)

# (Đảm bảo bạn đã import: request, DatabaseConnector, flash)

# (Đảm bảo bạn đã import: request, DatabaseConnector, flash)

# (Đảm bảo bạn đã import: request, DatabaseConnector, flash)

# (Đảm bảo bạn đã import: request, DatabaseConnector, flash)

@app.route("/Uphanloaikhachhang")
def Uphanloaikhachhang():
    """
    (SỬA LỖI LỆCH BẢNG) USER: Trang phân loại khách hàng.
    Thêm credit_score vào SELECT và sửa lại logic sắp xếp.
    """
    if "user" not in session or session["user"].get("role") != "BankUser":
        flash("Bạn không có quyền truy cập trang này.", "error")
        return redirect(url_for("login"))

    bank_id = session['user']['bank_id']
    results = []

    search_query = request.args.get('q', '')
    sort_by = request.args.get('sort_by', 'churn_probability')
    sort_order = request.args.get('sort_order', 'DESC')

    # (SỬA) Thêm credit_score (từ bảng c) vào danh sách hợp lệ
    valid_sort_cols = {'churn_probability', 'customer_id', 'credit_score', 'age', 'balance', 'estimated_salary'}
    if sort_by not in valid_sort_cols:
        sort_by = 'churn_probability'
    if sort_order.upper() not in ['ASC', 'DESC']:
        sort_order = 'DESC'

    try:
        with DatabaseConnector(**DATABASE_CONFIG) as db:

            latest_run_id_subquery = f"""
            SELECT p.run_id 
            FROM prediction_result p
            JOIN training_run tr ON p.run_id = tr.run_id
            WHERE tr.bank_id = %s
            ORDER BY p.prediction_date DESC
            LIMIT 1
            """

            params = [bank_id]
            # (SỬA LỖI) Thêm c.credit_score vào câu SELECT
            main_query = f"""
            SELECT 
                c.customer_id, c.credit_score, c.country, c.gender, c.age, c.tenure, 
                c.balance, c.products_number, c.credit_card, c.active_member, 
                c.estimated_salary,
                p.churn_probability,
                p.segment
            FROM prediction_result p
            JOIN Customer c ON p.customer_id = c.customer_id
            WHERE p.run_id = ({latest_run_id_subquery})
            """

            if search_query:
                main_query += " AND c.customer_id LIKE %s"
                params.append(f"%{search_query}%")

            # (SỬA LỖI) Sắp xếp đúng bí danh
            sort_column_alias = ""
            if sort_by in ['customer_id', 'credit_score', 'age', 'balance', 'estimated_salary']:
                sort_column_alias = f"c.{sort_by}"
            else:  # churn_probability
                sort_column_alias = f"p.{sort_by}"

            main_query += f" ORDER BY {sort_column_alias} {sort_order}"

            # 3. Thực thi
            df_results = db.queryDataset(main_query, tuple(params))
            if df_results is not None:
                results = df_results.to_dict('records')

    except Exception as e:
        flash(f"Lỗi khi tải dữ liệu phân loại: {e}", "error")
        traceback.print_exc()

    return render_template(
        "Uphanloaikhachhang.html",
        results=results,
        search_query=search_query,
        sort_by=sort_by,
        sort_order=sort_order
    )


# (Đảm bảo bạn đã import: request, DatabaseConnector, flash)

# (Đảm bảo bạn đã import: request, DatabaseConnector, flash)

@app.route("/Uchienluocgoiytudong")
def Uchienluocgoiytudong():
    """
    (ĐÃ SỬA) USER: Trang chiến lược gợi ý.
    Đếm số lượng khách hàng trong từng nhóm rủi ro từ kết quả dự đoán mới nhất.
    """
    if "user" not in session or session["user"].get("role") != "BankUser":
        return redirect(url_for("login"))

    bank_id = session['user']['bank_id']
    stats = {
        'total': 0,
        'high_risk': 0,
        'medium_risk': 0,
        'low_risk': 0,
        'latest_run_id': None
    }

    try:
        with DatabaseConnector(**DATABASE_CONFIG) as db:
            # 1. Tìm run_id mới nhất từ bảng dự đoán (prediction_result)
            latest_run_id_subquery = f"""
            SELECT p.run_id 
            FROM prediction_result p
            JOIN training_run tr ON p.run_id = tr.run_id
            WHERE tr.bank_id = %s
            ORDER BY p.prediction_date DESC
            LIMIT 1
            """

            # 2. Đếm số lượng khách hàng trong mỗi nhóm rủi ro
            # (Giả định: Cao > 0.7, Trung bình 0.4-0.7, Thấp < 0.4)
            query = f"""
            SELECT 
                COUNT(*) as total_customers,
                SUM(CASE WHEN churn_probability > 0.7 THEN 1 ELSE 0 END) as high_risk,
                SUM(CASE WHEN churn_probability > 0.4 AND churn_probability <= 0.7 THEN 1 ELSE 0 END) as medium_risk,
                SUM(CASE WHEN churn_probability <= 0.4 THEN 1 ELSE 0 END) as low_risk
            FROM prediction_result
            WHERE run_id = ({latest_run_id_subquery})
            """
            df_stats = db.queryDataset(query, (bank_id,))

            if df_stats is not None and not df_stats.empty:
                # Dùng .get(key, 0) để tránh lỗi nếu SUM() trả về None
                stats['total'] = int(df_stats.iloc[0].get('total_customers', 0) or 0)
                stats['high_risk'] = int(df_stats.iloc[0].get('high_risk', 0) or 0)
                stats['medium_risk'] = int(df_stats.iloc[0].get('medium_risk', 0) or 0)
                stats['low_risk'] = int(df_stats.iloc[0].get('low_risk', 0) or 0)

            # Lấy run_id để hiển thị
            df_run_id = db.queryDataset(latest_run_id_subquery, (bank_id,))
            if df_run_id is not None and not df_run_id.empty:
                stats['latest_run_id'] = int(df_run_id.iloc[0]['run_id'])

    except Exception as e:
        flash(f"Lỗi khi tải thống kê gợi ý: {e}", "error")

    return render_template("Uchienluocgoiytudong.html", stats=stats)


# (Đảm bảo bạn đã import: request, DatabaseConnector, flash)

# (Đảm bảo bạn đã import: request, DatabaseConnector, flash)

@app.route("/Utoiuuhoachiendich")
def Utoiuuhoachiendich():
    """
    (SỬA) USER: Trang tối ưu chiến dịch.
    Hiển thị 2 danh sách:
    1. Các lần train cũ (all_runs)
    2. Các dataset CÓ SẴN (để train lại)
    """
    if "user" not in session or session["user"].get("role") != "BankUser":
        return redirect(url_for("login"))

    bank_id = session['user']['bank_id']
    all_runs = []
    available_datasets = []  # (MỚI)

    try:
        with DatabaseConnector(**DATABASE_CONFIG) as db:
            # 1. (Giữ nguyên) Lấy tất cả các lần train 'Completed'
            query_runs = """
            SELECT r.run_id, r.run_date, r.performance_metric, d.file_path,
                   LAG(r.performance_metric, 1, 0) OVER (ORDER BY r.run_date) as previous_metric
            FROM training_run r
            JOIN dataset d ON r.dataset_id = d.dataset_id
            WHERE r.bank_id = %s AND r.status = 'Completed'
            ORDER BY r.run_date DESC
            """
            df_runs = db.queryDataset(query_runs, (bank_id,))
            if df_runs is not None:
                all_runs = df_runs.to_dict('records')
                # (Tính toán % thay đổi)
                for run in all_runs:
                    prev_metric = float(run['previous_metric'])
                    curr_metric = float(run['performance_metric'])
                    if prev_metric > 0:
                        run['change_pct'] = ((curr_metric - prev_metric) / prev_metric) * 100
                    else:
                        run['change_pct'] = 0

                        # 2. (MỚI) Lấy tất cả dataset có sẵn (để train)
            query_datasets = """
            SELECT dataset_id, file_path, upload_date FROM dataset
            WHERE bank_id = %s
            ORDER BY upload_date DESC
            """
            df_datasets = db.queryDataset(query_datasets, (bank_id,))
            if df_datasets is not None:
                available_datasets = df_datasets.to_dict('records')

    except Exception as e:
        flash(f"Lỗi khi tải dữ liệu chiến dịch: {e}", "error")

    return render_template(
        "Utoiuuhoachiendich.html",
        all_runs=all_runs,
        available_datasets=available_datasets  # (MỚI)
    )


# =============================================================================
# PHẦN 8: ACTION ROUTES (Upload, Update)
# =============================================================================

@app.route("/update_user", methods=["POST"])
def update_user():
    """Cập nhật thông tin User (Bảng Bank)."""
    if "user" not in session:
        return redirect(url_for("login"))
    flash("Chức năng cập nhật đang được xây dựng.", "info")
    return redirect(url_for("thongtincanhan"))


@app.route("/upload_dataset", methods=["POST"])
# (Đảm bảo bạn đã import json, os, datetime, DatabaseConnector,
# fetch_training_data, train_churn_model, và save_model_artifact_and_db_record)

@app.route("/upload_dataset", methods=["POST"])
# (Đảm bảo bạn đã import json, os, datetime, DatabaseConnector,
# fetch_training_data, train_churn_model, và save_model_artifact_and_db_record)

@app.route("/upload_dataset", methods=["POST"])
# (Đảm bảo bạn đã import json, os, datetime, DatabaseConnector,
# fetch_training_data, train_churn_model, và save_model_artifact_and_db_record)

# (Đảm bảo bạn đã import json, os, datetime, DatabaseConnector,
# fetch_training_data, train_churn_model, và save_model_artifact_and_db_record)

@app.route("/upload_dataset", methods=["POST"])
# (Nằm trong app.py)
@app.route("/upload_dataset", methods=["POST"])
# (Đảm bảo bạn đã import json, os, datetime, DatabaseConnector,
# train_churn_model, save_model_artifact_and_db_record, và pandas as pd)

@app.route("/upload_dataset", methods=["POST"])
# (Đảm bảo bạn đã import json, os, datetime, DatabaseConnector,
# train_churn_model, save_model_artifact_and_db_record, và pandas as pd)

@app.route("/upload_dataset", methods=["POST"])
# (Đảm bảo bạn đã import json, os, datetime, DatabaseConnector,
# joblib, pandas as pd, và các thư viện sklearn/xgboost)

@app.route("/upload_dataset", methods=["POST"])
# (Đảm bảo bạn đã import json, os, datetime, DatabaseConnector,
# joblib, pandas as pd, và các thư viện sklearn/xgboost)

# (Đảm bảo bạn đã import: json, os, datetime, DatabaseConnector,
# joblib, pandas as pd, và các thư viện sklearn/xgboost)

# (Đảm bảo bạn đã import json, os, datetime, DatabaseConnector,
# joblib, pandas as pd, và các thư viện sklearn/xgboost)

# (Đảm bảo bạn đã import json, os, datetime, DatabaseConnector,
# joblib, pandas as pd, và các thư viện sklearn/xgboost)

# (Đảm bảo bạn đã import json, os, datetime, DatabaseConnector,
# joblib, pandas as pd, và các thư viện sklearn/xgboost)

@app.route("/upload_dataset", methods=["POST"])
def upload_dataset():
    """
    (SỬA LỖI 11 vs 12 columns)
    Route này là DỰ ĐOÁN (PREDICTION).
    Header sẽ được đặt là 11 CỘT (không có churn).
    """
    if "user" not in session or session['user']['role'] != 'BankUser':
        return jsonify({"status": "error", "message": "Không có quyền truy cập"}), 403

    dataset_id = None

    try:
        json_data = request.form.get('dataset_content')
        filename = request.form.get('dataset_filename')
        if not json_data:
            return jsonify({"status": "error", "message": "Thiếu dữ liệu"}), 400

        bank_id = session['user']['bank_id']
        data = json.loads(json_data)

        # 1. (SỬA LỖI) Tải dữ liệu (11 cột) vào DataFrame
        # Header PHẢI KHỚP 11 cột (KHÔNG CÓ CHURN)
        header = ["customer_id", "credit_score", "country", "gender", "age", "tenure", "balance",
                  "products_number", "credit_card", "active_member", "estimated_salary"]  # <-- SỬA Ở ĐÂY (11 cột)

        df_predict = pd.DataFrame(data, columns=header)

        # 2. Ép kiểu dữ liệu (Giữ nguyên)
        df_predict['customer_id'] = pd.to_numeric(df_predict['customer_id'], errors='coerce')
        df_predict = df_predict.dropna(subset=['customer_id'])
        df_predict['customer_id'] = df_predict['customer_id'].astype(int).astype(str)
        numeric_cols = ['credit_score', 'age', 'tenure', 'products_number', 'credit_card', 'active_member']
        float_cols = ['balance', 'estimated_salary']
        for col in numeric_cols:
            df_predict[col] = pd.to_numeric(df_predict[col], errors='coerce').fillna(0).astype(int)
        for col in float_cols:
            df_predict[col] = pd.to_numeric(df_predict[col], errors='coerce').fillna(0).astype(float)

        # 3. Tải Model MỚI NHẤT
        latest_run_id = None
        model_pipeline = None

        query_run = """
        SELECT run_id, full_report_path FROM training_run
        WHERE bank_id = %s AND status = 'Completed'
        ORDER BY run_date DESC
        LIMIT 1
        """
        with DatabaseConnector(**DATABASE_CONFIG) as db_model:
            df_run = db_model.queryDataset(query_run, (bank_id,))

        if df_run is None or df_run.empty:
            return jsonify({"status": "error", "message": "Không tìm thấy model đã huấn luyện cho ngân hàng này."}), 404

        latest_run_id = int(df_run.iloc[0]['run_id'])
        artifact_path = df_run.iloc[0]['full_report_path']

        if not artifact_path or not os.path.exists(artifact_path):
            return jsonify({"status": "error", "message": f"Không tìm thấy file model: {artifact_path}"}), 404

        print(f"Đang tải model từ run_id: {latest_run_id} (path: {artifact_path})")
        model_pipeline = joblib.load(artifact_path)

        # 4. CHẠY DỰ ĐOÁN
        print("Bắt đầu dự đoán trên dữ liệu mới...")

        # (SỬA LỖI) features_for_prediction bây giờ là 10 cột,
        # Bỏ 'customer_id'
        features_for_prediction = df_predict.drop(columns=['customer_id'])

        probabilities = model_pipeline.predict_proba(features_for_prediction)[:, 1]
        df_predict['churn'] = model_pipeline.predict(features_for_prediction)

        print(f"Dự đoán hoàn tất cho {len(df_predict)} khách hàng.")

        # 5. Lưu File (bây giờ đã có 12 cột, bao gồm 'churn' dự đoán)
        save_path = os.path.join(data_dir, filename)
        df_predict.to_csv(save_path, index=False)
        db_file_path = os.path.join('data', filename).replace("\\", "/")

        # 6. Mở kết nối CSDL (Để LƯU)
        with DatabaseConnector(**DATABASE_CONFIG) as db:

            # 6a. Lưu vào Bảng Dataset
            query_dataset = "INSERT INTO Dataset (bank_id, upload_date, file_path, status) VALUES (%s, %s, %s, %s)"
            dataset_id = db.execute_query(query_dataset, (bank_id, datetime.now(), db_file_path, 'Processed'),
                                          fetch_last_id=True)

            if not dataset_id:
                raise Exception("Không thể tạo bản ghi Dataset.")

            # 6b. Chèn/Cập nhật Bảng Customer
            print(f"Đang chèn/cập nhật {len(df_predict)} khách hàng cho dataset_id {dataset_id}...")
            customer_data_to_insert = []
            for _, row in df_predict.iterrows():
                new_row_tuple = (
                    str(row['customer_id']), dataset_id, int(row['credit_score']),
                    str(row['country']), str(row['gender']), int(row['age']),
                    int(row['tenure']), float(row['balance']), int(row['products_number']),
                    int(row['credit_card']), int(row['active_member']),
                    float(row['estimated_salary']), int(row['churn'])  # Dùng cột churn đã dự đoán
                )
                customer_data_to_insert.append(new_row_tuple)

            sql_insert_customer = """
            INSERT INTO Customer 
                (customer_id, dataset_id, credit_score, country, gender, age, tenure, 
                balance, products_number, credit_card, active_member, 
                estimated_salary, churn)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                dataset_id = VALUES(dataset_id), credit_score = VALUES(credit_score),
                country = VALUES(country), gender = VALUES(gender), age = VALUES(age),
                tenure = VALUES(tenure), balance = VALUES(balance),
                products_number = VALUES(products_number), credit_card = VALUES(credit_card),
                active_member = VALUES(active_member), estimated_salary = VALUES(estimated_salary),
                churn = VALUES(churn)
            """
            cursor = db.conn.cursor()
            cursor.executemany(sql_insert_customer, customer_data_to_insert)
            db.conn.commit()
            print(f"Chèn/Cập nhật {len(customer_data_to_insert)} khách hàng thành công.")

            # 6c. Chuẩn bị và Lưu vào 'prediction_result'
            results_to_insert = []
            for idx, (index, row) in enumerate(df_predict.iterrows()):
                results_to_insert.append((
                    str(row['customer_id']), latest_run_id, float(probabilities[idx]),
                    int(row['credit_score']), float(row['estimated_salary']),
                    float(row['balance']), datetime.now()
                ))

            sql_delete = "DELETE FROM prediction_result WHERE run_id = %s"
            cursor.execute(sql_delete, (latest_run_id,))

            sql_insert_pred = """
            INSERT INTO prediction_result 
                (customer_id, run_id, churn_probability, credit_score, salary, balance, prediction_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.executemany(sql_insert_pred, results_to_insert)
            db.conn.commit()
            cursor.close()
            print(f"Đã lưu {len(results_to_insert)} kết quả dự đoán vào CSDL.")

        return jsonify({"status": "success"})

    except Exception as e:
        print(f"LỖI trong /upload_dataset (Prediction): {e}")
        traceback.print_exc()

        if dataset_id:
            try:
                with DatabaseConnector(**DATABASE_CONFIG) as db:
                    print(f"Đang rollback... Xóa dataset_id {dataset_id}")
                    db.execute_query("DELETE FROM Dataset WHERE dataset_id = %s", (dataset_id,))
            except Exception as e_del:
                print(f"Lỗi khi đang rollback: {e_del}")

        return jsonify({"status": "error", "message": f"Lỗi server: {e}"}), 500


# (Đảm bảo bạn đã import: request, DatabaseConnector, flash,
# fetch_training_data, train_churn_model, save_model_artifact_and_db_record)

@app.route("/retrain_model", methods=["POST"])
def retrain_model():
    """
    (MỚI) Route này xử lý logic HUẤN LUYỆN LẠI.
    Nó lấy 1 model_id (thuật toán) và 1 dataset_id (dữ liệu CÓ CHURN)
    và tạo ra một 'training_run' mới.
    """
    if "user" not in session or session['user']['role'] != 'BankUser':
        flash("Bạn không có quyền truy cập.", "error")
        return redirect(url_for("Utoiuuhoachiendich"))

    try:
        # 1. Lấy lựa chọn của User từ form
        # (Giả sử model_id = 3 (XGBoost) như chúng ta đã sửa)
        model_id_to_use = 3

        # Lấy dataset_id mà user chọn (ví dụ: dataset_id = 2)
        dataset_id_to_train = request.form.get('dataset_id')
        bank_id = session['user']['bank_id']

        if not dataset_id_to_train:
            flash("Lỗi: Bạn chưa chọn dataset để huấn luyện.", "error")
            return redirect(url_for("Utoiuuhoachiendich"))

        # 2. Tải dữ liệu huấn luyện (PHẢI CÓ CHURN)
        print(f"Bắt đầu huấn luyện lại cho dataset_id: {dataset_id_to_train}")
        df_train = None
        with DatabaseConnector(**DATABASE_CONFIG) as db:
            df_train = fetch_training_data(db, dataset_id_to_train)

        if df_train is None or df_train.empty:
            flash(f"Lỗi: Không tìm thấy dữ liệu (có churn) cho dataset_id {dataset_id_to_train}.", "error")
            return redirect(url_for("Utoiuuhoachiendich"))

        # 3. Huấn luyện model (Tốn thời gian)
        model_pipeline, f1, auc, _, _ = train_churn_model(df_train)

        # 4. Lưu artifact và bản ghi training_run
        if model_pipeline:
            run_id = save_model_artifact_and_db_record(bank_id, dataset_id_to_train, model_pipeline, f1, auc)
            flash(f"Huấn luyện thành công! Đã tạo Run ID mới: {run_id}", "success")
        else:
            raise Exception("Huấn luyện thất bại, model_pipeline là None.")

    except Exception as e:
        print(f"LỖI trong /retrain_model: {e}")
        traceback.print_exc()
        flash(f"Lỗi server: {e}", "error")

    return redirect(url_for("Utoiuuhoachiendich"))


@app.route("/get_llm_suggestion", methods=["POST"])
def get_llm_suggestion():
    """
    (MỚI) API Endpoint để lấy gợi ý từ LLM.
    Được gọi bằng JavaScript từ trang Uchienluocgoiytudong.
    """
    if "user" not in session or session['user']['role'] != 'BankUser':
        return jsonify({"status": "error", "message": "Không có quyền truy cập"}), 403

    bank_id = session['user']['bank_id']
    bank_name = session['user'].get('name', 'Ngân hàng')  # Lấy tên ngân hàng để cá nhân hóa

    # Lấy tên nhóm (vd: "high_risk") từ request JSON
    segment_key = request.json.get('segment_key')

    if not segment_key:
        return jsonify({"status": "error", "message": "Thiếu 'segment_key'"}), 400

    # 1. Định nghĩa các ngưỡng và tên
    segment_map = {
        "high_risk": {
            "condition": "p.churn_probability > 0.7",
            "name_vi": "Khách hàng Nguy cơ Rời bỏ Cao"
        },
        "medium_risk": {
            "condition": "p.churn_probability > 0.4 AND p.churn_probability <= 0.7",
            "name_vi": "Khách hàng Nguy cơ Trung bình"
        },
        "low_risk": {
            "condition": "p.churn_probability <= 0.4",
            "name_vi": "Khách hàng An toàn / Nguy cơ Thấp"
        }
    }

    segment_info = segment_map.get(segment_key)
    if not segment_info:
        return jsonify({"status": "error", "message": "Segment không hợp lệ"}), 400

    query_condition = segment_info["condition"]
    segment_name_vietnamese = segment_info["name_vi"]

    segment_stats = {}

    try:
        with DatabaseConnector(**DATABASE_CONFIG) as db:
            # 2. Lấy run_id mới nhất (giống logic ở trang Uchienluocgoiytudong)
            latest_run_id_subquery = f"""
            SELECT p.run_id 
            FROM prediction_result p
            JOIN training_run tr ON p.run_id = tr.run_id
            WHERE tr.bank_id = %s
            ORDER BY p.prediction_date DESC
            LIMIT 1
            """

            # 3. Lấy thông tin chi tiết cho nhóm này
            # (QUAN TRỌNG: Phải JOIN với Customer để lấy 'age')
            query_stats = f"""
            SELECT 
                COUNT(*) as count,
                AVG(p.churn_probability) * 100 as avg_churn,
                AVG(p.balance) as avg_balance,
                AVG(p.credit_score) as avg_credit_score,
                AVG(c.age) as avg_age
            FROM prediction_result p
            JOIN Customer c ON p.customer_id = c.customer_id
            WHERE p.run_id = ({latest_run_id_subquery})
            AND ({query_condition})
            """

            df_stats = db.queryDataset(query_stats, (bank_id,))

            if df_stats is None or df_stats.empty or df_stats.iloc[0]['count'] == 0:
                return jsonify({"status": "error", "message": "Không có dữ liệu cho nhóm này."}), 404

            # Chuyển đổi sang dict và xử lý None (nếu có)
            segment_stats = df_stats.iloc[0].to_dict()
            segment_stats = {k: (v if v is not None and not pd.isna(v) else 0) for k, v in segment_stats.items()}


    except Exception as e:
        print(f"Lỗi CSDL khi lấy stats cho LLM: {e}")
        return jsonify({"status": "error", "message": f"Lỗi CSDL: {e}"}), 500

    # 4. Gọi hàm OpenAI (đã tạo ở Bước 3)
    suggestion_markdown = get_strategy_from_openai(
        segment_name_vietnamese,
        segment_stats,
        bank_name
    )

    # 5. Trả về kết quả (dạng Markdown)
    return jsonify({
        "status": "success",
        "segment_name": segment_name_vietnamese,
        "stats": segment_stats,  # Gửi kèm stats nếu frontend muốn hiển thị
        "suggestion_markdown": suggestion_markdown  # Đây là nội dung AI tạo ra
    })

# =============================================================================
# PHẦN 9: RUN APP
# =============================================================================
if __name__ == "__main__":
    app.run(debug=True)