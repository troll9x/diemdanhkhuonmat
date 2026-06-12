"""Tiện ích Định vị Địa lý: Tính khoảng cách theo công thức Haversine."""
import math


def calculate_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Tính khoảng cách đường thẳng (great-circle) giữa hai toạ độ GPS
    bằng công thức Haversine. Trả về khoảng cách tính bằng mét.

    Tham số:
      lat1, lon1 — vĩ độ và kinh độ điểm thứ nhất (độ)
      lat2, lon2 — vĩ độ và kinh độ điểm thứ hai (độ)

    Ứng dụng: kiểm tra sinh viên có đứng đủ gần giảng viên khi điểm danh không.
    """
    R = 6_371_000  # Bán kính Trái Đất tính bằng mét

    # Chuyển đổi từ độ sang radian
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)   # Hiệu vĩ độ
    dlam = math.radians(lon2 - lon1)   # Hiệu kinh độ

    # Công thức Haversine
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c   # Khoảng cách tính bằng mét
