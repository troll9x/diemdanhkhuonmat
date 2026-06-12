"""
Tiện Ích Nhập CSV (CSV Import Utilities)
Hỗ trợ nhập dữ liệu hàng loạt từ file CSV cho sinh viên và giảng viên.

Hàm chính:
  parse_csv_file(file_content, encoding) — Parse bytes CSV → (headers, rows)
  validate_student_row(row, row_num)     — Validate một dòng dữ liệu sinh viên
  validate_lecturer_row(row, row_num)    — Validate một dòng dữ liệu giảng viên
  process_student_import(rows, db)       — Nhập danh sách sinh viên vào DB (bỏ qua trùng lặp)
  process_lecturer_import(rows, db)      — Nhập danh sách giảng viên vào DB
Trả về: (success_count, error_list) — số bản ghi thành công và danh sách lỗi
"""
import csv
import io
from typing import List, Dict, Tuple, Any
from datetime import datetime


def parse_csv_file(file_content: bytes, encoding: str = 'utf-8') -> Tuple[List[str], List[Dict[str, str]]]:
    """
    Parse CSV file content.
    
    Args:
        file_content: Raw bytes from uploaded file
        encoding: File encoding (default: utf-8)
    
    Returns:
        Tuple of (headers, rows)
        - headers: List of column names
        - rows: List of dictionaries (each row as dict)
    """
    try:
        # Decode bytes to string
        content = file_content.decode(encoding)
        
        # Parse CSV
        reader = csv.DictReader(io.StringIO(content))
        headers = reader.fieldnames if reader.fieldnames else []
        rows = list(reader)
        
        return headers, rows
    except UnicodeDecodeError:
        # Try with different encoding
        content = file_content.decode('latin-1')
        reader = csv.DictReader(io.StringIO(content))
        headers = reader.fieldnames if reader.fieldnames else []
        rows = list(reader)
        return headers, rows


def validate_required_fields(row: Dict[str, str], required_fields: List[str]) -> Tuple[bool, List[str]]:
    """
    Validate that row contains all required fields.
    
    Args:
        row: Dictionary representing one CSV row
        required_fields: List of required field names
    
    Returns:
        Tuple of (is_valid, missing_fields)
    """
    missing = []
    for field in required_fields:
        if field not in row or not row[field] or not row[field].strip():
            missing.append(field)
    
    return len(missing) == 0, missing


def clean_string(value: str) -> str:
    """Clean and normalize string value."""
    if not value:
        return ''
    return value.strip()


def parse_boolean(value: str) -> bool:
    """Parse boolean from string."""
    if not value:
        return False
    value_lower = value.lower().strip()
    return value_lower in ['true', '1', 'yes', 'y', 'có', 'đúng']


def parse_integer(value: str, default: int = None) -> int:
    """Parse integer from string."""
    if not value or not value.strip():
        return default
    try:
        return int(value.strip())
    except ValueError:
        return default


def parse_date(value: str, format: str = '%Y-%m-%d') -> datetime:
    """Parse date from string."""
    if not value or not value.strip():
        return None
    try:
        return datetime.strptime(value.strip(), format)
    except ValueError:
        # Try alternative formats
        for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d']:
            try:
                return datetime.strptime(value.strip(), fmt)
            except ValueError:
                continue
        return None


def generate_import_result(
    total: int,
    success: int,
    failed: int,
    errors: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Generate standardized import result.
    
    Args:
        total: Total rows processed
        success: Number of successful imports
        failed: Number of failed imports
        errors: List of error details
    
    Returns:
        Dictionary with import results
    """
    return {
        'total': total,
        'success': success,
        'failed': failed,
        'success_rate': round((success / total * 100) if total > 0 else 0, 2),
        'errors': errors
    }


def validate_email(email: str) -> bool:
    """Basic email validation."""
    if not email:
        return False
    email = email.strip()
    return '@' in email and '.' in email.split('@')[1]


def validate_phone(phone: str) -> bool:
    """Basic phone validation (Vietnamese format)."""
    if not phone:
        return True  # Optional field
    phone = phone.strip().replace(' ', '').replace('-', '')
    return phone.isdigit() and len(phone) >= 9 and len(phone) <= 15