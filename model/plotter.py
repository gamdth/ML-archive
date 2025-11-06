import io
import base64
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay

# File này không cần import Flask, nhưng nó cần import các hàm
# từ file huấn luyện để hiểu pipeline
try:
    from train_and_predict import add_custom_features
except ImportError:
    from ml6 import add_custom_features  # Thử import từ ml4 nếu train_and_predict thất bại


def plot_to_base64(fig):
    """Hàm helper: Chuyển một figure Matplotlib thành chuỗi Base64."""
    img_buffer = io.BytesIO()
    # Dùng bbox_inches='tight' để biểu đồ không bị cắt xén
    fig.savefig(img_buffer, format='png', bbox_inches='tight')
    plt.close(fig)  # Đóng figure để giải phóng bộ nhớ
    img_buffer.seek(0)
    img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
    return img_base64


def plot_feature_importance_base64(model_pipeline):
    """Vẽ biểu đồ Feature Importance và trả về Base64."""
    print("Plotter: Đang tạo biểu đồ Feature Importance...")
    try:
        xgb_model = model_pipeline.named_steps['model']
        preprocessor = model_pipeline.named_steps['preprocessor']
        feature_names = preprocessor.get_feature_names_out()
        importances = xgb_model.feature_importances_

        df = pd.DataFrame({
            'Feature': feature_names,
            'Importance': importances
        }).sort_values(by='Importance', ascending=False)
        df['Feature'] = df['Feature'].str.replace('num__', '').str.replace('cat__', '')

        fig, ax = plt.subplots(figsize=(10, 8))
        sns.barplot(x='Importance', y='Feature', data=df.head(15), color="#3498db", ax=ax)
        ax.set_title('Top 15 Đặc trưng Quan trọng nhất')
        ax.set_xlabel('Tầm quan trọng')
        ax.set_ylabel('Đặc trưng')

        return plot_to_base64(fig)
    except Exception as e:
        return f"Lỗi khi tạo Feature Importance: {e}"


def plot_confusion_matrix_base64(model_pipeline, X_test, y_test):
    """Vẽ Ma trận Nhầm lẫn và trả về Base64."""
    print("Plotter: Đang tạo biểu đồ Confusion Matrix...")
    try:
        y_pred = model_pipeline.predict(X_test)
        cm = confusion_matrix(y_test, y_pred)

        fig, ax = plt.subplots(figsize=(8, 6))
        disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=['Ở lại (0)', 'Rời bỏ (1)'])
        disp.plot(ax=ax, cmap='Blues', colorbar=False)
        ax.set_title('Ma trận Nhầm lẫn (Hiệu suất)')

        return plot_to_base64(fig)
    except Exception as e:
        return f"Lỗi khi tạo Confusion Matrix: {e}"


def plot_eda_scatter_base64(df, x_var, y_var):
    """Vẽ biểu đồ Scatter Plot (EDA) và trả về Base64."""
    print(f"Plotter: Đang tạo biểu đồ EDA Scatter: {x_var} vs {y_var}")
    try:
        fig, ax = plt.subplots(figsize=(10, 7))
        sns.scatterplot(data=df, x=x_var, y=y_var, hue='churn', ax=ax, alpha=0.6, s=50, palette="coolwarm")
        ax.set_title(f'Tương quan giữa {x_var} và {y_var} (theo Churn)')
        ax.legend(title='Churn (0=Ở lại, 1=Rời bỏ)')

        return plot_to_base64(fig)
    except Exception as e:
        return f"Lỗi khi tạo Scatter Plot: {e}"


def plot_eda_box_base64(df, x_var):
    """Vẽ biểu đồ Box Plot (EDA) và trả về Base64."""
    print(f"Plotter: Đang tạo biểu đồ EDA Box Plot: {x_var} vs Churn")
    try:
        fig, ax = plt.subplots(figsize=(10, 7))
        sns.boxplot(data=df, x='churn', y=x_var, ax=ax, palette="plasma")
        ax.set_title(f'Phân phối của {x_var} theo Churn')
        ax.set_xlabel('Churn (0=Ở lại, 1=Rời bỏ)')

        return plot_to_base64(fig)
    except Exception as e:
        return f"Lỗi khi tạo Box Plot: {e}"


# (Tùy chọn) Thêm 1 đoạn để test file này
if __name__ == '__main__':
    print("Đang chạy file plotter.py ở chế độ test...")
    print("File này không dùng để chạy trực tiếp, mà để được import bởi app.py.")
    print("Vui lòng chạy 'app.py' để khởi động web server.")