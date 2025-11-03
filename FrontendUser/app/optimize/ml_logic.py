# optimize/ml_logic.py

import os
import joblib

from FrontendUser.FrontendUser.app.DatabaseConnector import save_training_run_metadata
from FrontendUser.FrontendUser.train_churn_model import DatabaseConnector, fetch_training_data, train_churn_model

# Import các thư viện ML, CSDL, v.v. (từ script train_churn_model.py cũ của bạn)

# Thư mục lưu file model
SAVE_DIRECTORY = "saved_models"


def train_and_save_new_run(db_config, bank_id, dataset_id, base_model_id):
    """
    Thực hiện toàn bộ quy trình: Tải dữ liệu, Huấn luyện, Lưu File và Lưu Metadata CSDL.
    """
    print(f"Bắt đầu tái huấn luyện cho Bank {bank_id}, Dataset {dataset_id}")

    # 1. Tải dữ liệu
    try:
        with DatabaseConnector(db_config) as db:
            customer_df = fetch_training_data(db, dataset_id)
    except Exception as e:
        print(f"Lỗi tải dữ liệu: {e}")
        return False, None

    if customer_df is None:
        return False, None

    # 2. Huấn luyện Model
    try:
        trained_model, final_f1_score, final_auc_score = train_churn_model(customer_df)
    except Exception as e:
        print(f"Lỗi huấn luyện mô hình: {e}")
        return False, None

    # 3. LƯU FILE VÀ METADATA
    try:
        # 3A. Lưu File Model
        NEW_FILE_NAME = f"model_churn_bank_{bank_id}_ds_{dataset_id}_{os.urandom(4).hex()}.joblib"
        model_save_path = os.path.join(SAVE_DIRECTORY, NEW_FILE_NAME)
        os.makedirs(SAVE_DIRECTORY, exist_ok=True)
        joblib.dump(trained_model, model_save_path)
        print(f"Đã lưu file model vào: {model_save_path}")

        # 3B. Lưu Metadata vào training_run
        with DatabaseConnector(db_config) as db_meta:
            new_run_id = save_training_run_metadata(
                db_meta,
                bank_id=bank_id,
                dataset_id=dataset_id,
                model_artifact_path=model_save_path,
                f1_score=final_f1_score
                # Lưu ý: Hàm này dùng BASE_MODEL_ID mặc định. Cần truyền vào nếu muốn linh hoạt.
            )

        if new_run_id:
            return True, new_run_id
        else:
            return False, None

    except Exception as e:
        print(f"Lỗi khi lưu trữ (File/CSDL): {e}")
        return False, None

# Lưu ý: Các hàm CSDL/ML chi tiết (DatabaseConnector, train_churn_model,...)
# cần được đặt trong các file tiện ích (ví dụ: db_utils.py) trong thư mục gốc
# hoặc thư mục optimize để có thể được import vào đây.