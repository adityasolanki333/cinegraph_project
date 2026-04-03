import logging

logger = logging.getLogger(__name__)


def error_response(message, code, status=400):
    if status == 500:
        logger.error('Internal error: %s', message)
        message = 'An internal error occurred'
    return {'error': message, 'code': code, '_status': status}
