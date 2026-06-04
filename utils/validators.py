"""Input validation utilities."""
import re
from flask import current_app


def validate_email(email):
    """Validate email format."""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_phone(phone):
    """Validate phone number format."""
    if not phone:
        return True  # Phone is optional
    # Remove spaces, dashes, parentheses
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    # Check if it's all digits and has reasonable length
    return cleaned.isdigit() and 7 <= len(cleaned) <= 15


def allowed_file(filename):
    """Check if file extension is allowed."""
    if not filename:
        return False
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    allowed = current_app.config.get('ALLOWED_EXTENSIONS', [])
    return ext in allowed


def validate_password_strength(password):
    """Validate password meets minimum requirements."""
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
    """Sanitize filename to prevent directory traversal."""
    # Remove any path components
    filename = filename.replace('\\', '/').split('/')[-1]
    # Remove any non-alphanumeric characters except dots, dashes, underscores
    filename = re.sub(r'[^\w\.\-]', '_', filename)
    return filename