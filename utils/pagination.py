"""Pagination utilities."""
from flask import request


def paginate(query, schema=None):
    """
    Paginate a SQLAlchemy query.
    
    Args:
        query: SQLAlchemy query object
        schema: Optional Marshmallow schema for serialization
    
    Returns:
        dict with items, pagination metadata
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Limit per_page to prevent abuse
    per_page = min(per_page, 100)
    
    paginated = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    items = paginated.items
    
    # Serialize if schema provided
    if schema:
        items = schema.dump(items, many=True)
    
    return {
        'items': items,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total_items': paginated.total,
            'total_pages': paginated.pages,
            'has_next': paginated.has_next,
            'has_prev': paginated.has_prev,
            'next_page': paginated.next_num if paginated.has_next else None,
            'prev_page': paginated.prev_num if paginated.has_prev else None
        }
    }