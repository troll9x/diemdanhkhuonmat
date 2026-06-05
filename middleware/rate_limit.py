"""Rate limiting middleware."""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
    strategy="fixed-window"
)


def init_limiter(app):
    """Initialize rate limiter with app."""
    limiter.init_app(app)
    
    # Override storage_uri from config if provided
    if app.config.get('RATELIMIT_STORAGE_URL'):
        limiter.storage_uri = app.config['RATELIMIT_STORAGE_URL']
    
    # Override default limits from config if provided
    if app.config.get('RATELIMIT_DEFAULT'):
        limiter.default_limits = [app.config['RATELIMIT_DEFAULT']]
    
    return limiter