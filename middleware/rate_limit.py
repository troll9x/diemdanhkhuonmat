"""Middleware giới hạn tốc độ yêu cầu (Rate Limiting)."""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Khởi tạo bộ giới hạn tốc độ dùng địa chỉ IP của client làm khoá nhận dạng
limiter = Limiter(
    key_func=get_remote_address,              # Nhận dạng client theo địa chỉ IP
    default_limits=["200 per day", "50 per hour"],  # Giới hạn mặc định: 200/ngày, 50/giờ
    storage_uri="memory://",                  # Lưu bộ đếm trong bộ nhớ (dùng Redis khi production)
    strategy="fixed-window"                   # Chiến lược cửa sổ cố định
)


def init_limiter(app):
    """
    Khởi tạo bộ giới hạn tốc độ và gắn vào ứng dụng Flask.
    Ghi đè giá trị mặc định từ cấu hình ứng dụng nếu có.
    """
    limiter.init_app(app)

    # Ghi đè nơi lưu trữ bộ đếm nếu được cấu hình (ví dụ: Redis URL)
    if app.config.get('RATELIMIT_STORAGE_URL'):
        limiter.storage_uri = app.config['RATELIMIT_STORAGE_URL']

    # Ghi đè giới hạn mặc định nếu được cấu hình
    if app.config.get('RATELIMIT_DEFAULT'):
        limiter.default_limits = [app.config['RATELIMIT_DEFAULT']]

    return limiter
