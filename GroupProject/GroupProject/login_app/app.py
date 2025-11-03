import json
import os
import csv
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, make_response, session

# -------------------------
# Cấu hình đường dẫn
# -------------------------
basedir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(basedir, 'templates')
static_dir = os.path.join(basedir, 'static')
data_dir = os.path.join(basedir, 'data')          # thư mục data
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

# FILES (CSV)
USER_CSV_FILE = os.path.join(basedir, 'QLND.csv')
DATA_CSV_FILE = os.path.join(basedir, 'QLDL.csv')
ACTIVITY_CSV_FILE = os.path.join(basedir, 'QLHD.csv')
CAMPAIGN_CSV_FILE = os.path.join(basedir, 'QLCD.csv')

# FILE JSON chứa người dùng (dữ liệu đăng nhập dynamic)
USERS_JSON_FILE = os.path.join(data_dir, 'data.json')

# -------------------------
# Tạo Flask app (duy nhất)
# -------------------------
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.secret_key = "super-secret-key"

# -------------------------
# Khởi tạo CSV nếu chưa có
# (mình giữ logic bạn từng có)
# -------------------------
USER_CSV_HEADERS = ['STT', 'User', 'Email', 'Mật khẩu', 'Trạng thái', 'Dịch vụ', 'Ngày đăng nhập', 'Ngày kết thúc']
if not os.path.exists(USER_CSV_FILE):
    initial_users = [
        {'STT': '01', 'User': 'A', 'Email': 'A@gmail.com', 'Mật khẩu': 'A123', 'Trạng thái': 'Hoạt động', 'Dịch vụ': 'Premium', 'Ngày đăng nhập': '5/10/2025', 'Ngày kết thúc': '5/10/2026'},
        {'STT': '02', 'User': 'B', 'Email': 'B@gmail.com', 'Mật khẩu': 'B456', 'Trạng thái': 'Hoạt động', 'Dịch vụ': 'Premium', 'Ngày đăng nhập': '5/10/2025', 'Ngày kết thúc': '5/10/2026'},
    ]
    with open(USER_CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=USER_CSV_HEADERS)
        writer.writeheader()
        writer.writerows(initial_users)

DATA_CSV_HEADERS = ['STT', 'User', 'Tên bộ dữ liệu', 'Kiểu dữ liệu', 'Ngày cập nhật', 'Trạng thái', 'Thao tác', 'Ghi chú']
if not os.path.exists(DATA_CSV_FILE):
    initial_data = [
        {'STT': '1', 'User': 'User01', 'Tên bộ dữ liệu': 'khach_hang_moi', 'Kiểu dữ liệu': 'Định lượng', 'Ngày cập nhật': '01/10/2025', 'Trạng thái': 'Hoàn thành', 'Thao tác': 'abcde', 'Ghi chú': '...'},
        {'STT': '2', 'User': 'User02', 'Tên bộ dữ liệu': 'khach_hang_moi', 'Kiểu dữ liệu': 'Định lượng', 'Ngày cập nhật': '02/10/2025', 'Trạng thái': 'Hoàn thành', 'Thao tác': 'abcde', 'Ghi chú': '...'},
    ]
    with open(DATA_CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=DATA_CSV_HEADERS)
        writer.writeheader()
        writer.writerows(initial_data)

ACTIVITY_CSV_HEADERS = ['STT', 'User', 'Email', 'Đăng nhập', 'Đăng xuất']
if not os.path.exists(ACTIVITY_CSV_FILE):
    initial_activities = [
        {'STT': '01', 'User': 'A', 'Email': 'A@gmail.com', 'Đăng nhập': '10:30 5/10/2025', 'Đăng xuất': '11:00 5/10/2025'},
        {'STT': '02', 'User': 'B', 'Email': 'B@gmail.com', 'Đăng nhập': '21:00 6/10/2025', 'Đăng xuất': '21:15 6/10/2025'},
    ]
    with open(ACTIVITY_CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=ACTIVITY_CSV_HEADERS)
        writer.writeheader()
        writer.writerows(initial_activities)

CAMPAIGN_CSV_HEADERS = ['STT', 'Chiến dịch', 'Điều kiện áp dụng', 'Người tạo', 'Ngân sách', 'Bắt đầu', 'Kết thúc']
if not os.path.exists(CAMPAIGN_CSV_FILE):
    initial_campaigns = [
        {'STT': '01', 'Chiến dịch': 'Marketing 1', 'Điều kiện áp dụng': 'ABCDEF', 'Người tạo': 'USER1', 'Ngân sách': '10.000.000', 'Bắt đầu': '5/10/2025', 'Kết thúc': '5/10/2025'},
        {'STT': '02', 'Chiến dịch': 'Marketing 2', 'Điều kiện áp dụng': 'ABCDEF', 'Người tạo': 'USER2', 'Ngân sách': '8.000.000', 'Bắt đầu': '5/11/2025', 'Kết thúc': '15/11/2025'},
    ]
    with open(CAMPAIGN_CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=CAMPAIGN_CSV_HEADERS)
        writer.writeheader()
        writer.writerows(initial_campaigns)

# -------------------------
# USERS JSON: tạo file mẫu nếu chưa có
# -------------------------
if not os.path.exists(USERS_JSON_FILE):
    sample_users = [
        {"email": "nguyenvanb@gmail.com", "password": "123456", "name": "Nguyễn Văn B", "role": "Trưởng phòng Marketing", "permission": "Super Admin"},
        {"email": "lethianh@gmail.com", "password": "654321", "name": "Lê Thị Ánh", "role": "Nhân viên Kinh doanh", "permission": "Admin"}
    ]
    with open(USERS_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(sample_users, f, ensure_ascii=False, indent=2)

# -------------------------
# Admin credentials (nếu bạn muốn giữ)
# -------------------------
ADMIN_USER = {"email": "admin@gmail.com", "password": "123456"}

# -------------------------
# Routes
# -------------------------
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

        # 1) Kiểm tra admin trước (tuỳ bạn có cần)
        if email == ADMIN_USER["email"] and password == ADMIN_USER["password"]:
            session["user"] = {"email": email, "name": "Administrator", "role": "Admin", "permission": "Admin"}
            resp = make_response(redirect(url_for("success")))
            if remember:
                resp.set_cookie("email", email, max_age=60*60*24*7)
                resp.set_cookie("password", password, max_age=60*60*24*7)
            else:
                resp.delete_cookie("email")
                resp.delete_cookie("password")
            return resp

        # 2) Kiểm tra users.json
        try:
            with open(USERS_JSON_FILE, "r", encoding="utf-8") as f:
                users = json.load(f)
        except Exception as e:
            users = []
            print("Lỗi đọc users.json:", e)

        user_found = None
        for u in users:
            if u.get("email") == email and u.get("password") == password:
                user_found = u
                break

        if user_found:
            session["user"] = user_found
            resp = make_response(redirect(url_for("thongtincanhan")))
            if remember:
                resp.set_cookie("email", email, max_age=60*60*24*7)
                resp.set_cookie("password", password, max_age=60*60*24*7)
            else:
                resp.delete_cookie("email")
                resp.delete_cookie("password")
            return resp
        else:
            message = "Sai email hoặc mật khẩu!"

    return render_template("login.html", message=message, saved_email=saved_email, saved_password=saved_password)

@app.route("/success")
def success():
    return render_template("success.html")

@app.route("/go_home", methods=["POST"])
def go_home():
    return redirect(url_for("home_page"))

@app.route("/home")
def home_page():
    return render_template("home.html")

@app.route("/gioithieu")
def gioithieu():
    return render_template("gioithieu.html")

@app.route("/thongbao")
def thongbao():
    return render_template("thongbao.html")

@app.route("/tongquan")
def tongquan():
    return render_template("tongquan.html")

@app.route("/quanlinguoidung1")
def quanlinguoidung1():
    users_list = []
    try:
        with open(USER_CSV_FILE, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            users_list = list(reader)
    except FileNotFoundError:
        print(f"LỖI: Không tìm thấy file {USER_CSV_FILE}.")
    return render_template("quanlinguoidung1.html", users=users_list)

@app.route("/add_user", methods=["POST"])
def add_user():
    if request.method == "POST":
        new_user_val = request.form.get("user")
        new_email = request.form.get("email")
        new_password = request.form.get("password")
        new_status = request.form.get("status")
        new_service = request.form.get("service")
        new_login_date = request.form.get("login_date")
        new_end_date = request.form.get("end_date")

        current_stt = 0
        try:
            with open(USER_CSV_FILE, 'r', newline='', encoding='utf-8') as f:
                current_stt = len(list(csv.reader(f))) - 1
        except FileNotFoundError:
            current_stt = 0

        new_stt = f"{current_stt + 1:02d}"

        new_user_dict = {
            'STT': new_stt, 'User': new_user_val, 'Email': new_email, 'Mật khẩu': new_password,
            'Trạng thái': new_status, 'Dịch vụ': new_service, 'Ngày đăng nhập': new_login_date, 'Ngày kết thúc': new_end_date
        }

        with open(USER_CSV_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=USER_CSV_HEADERS)
            writer.writerow(new_user_dict)

        return redirect(url_for('quanlinguoidung1'))

@app.route("/quanlidulieu")
def quanlidulieu():
    data_list = []
    try:
        with open(DATA_CSV_FILE, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            data_list = list(reader)
    except FileNotFoundError:
        print(f"LỖI: Không tìm thấy file {DATA_CSV_FILE}.")
    return render_template("quanlidulieu.html", data=data_list)

@app.route("/quanlihoatdong")
def quanlihoatdong():
    activity_list = []
    try:
        with open(ACTIVITY_CSV_FILE, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            activity_list = list(reader)
    except FileNotFoundError:
        print(f"LỖI: Không tìm thấy file {ACTIVITY_CSV_FILE}.")
    return render_template("quanlihoatdong.html", activities=activity_list)

@app.route("/quanlicacchiendich")
def quanlicacchiendich():
    campaign_list = []
    try:
        with open(CAMPAIGN_CSV_FILE, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            campaign_list = list(reader)
    except FileNotFoundError:
        print(f"LỖI: Không tìm thấy file {CAMPAIGN_CSV_FILE}.")
    return render_template("quanlicacchiendich.html", campaigns=campaign_list)

@app.route("/caidat")
def caidat():
    return render_template("caidat.html")

@app.route("/thongtincanhan")
def thongtincanhan():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("thongtincanhan.html", user=session["user"])

@app.route("/update_user", methods=["POST"])
def update_user():
    if "user" not in session:
        return redirect(url_for("login"))

    updated_user = {
        "email": request.form.get("email"),
        "password": request.form.get("password"),
        "name": request.form.get("name"),
        "role": request.form.get("role"),
        "permission": request.form.get("permission")
    }

    # Đọc users từ JSON và cập nhật
    try:
        with open(USERS_JSON_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
    except Exception as e:
        users = []
        print("Lỗi đọc users.json:", e)

    for u in users:
        if u.get("email") == session["user"].get("email"):
            u.update(updated_user)
            break

    with open(USERS_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

    # Cập nhật session để hiển thị mới
    session["user"] = updated_user
    return redirect(url_for("thongtincanhan"))
# Run
if __name__ == "__main__":
    app.run(debug=True)
