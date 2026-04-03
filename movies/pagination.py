def paginate_queryset(request, queryset, default_limit=20, max_limit=100):
    try:
        page = max(1, int(request.GET.get('page', 1)))
    except (ValueError, TypeError):
        page = 1
    try:
        limit = max(1, min(max_limit, int(request.GET.get('limit', default_limit))))
    except (ValueError, TypeError):
        limit = default_limit
    total = queryset.count()
    offset = (page - 1) * limit
    items = queryset[offset:offset + limit]
    return items, {
        'page': page,
        'limit': limit,
        'total': total,
        'totalPages': (total + limit - 1) // limit if total > 0 else 1,
        'hasMore': offset + limit < total,
    }
