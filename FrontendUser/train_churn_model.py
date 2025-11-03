import os
import mysql.connector
import pandas as pd
import traceback
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import f1_score, roc_auc_score, classification_report
import xgboost as xgb


# =============================================================================
# PHẦN 1: CLASS KẾT NỐI (Sửa lại chỉ dùng MYSQL.CONNECTOR)
# =============================================================================

class DatabaseConnector:  # Đổi tên class cho rõ ràng
    def __init__(self,
                 server="localhost",
                 port=3306,
                 database="bank",
                 username="root",
                 password="@Obama123"):
        # Lưu config để kết nối
        self.config = {
            'host': server,
            'port': port,
            'database': database,
            'user': username,
            'password': password
        }
        self.conn = None  # Đây là đối tượng connection

    def connect(self):
        """Tạo kết nối dùng mysql.connector"""
        try:
            self.conn = mysql.connector.connect(**self.config)
            return self.conn
        except mysql.connector.Error as e:
            print(f"LỖI KẾT NỐI MYSQL: {e}")
            traceback.print_exc()
            self.conn = None
            return None

    def disConnect(self):
        """Ngắt kết nối self.conn (thay vì self.session)"""
        if self.conn and self.conn.is_connected():
            self.conn.close()
            # print("Đã ngắt kết nối CSDL.")

    def queryDataset(self, sql, params=None):
        """
        Dùng self.conn để truy vấn (thay vì self.engine)
        """
        # 1. Kiểm tra self.conn
        if not self.conn or not self.conn.is_connected():
            print("Lỗi: Chưa kết nối. Đang thử kết nối lại...")
            if not self.connect():  # Thử kết nối lại
                print("Lỗi: Không thể kết nối lại.")
                return None  # Vẫn lỗi thì thoát

        try:
            # 2. Dùng self.conn cho pd.read_sql
            # pd.read_sql hiểu được connection của mysql.connector
            df = pd.read_sql(sql, self.conn, params=params)
            return df
        except Exception as e:
            print(f"Lỗi khi truy vấn queryDataset: {e}")
            traceback.print_exc()
            return None

    def __enter__(self):
        if self.connect():
            return self
        else:
            raise IOError("Không thể kết nối CSDL")

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disConnect()  # Đảm bảo gọi đúng hàm disconnect


# =============================================================================
# PHẦN 2: CÁC HÀM XỬ LÝ (SỬA LẠI CÁCH TRUYỀN PARAMETER)
# =============================================================================

def fetch_training_data(db_connector, dataset_id_to_train):
    """
    Tải dữ liệu từ bảng Customer dựa trên dataset_id.
    """
    print(f"Đang tải dữ liệu huấn luyện từ CSDL cho dataset_id = {dataset_id_to_train}...")

    # Sửa SQL: mysql.connector dùng %s làm placeholder, KHÔNG dùng :d_id
    sql_query = """
    SELECT 
        credit_score, country, gender, age, tenure, balance, 
        products_number, credit_card, active_member, estimated_salary, 
        churn 
    FROM Customer
    WHERE dataset_id = %s 
    """
    # Sửa Params: Phải là một list hoặc tuple, KHÔNG phải dictionary
    params = (dataset_id_to_train,)

    # Dùng hàm queryDataset của class Connector
    df = db_connector.queryDataset(sql_query, params)

    if df is None or df.empty:
        print(f"Lỗi: Không tìm thấy dữ liệu cho dataset_id = {dataset_id_to_train}.")
        return None

    print(f"Tải thành công {len(df)} dòng dữ liệu.")
    return df


def train_churn_model(df):
    """
    Hàm này không thay đổi, vì nó làm việc trên DataFrame.
    """
    print("\nBắt đầu quá trình huấn luyện mô hình...")

    # 1. Định nghĩa Features (X) và Target (y)
    features = ['credit_score', 'country', 'gender', 'age', 'tenure', 'balance',
                'products_number', 'credit_card', 'active_member', 'estimated_salary']
    target = 'churn'

    X = df[features]
    y = df[target]

    # 2. Tiền xử lý (Preprocessing)
    numeric_features = ['credit_score', 'age', 'tenure', 'balance', 'products_number', 'estimated_salary']
    categorical_features = ['country', 'gender']

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), numeric_features),
            ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
        ],
        remainder='passthrough'
    )

    # 3. Tách tập Train / Test
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    print(f"Tập huấn luyện: {len(X_train)} | Tập kiểm tra: {len(X_test)}")

    # 4. Chọn mô hình (XGBoost)
    model = xgb.XGBClassifier(use_label_encoder=False, eval_metric='logloss', random_state=42)

    # 5. Tạo Pipeline
    full_pipeline = Pipeline(steps=[('preprocessor', preprocessor),
                                    ('model', model)])

    print("Đang huấn luyện (fitting) pipeline...")
    full_pipeline.fit(X_train, y_train)
    print("Huấn luyện hoàn tất!")

    # 6. Đánh giá
    y_pred = full_pipeline.predict(X_test)
    f1 = f1_score(y_test, y_pred)
    auc = roc_auc_score(y_test, full_pipeline.predict_proba(X_test)[:, 1])

    print("\n--- ĐÁNH GIÁ MÔ HÌNH ---")
    print(f"F1-Score (trên tập test): {f1:.4f}")
    print(f"AUC Score (trên tập test): {auc:.4f}")
    print("\nBáo cáo phân loại chi tiết:")
    print(classification_report(y_test, y_pred))

    return full_pipeline


# =============================================================================
# PHẦN 3: HÀM CHẠY CHÍNH (ĐÃ CẬP NHẬT ĐƯỜNG DẪN LƯU)
# =============================================================================

if __name__ == "__main__":

    # 1. CẤU HÌNH KẾT NỐI DATABASE
    db_config = {
        "server": "localhost",
        "port": 3306,
        "database": "bank",  # Đảm bảo đúng tên CSDL
        "username": "root",
        "password": "@Obama123"
    }

    # 2. CHỌN DATASET ĐỂ TRAIN
    DATASET_ID_TO_TRAIN = 2

    # 3. (MỚI) ĐỊNH NGHĨA VỊ TRÍ VÀ TÊN FILE LƯU
    # ------------------- BẠN CÓ THỂ SỬA Ở ĐÂY -------------------

    # Tên thư mục bạn muốn lưu (ví dụ: 'saved_models')
    # Thư mục này sẽ được tạo bên trong project của bạn.
    # Bạn cũng có thể dùng đường dẫn tuyệt đối, ví dụ: r"E:\LuuModel"
    SAVE_DIRECTORY = "saved_models"

    # Tên file mới bạn muốn đặt
    NEW_FILE_NAME = f"model_churn_v1_dataset_{DATASET_ID_TO_TRAIN}.joblib"

    # -------------------------------------------------------------

    # Tự động kết hợp đường dẫn (xử lý / và \ )
    model_save_path = os.path.join(SAVE_DIRECTORY, NEW_FILE_NAME)

    trained_model = None
    try:
        # 4. KẾT NỐI VÀ LẤY DỮ LIỆU
        with DatabaseConnector(**db_config) as db:
            print(f"Kết nối CSDL '{db_config['database']}' thành công.")

            # Bước A: Lấy data từ MySQL
            customer_df = fetch_training_data(db, DATASET_ID_TO_TRAIN)

        # 5. HUẤN LUYỆN MODEL (nếu lấy data thành công)
        if customer_df is not None:
            trained_model = train_churn_model(customer_df)
        else:
            print("Không có dữ liệu để huấn luyện. Dừng chương trình.")

        # 6. LƯU MODEL ĐÃ TRAIN (ĐÃ CẬP NHẬT)
        if trained_model is not None:
            # (MỚI) Tự động tạo thư mục nếu nó chưa tồn tại
            os.makedirs(SAVE_DIRECTORY, exist_ok=True)

            # Lưu model vào đường dẫn MỚI
            joblib.dump(trained_model, model_save_path)

            print(f"\nĐã lưu mô hình đã huấn luyện vào file: '{model_save_path}'")
            print("Bạn có thể dùng file này để dự đoán sau này.")

    except IOError as e:
        print(f"LỖI KẾT NỐI DATABASE (IOError): {e}")
    except Exception as e:
        print(f"LỖI CHUNG XẢY RA: {e}")
        traceback.print_exc()