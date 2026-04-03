import json
import logging
from django.http import JsonResponse

logger = logging.getLogger(__name__)

MAX_TITLE_LENGTH = 500
MAX_DESCRIPTION_LENGTH = 5000
MAX_REVIEW_TEXT_LENGTH = 10000
MAX_BIO_LENGTH = 2000
MAX_COMMENT_LENGTH = 5000
MAX_NOTE_LENGTH = 2000
MAX_URL_LENGTH = 2048
MAX_MESSAGE_LENGTH = 5000
VALID_MEDIA_TYPES = ('movie', 'tv')
MIN_RATING = 1
MAX_RATING = 10


def error_response(message, code, status=400):
    if status == 500:
        logger.error('Internal error: %s', message)
        message = 'An internal error occurred'
    return JsonResponse({'error': message, 'code': code}, status=status)


def parse_json_body(request):
    try:
        return json.loads(request.body), None
    except json.JSONDecodeError:
        return None, error_response('Invalid JSON in request body', 'INVALID_JSON')


def validate_rating(value):
    if value is None:
        return None, 'Rating is required'
    try:
        rating = int(value)
    except (TypeError, ValueError):
        return None, f'Rating must be an integer between {MIN_RATING} and {MAX_RATING}'
    if rating < MIN_RATING or rating > MAX_RATING:
        return None, f'Rating must be between {MIN_RATING} and {MAX_RATING}'
    return rating, None


def validate_tmdb_id(value):
    if value is None:
        return None, 'tmdbId is required'
    try:
        tmdb_id = int(value)
    except (TypeError, ValueError):
        return None, 'tmdbId must be a positive integer'
    if tmdb_id <= 0:
        return None, 'tmdbId must be a positive integer'
    return tmdb_id, None


def validate_media_type(value, default='movie'):
    if value is None:
        return default, None
    if value not in VALID_MEDIA_TYPES:
        return None, f'mediaType must be one of: {", ".join(VALID_MEDIA_TYPES)}'
    return value, None


def validate_string_length(value, field_name, max_length, required=False):
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            return None, f'{field_name} is required'
        return '', None
    if not isinstance(value, str):
        return None, f'{field_name} must be a string'
    if len(value) > max_length:
        return None, f'{field_name} must be at most {max_length} characters'
    return value, None
