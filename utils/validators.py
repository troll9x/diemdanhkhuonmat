"""Các tiện ích kiểm tra và xác thực dữ liệu đầu vào."""
import re
from flask import current_app


def validate_email(email):
    """
    Kiểm tra định dạng địa chỉ email có hợp lệ không.
    Trả về True nếu hợp lệ, False nếu không.
    """
    if not email:
        return False
    # Biểu thức chính quy kiểm tra định dạng email chuẩn
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_phone(phone):
    """
    Kiểm tra định dạng số điện thoại.
    Số điện thoại là tuỳ chọn — trả về True nếu để trống.
    Trả về True nếu hợp lệ (chỉ chứa số, độ dài 7–15 ký tự).
    """
    if not phone:
        return True   # Số điện thoại không bắt buộc
    # Loại bỏ khoảng trắng, gạch ngang, dấu ngoặc
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    # Kiểm tra chỉ chứa chữ số và có độ dài hợp lệ
    return cleaned.isdigit() and 7 <= len(cleaned) <= 15


def allowed_file(filename):
    """
    Kiểm tra phần mở rộng (extension) của file có được phép upload không.
    Danh sách cho phép được lấy từ cấu hình ALLOWED_EXTENSIONS.
    Trả về True nếu được phép, False nếu không.
    """
    if not filename:
        return False
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()   # Lấy phần mở rộng (chữ thường)
    allowed = current_app.config.get('ALLOWED_EXTENSIONS', [])
    return ext in allowed


def validate_password_strength(password):
    """
    Kiểm tra độ mạnh của mật khẩu theo các tiêu chí:
      - Ít nhất 8 ký tự
      - Chứa ít nhất 1 chữ hoa
      - Chứa ít nhất 1 chữ thường
      - Chứa ít nhất 1 chữ số
    Trả về: (bool hợp_lệ, str thông_báo)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one digit"
    return True, "Password is strong"


def sanitize_filename(filename):
    """
    Làm sạch tên file để ngăn chặn tấn công directory traversal.
    - Loại bỏ các thành phần đường dẫn (chỉ giữ lại tên file thuần)
    - Thay thế ký tự đặc biệt bằng dấu gạch dưới
    Trả về tên file đã được làm sạch.
    """
    # Loại bỏ phần đường dẫn, chỉ giữ tên file
    filename = filename.replace('\\', '/').split('/')[-1]
    # Chỉ cho phép chữ cái, số, dấu chấm, gạch ngang, gạch dưới
    filename = re.sub(r'[^\w\.\-]', '_', filename)
    return filename
