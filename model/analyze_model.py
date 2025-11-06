import os
import traceback

import joblib
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from sklearn.preprocessing import FunctionTransformer  # Cần import lại

# Import class DatabaseConnector và hàm add_custom_features từ file cũ
# Hãy đảm bảo tên file này chính xác (là file bạn dùng để huấn luyện)
try:
    from train_and_predict import DatabaseConnector, add_custom_features
except ImportError:
    try:
        from ml4 import DatabaseConnector, add_custom_features
    except ImportError:
        print("LỖI: Không tìm thấy file huấn luyện (ml4.py hoặc train_and_predict.py) ở cùng thư mục.")
        print("Vui lòng copy class 'DatabaseConnector' và hàm 'add_custom_features' vào file này.")


def plot_feature_importance(model_pipeline, bank_id, dataset_id):
    """
    Hàm này nhận vào pipeline đã huấn luyện và vẽ biểu đồ độ quan trọng.
    """
    print("Đang trích xuất độ quan trọng của đặc trưng...")

    # 1. Trích xuất mô hình XGBoost thực sự từ bên trong pipeline
    xgb_model = model_pipeline.named_steps['model']

    # 2. Trích xuất bộ tiền xử lý (preprocessor)
    preprocessor = model_pipeline.named_steps['preprocessor']

    # 3. Lấy danh sách tên đặc trưng SAU KHI đã được One-Hot-Encoding
    try:
        feature_names = preprocessor.get_feature_names_out()
    except Exception as e:
        print(f"Lỗi khi lấy tên đặc trưng: {e}")
        print("Đang thử cách dự phòng...")
        num_features = preprocessor.transformers_[0][2]
        cat_features_raw = preprocessor.named_transformers_['cat'].get_feature_names_out()

        num_features_prefixed = [f"num__{col}" for col in num_features]
        cat_features_prefixed = [f"cat__{col}" for col in cat_features_raw]

        feature_names = np.concatenate([num_features_prefixed, cat_features_prefixed])

    # 4. Lấy điểm số quan trọng từ mô hình XGBoost
    importances = xgb_model.feature_importances_

    # 5. Tạo DataFrame để dễ dàng vẽ
    feature_importance_df = pd.DataFrame({
        'Feature': feature_names,
        'Importance': importances
    }).sort_values(by='Importance', ascending=False)

    # 6. Dọn dẹp tên cột (loại bỏ tiền tố 'num__' và 'cat__')
    feature_importance_df['Feature'] = feature_importance_df['Feature'].str.replace('num__', '').str.replace('cat__',
                                                                                                             '')

    print("\n--- Các đặc trưng quan trọng nhất ---")
    print(feature_importance_df.head(10))

    # 7. Vẽ biểu đồ (Giữ nguyên)
    plt.figure(figsize=(12, 10))
    sns.barplot(x='Importance', y='Feature', data=feature_importance_df.head(15), color="#3498db")
    plt.title(f'Feature Importance cho Bank {bank_id} - Dataset {dataset_id}')
    # ... (Giữ nguyên)
    plt.tight_layout()

    # === (THAY ĐỔI QUAN TRỌNG) ===
    # Đảm bảo bạn có thư mục 'static'
    os.makedirs('static', exist_ok=True)

    # Lưu file ảnh VÀO THƯ MỤC 'static'
    plot_filename = f'static/feature_importance_bank_{bank_id}_dataset_{dataset_id}.png'
    plt.savefig(plot_filename)
    print(f"\nĐã lưu biểu đồ vào file: {plot_filename}")

    # plt.show() # Không cần dòng này nữa, vì server sẽ hiển thị
    plt.close()  # Đóng biểu đồ lại để tiết kiệm bộ nhớ


# =============================================================================
# HÀM CHẠY CHÍNH
# =============================================================================
if __name__ == "__main__":

    # 1. Chỉ định mô hình bạn muốn phân tích
    BANK_ID = 1
    DATASET_ID = 2

    # 2. Tạo đường dẫn đến file .joblib
    SAVE_DIRECTORY = "saved_models"
    MODEL_FILE_NAME = f"model_churn_bank_{BANK_ID}_dataset_{DATASET_ID}.joblib"
    model_path = os.path.join(SAVE_DIRECTORY, MODEL_FILE_NAME)

    if not os.path.exists(model_path):
        print(f"Lỗi: Không tìm thấy file mô hình tại '{model_path}'.")
        print("Vui lòng chạy file huấn luyện trước.")
    else:
        print(f"Đang tải mô hình từ: {model_path}...")

        # 3. Tải mô hình pipeline đã lưu
        try:
            # Tải mô hình
            loaded_pipeline = joblib.load(model_path)
            print("Tải mô hình thành công!")

            # 4. Gọi hàm vẽ biểu đồ
            plot_feature_importance(loaded_pipeline, BANK_ID, DATASET_ID)

        except Exception as e:
            print(f"Lỗi khi tải hoặc phân tích mô hình: {e}")
            traceback.print_exc()