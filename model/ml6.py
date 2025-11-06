import os
import mysql.connector
import pandas as pd
import traceback
import joblib  # Chúng ta dùng joblib thay vì pickle (tốt hơn cho sklearn)
import numpy as np
from datetime import datetime
from sklearn.preprocessing import FunctionTransformer, StandardScaler, OneHotEncoder
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import f1_score, roc_auc_score, classification_report
import xgboost as xgb


# =============================================================================
# PHẦN 1: CLASS KẾT NỐI (Giữ nguyên)
# =============================================================================
class DatabaseConnector:
    def __init__(self,
                 server="localhost",
                 port=3306,
                 database="bank",
                 username="root",
                 password="@Obama123"):
        self.config = {
            'host': server,
            'port': port,
            'database': database,
            'user': username,
            'password': password
        }
        self.conn = None

    def connect(self):
        try:
            self.conn = mysql.connector.connect(**self.config)
            return self.conn
        except mysql.connector.Error as e:
            print(f"LỖI KẾT NỐI MYSQL: {e}")
            traceback.print_exc()
            self.conn = None
            return None

    def disConnect(self):
        if self.conn and self.conn.is_connected():
            self.conn.close()

    def queryDataset(self, sql, params=None):
        if not self.conn or not self.conn.is_connected():
            print("Lỗi: Chưa kết nối. Đang thử kết nối lại...")
            if not self.connect():
                print("Lỗi: Không thể kết nối lại.")
                return None
        try:
            # Cảnh báo UserWarning là bình thường, pandas ưu tiên SQLAlchemy
            df = pd.read_sql(sql, self.conn, params=params)
            return df
        except Exception as e:
            print(f"Lỗi khi truy vấn queryDataset: {e}")
            traceback.print_exc()
            return None

    def execute_query(self, sql, params=None):
        if not self.conn or not self.conn.is_connected():
            print("Lỗi: Chưa kết nối. Đang thử kết nối lại...")
            if not self.connect():
                print("Lỗi: Không thể kết nối lại.")
                return False
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, params)
            self.conn.commit()
            cursor.close()
            return True
        except mysql.connector.Error as e:
            print(f"Lỗi khi thực thi execute_query: {e}")
            self.conn.rollback()
            return False
        except Exception as e:
            print(f"Lỗi không xác định trong execute_query: {e}")
            return False

    def __enter__(self):
        if self.connect():
            return self
        else:
            raise IOError("Không thể kết nối CSDL")

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disConnect()


# =============================================================================
# PHẦN 2: CÁC HÀM XỬ LÝ (Giữ nguyên)
# =============================================================================

def fetch_training_data(db_connector, dataset_id_to_train):
    """ Tải dữ liệu (Giữ nguyên) """
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


# --- Hàm Feature Engineering (Giữ nguyên) ---
def add_custom_features(df_in):
    df = df_in.copy()
    epsilon = 1e-6
    print("...Đang tạo các đặc trưng mới (features)...")
    df['Balance_per_Salary'] = df['balance'] / (df['estimated_salary'] + epsilon)
    df['CreditScore_per_Tenure'] = df['credit_score'] / (df['tenure'] + 1.0)
    df['Balance_per_Age'] = df['balance'] / (df['age'] + epsilon)
    df['Active_HasCard'] = df['active_member'] * df['credit_card']
    df['Products_per_Tenure'] = df['products_number'] / (df['tenure'] + 1.0)
    return df


# --- Hàm Huấn luyện (Giữ nguyên) ---
def train_churn_model(df):
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
    print(f"Tính toán scale_pos_weight cho dữ liệu mất cân bằng: {scale_pos_weight:.2f}")

    model = xgb.XGBClassifier(use_label_encoder=False,
                              eval_metric='logloss',
                              random_state=42)

    full_pipeline = Pipeline(steps=[
        ('feature_engineering', FunctionTransformer(add_custom_features, validate=False)),
        ('preprocessor', preprocessor),
        ('model', model)
    ])

    param_grid = {
        'model__max_depth': [6, 7, 8],
        'model__learning_rate': [0.08, 0.1, 0.12],
        'model__n_estimators': [100, 125, 150],
        'model__scale_pos_weight': [scale_pos_weight]
    }

    grid_search = GridSearchCV(
        estimator=full_pipeline,
        param_grid=param_grid,
        scoring='f1',
        cv=5,
        n_jobs=-1,
        verbose=2
    )

    print("Đang chạy GridSearchCV (với Feature Engineering)...")
    grid_search.fit(X_train, y_train)

    print("\n--- KẾT QUẢ TINH CHỈNH (với Feature Engineering) ---")
    print(f"Cấu hình tham số tốt nhất: {grid_search.best_params_}")
    print(f"F1-Score tốt nhất (trên tập CV): {grid_search.best_score_:.4f}")

    best_model_pipeline = grid_search.best_estimator_

    y_pred = best_model_pipeline.predict(X_test)
    f1 = f1_score(y_test, y_pred)
    auc = roc_auc_score(y_test, best_model_pipeline.predict_proba(X_test)[:, 1])

    print("\n--- ĐÁNH GIÁ MÔ HÌNH TỐT NHẤT (trên tập test) ---")
    print(f"F1-Score (trên tập test): {f1:.4f}")
    print(f"AUC Score (trên tập test): {auc:.4f}")
    print("\nBáo cáo phân loại chi tiết:")
    print(classification_report(y_test, y_pred))

    return best_model_pipeline, f1, auc


# --- Hàm Lưu CSDL (Giữ nguyên) ---
def save_training_run_metadata(db_connector, bank_id, dataset_id, f1_score, auc_score, model_artifact_path):
    print(f"\nĐang chuẩn bị lưu metadata vào bảng training_run...")
    try:
        query_version = """
        SELECT COALESCE(MAX(iteration_number), 0) + 1 
        FROM training_run 
        WHERE bank_id = %s AND dataset_id = %s
        """
        params_version = (bank_id, dataset_id)
        df_version = db_connector.queryDataset(query_version, params_version)

        if df_version is None or df_version.empty:
            print("Lỗi khi lấy iteration_number, đặt mặc định là 1")
            next_version = 1
        else:
            next_version = int(df_version.iloc[0, 0])

        print(f"Lần huấn luyện thứ: {next_version} cho Bank ID: {bank_id}, Dataset ID: {dataset_id}")

        sql_insert = """
        INSERT INTO training_run 
            (bank_id, dataset_id, model_id, run_date, iteration_number, 
             performance_metric, full_report_path, is_best_model, status)
        VALUES 
            (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params_insert = (
            bank_id, dataset_id, 1, datetime.now(), next_version,
            float(f1_score), model_artifact_path, 1, 'Completed'
        )

        if db_connector.execute_query(sql_insert, params_insert):
            print(f"Lưu metadata Training Run thành công!")
        else:
            print("LỖI khi lưu metadata Training Run.")
    except Exception as e:
        print(f"LỖI nghiêm trọng khi lưu metadata: {e}")
        traceback.print_exc()


# =============================================================================
# PHẦN 3: HÀM CHẠY CHÍNH (Đã Nâng Cấp)
# =============================================================================

if __name__ == "__main__":

    # 1. CẤU HÌNH (Giữ nguyên)
    db_config = {
        "server": "localhost",
        "port": 3306,
        "database": "bank",
        "username": "root",
        "password": "@Obama123"
    }
    BANK_ID = 1
    DATASET_ID_TO_TRAIN = 2

    # 2. ĐỊNH NGHĨA ĐƯỜNG DẪN LƯU (Giữ nguyên)
    SAVE_DIRECTORY = "saved_models"
    NEW_FILE_NAME = f"model_churn_bank_{BANK_ID}_dataset_{DATASET_ID_TO_TRAIN}.joblib"
    model_save_path = os.path.join(SAVE_DIRECTORY, NEW_FILE_NAME)

    trained_model = None
    final_f1_score = 0.0
    final_auc_score = 0.0

    try:
        # 3. KẾT NỐI VÀ LẤY DỮ LIỆU (Giữ nguyên)
        with DatabaseConnector(**db_config) as db:
            print(f"Kết nối CSDL '{db_config['database']}' thành công.")
            customer_df = fetch_training_data(db, DATASET_ID_TO_TRAIN)

            # 4. HUẤN LUYỆN MODEL (Giữ nguyên)
            if customer_df is not None:
                trained_model, final_f1_score, final_auc_score = train_churn_model(customer_df)
            else:
                print("Không có dữ liệu để huấn luyện. Dừng chương trình.")

            # 5. LƯU MODEL VÀ METADATA (Giữ nguyên)
            if trained_model is not None:
                os.makedirs(SAVE_DIRECTORY, exist_ok=True)
                joblib.dump(trained_model, model_save_path)
                print(f"\nĐã lưu file mô hình đã huấn luyện vào: '{model_save_path}'")

                save_training_run_metadata(
                    db_connector=db,
                    bank_id=BANK_ID,
                    dataset_id=DATASET_ID_TO_TRAIN,
                    f1_score=final_f1_score,
                    auc_score=final_auc_score,
                    model_artifact_path=model_save_path
                )

            else:
                print("Huấn luyện thất bại, không có mô hình để lưu.")

    except IOError as e:
        print(f"LỖI KẾT NỐI DATABASE (IOError): {e}")
    except Exception as e:
        print(f"LỖI CHUNG XẢY RA: {e}")
        traceback.print_exc()

    # -------------------------------------------------------------------------
    # (MỚI) PHẦN 6: TẢI VÀ KIỂM TRA MÔ HÌNH ĐÃ LƯU
    # (Mô phỏng theo code ví dụ của bạn)
    # -------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("PHẦN 6: TẢI VÀ KIỂM TRA MÔ HÌNH ĐÃ LƯU")
    print("=" * 60)

    if os.path.exists(model_save_path):
        try:
            print(f"Đang tải mô hình từ file: {model_save_path}")
            # Dùng joblib.load (tương tự pickle.load)
            loaded_model = joblib.load(model_save_path)

            print("Tải mô hình thành công!")

            # Tạo một khách hàng mẫu (dữ liệu thô 10 cột)
            # Đây là một khách hàng có nguy cơ rời bỏ cao (Spain, 1 sản phẩm, không active)
            sample_customer_data = {
                'credit_score': 650,
                'country': 'Spain',
                'gender': 'Female',
                'age': 45,
                'tenure': 2,
                'balance': 120000.0,
                'products_number': 1,
                'credit_card': 1,
                'active_member': 0,
                'estimated_salary': 50000.0
            }

            # Chuyển nó thành DataFrame (vì pipeline của chúng ta nhận đầu vào là DataFrame)
            sample_df = pd.DataFrame([sample_customer_data])

            print(f"\nĐang dự đoán cho khách hàng mẫu:\n {sample_df.to_string()}")

            # 1. Dự đoán (predict) -> trả về 0 (Không) hoặc 1 (Có)
            prediction = loaded_model.predict(sample_df)

            # 2. Dự đoán xác suất (predict_proba) -> trả về [P(0), P(1)]
            probabilities = loaded_model.predict_proba(sample_df)

            churn_probability = probabilities[0][1]  # Lấy xác suất rời bỏ (class 1)

            print("\n--- KẾT QUẢ DỰ ĐOÁN TỪ MÔ HÌNH ĐÃ LƯU ---")
            print(f"Dự đoán (0 = Không, 1 = Có): {prediction[0]}")
            print(f"Xác suất rời bỏ (Churn Probability): {churn_probability:.2%}")

        except Exception as e:
            print(f"LỖI khi tải hoặc dự đoán bằng mô hình đã lưu: {e}")
            traceback.print_exc()
    else:
        print(f"Lỗi: Không tìm thấy file mô hình tại '{model_save_path}'. "
              "Có thể quá trình huấn luyện (Phần 4) đã thất bại.")