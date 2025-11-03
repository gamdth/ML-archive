import mysql.connector
import pandas as pd
import traceback
import joblib
import os
import datetime
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import f1_score, roc_auc_score, classification_report
import xgboost as xgb

# =============================================================================
# CẤU HÌNH & HẰNG SỐ (GIỮ NGUYÊN)
# =============================================================================

DATABASE_CONFIG = {
    "server": "localhost",
    "port": 3306,
    "database": "bank",
    "user": "root",
    "password": "@Obama123"
}
# Giả định Bank_ID này là Ngân hàng đang thực hiện tái huấn luyện
BANK_ID_TRAINING = 1
# Giả định Model_ID gốc được dùng để retrain (ví dụ: XGBoost) là 1
# Trong ứng dụng thực tế, User sẽ chọn model_id này.
BASE_MODEL_ID = 1


# =============================================================================
# PHẦN 1: CLASS KẾT NỐI VÀ THAO TÁC CSDL (GIỮ NGUYÊN)
# =============================================================================

class DatabaseConnector:
    def __init__(self, config):
        self.config = config
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
            if not self.connect():
                return None
        try:
            df = pd.read_sql(sql, self.conn, params=params)
            return df
        except Exception as e:
            print(f"Lỗi khi truy vấn queryDataset: {e}")
            traceback.print_exc()
            return None

    def execute_non_query(self, sql, params=None):
        if not self.conn or not self.conn.is_connected():
            if not self.connect():
                return False

        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, params)
            self.conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"Lỗi khi thực thi non-query: {e}")
            self.conn.rollback()
            traceback.print_exc()
            return False
        finally:
            if cursor:
                cursor.close()

    def __enter__(self):
        if self.connect():
            return self
        else:
            raise IOError("Không thể kết nối CSDL")

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disConnect()


# =============================================================================
# PHẦN 2: CÁC HÀM XỬ LÝ DỮ LIỆU VÀ HUẤN LUYỆN (GIỮ NGUYÊN)
# =============================================================================

def fetch_training_data(db_connector, dataset_id_to_train):
    # ... (Giữ nguyên hàm này)
    print(f"Đang tải dữ liệu huấn luyện từ CSDL cho dataset_id = {dataset_id_to_train}...")
    sql_query = """
    SELECT 
        credit_score, country, gender, age, tenure, balance, 
        products_number, credit_card, active_member, estimated_salary, 
        churn 
    FROM customer
    WHERE dataset_id = %s 
    """
    params = (dataset_id_to_train,)
    df = db_connector.queryDataset(sql_query, params)

    if df is None or df.empty:
        print(f"Lỗi: Không tìm thấy dữ liệu cho dataset_id = {dataset_id_to_train}.")
        return None
    print(f"Tải thành công {len(df)} dòng dữ liệu.")
    return df


def train_churn_model(df):
    # ... (Giữ nguyên hàm này, trả về full_pipeline, f1, auc)
    print("\nBắt đầu quá trình huấn luyện mô hình...")

    features = ['credit_score', 'country', 'gender', 'age', 'tenure', 'balance',
                'products_number', 'credit_card', 'active_member', 'estimated_salary']
    target = 'churn'
    X = df[features]
    y = df[target]
    numeric_features = ['credit_score', 'age', 'tenure', 'balance', 'products_number', 'estimated_salary']
    categorical_features = ['country', 'gender']

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), numeric_features),
            ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
        ],
        remainder='passthrough'
    )
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    neg_count = y_train.value_counts()[0]
    pos_count = y_train.value_counts()[1]
    scale_pos_weight_val = neg_count / pos_count

    model = xgb.XGBClassifier(
        use_label_encoder=False,
        eval_metric='logloss',
        random_state=42,
        scale_pos_weight=scale_pos_weight_val
    )
    full_pipeline = Pipeline(steps=[('preprocessor', preprocessor),
                                    ('model', model)])

    print("Đang huấn luyện (fitting) pipeline...")
    full_pipeline.fit(X_train, y_train)
    print("Huấn luyện hoàn tất!")

    y_pred = full_pipeline.predict(X_test)
    f1 = f1_score(y_test, y_pred)
    auc = roc_auc_score(y_test, full_pipeline.predict_proba(X_test)[:, 1])
    full_report = classification_report(y_test, y_pred)

    print("\n--- ĐÁNH GIÁ MÔ HÌNH ---")
    print(f"F1-Score (trên tập test): {f1:.4f}")
    print(f"AUC Score (trên tập test): {auc:.4f}")
    print(full_report)

    return full_pipeline, f1, auc


# =============================================================================
# PHẦN 3: LƯU METADATA VÀO BẢNG training_run (ĐÃ SỬA)
# =============================================================================

def get_next_iteration_number(db_connector, bank_id):
    """Truy vấn CSDL để lấy số iteration_number lớn nhất + 1 cho bank_id này."""
    sql = """
    SELECT MAX(iteration_number) 
    FROM training_run 
    WHERE bank_id = %s
    """
    df = db_connector.queryDataset(sql, (bank_id,))

    if df is not None and not df.empty and df.iloc[0, 0] is not None:
        # Nếu đã có bản ghi, lấy MAX + 1
        return int(df.iloc[0, 0]) + 1
    else:
        # Nếu chưa có bản ghi, bắt đầu từ 1
        return 1


def save_training_run_metadata(db_connector, bank_id, dataset_id, model_artifact_path, f1_score):
    """
    Lưu metadata của phiên huấn luyện vào bảng training_run.
    """
    print("\nĐang chuẩn bị lưu metadata vào bảng training_run...")

    # 1. Tính toán iteration_number
    next_iteration = get_next_iteration_number(db_connector, bank_id)
    print(f"Lần huấn luyện thứ: {next_iteration} cho Bank ID: {bank_id}")

    # 2. Chuẩn bị câu lệnh INSERT
    # Lưu ý: full_report_path được dùng để lưu đường dẫn file model .joblib
    # Cột is_best_model có thể để NULL/FALSE, vì ta đã thống nhất không dùng.
    sql_insert = """
    INSERT INTO training_run 
        (bank_id, dataset_id, model_id, run_date, iteration_number, 
         performance_metric, full_report_path, status)
    VALUES 
        (%s, %s, %s, NOW(), %s, %s, %s, 'Completed')
    """

    params = (
        bank_id,
        dataset_id,
        BASE_MODEL_ID,  # model_id gốc (ví dụ: XGBoost)
        next_iteration,
        f1_score,
        model_artifact_path
    )

    new_run_id = db_connector.execute_non_query(sql_insert, params)

    if new_run_id:
        print(f"Lưu metadata Training Run thành công! Run ID: {new_run_id}")
        return new_run_id
    else:
        print("LỖI: Không thể lưu metadata Training Run.")
        return None


# =============================================================================
# PHẦN 4: HÀM CHẠY CHÍNH (MAIN EXECUTION)
# =============================================================================

if __name__ == "__main__":

    DATASET_ID_TO_TRAIN = 2
    SAVE_DIRECTORY = "saved_models"
    NEW_FILE_NAME = f"model_churn_bank_{BANK_ID_TRAINING}_dataset_{DATASET_ID_TO_TRAIN}.joblib"
    model_save_path = os.path.join(SAVE_DIRECTORY, NEW_FILE_NAME)

    try:
        # 1. KẾT NỐI VÀ LẤY DỮ LIỆU
        with DatabaseConnector(DATABASE_CONFIG) as db:
            print(f"Kết nối CSDL '{DATABASE_CONFIG['database']}' thành công.")
            customer_df = fetch_training_data(db, DATASET_ID_TO_TRAIN)

        # 2. HUẤN LUYỆN MODEL
        if customer_df is not None:
            trained_model, final_f1_score, final_auc_score = train_churn_model(customer_df)
        else:
            print("Không có dữ liệu để huấn luyện. Dừng chương trình.")
            exit()

        # 3. LƯU FILE VÀ METADATA
        # --- 3A. LƯU FILE (.joblib) ---
        os.makedirs(SAVE_DIRECTORY, exist_ok=True)
        joblib.dump(trained_model, model_save_path)
        print(f"\nĐã lưu file mô hình đã huấn luyện vào: '{model_save_path}'")

        # --- 3B. LƯU METADATA VÀO CSDL (training_run) ---
        # Cần kết nối CSDL lần 2 để đảm bảo kết nối ổn định sau quá trình tính toán nặng
        with DatabaseConnector(DATABASE_CONFIG) as db_meta:
            save_training_run_metadata(
                db_meta,
                bank_id=BANK_ID_TRAINING,
                dataset_id=DATASET_ID_TO_TRAIN,
                model_artifact_path=model_save_path,
                f1_score=final_f1_score
            )

    except IOError as e:
        print(f"LỖI KẾT NỐI DATABASE (IOError): {e}")
    except Exception as e:
        print(f"LỖI CHUNG XẢY RA: {e}")
        traceback.print_exc()