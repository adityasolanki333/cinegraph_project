
import os
import django
import logging
import sys

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'movieflix.settings')
django.setup()

# Get loggers
logger = logging.getLogger('django')
movie_logger = logging.getLogger('movies')

print("--- STARTING LOGGING TEST ---")
print(f"Root handlers: {logging.getLogger().handlers}")
print(f"Django handlers: {logger.handlers}")

# Test logs
logger.info("TEST INFO LOG from django logger")
logger.warning("TEST WARNING LOG from django logger")
movie_logger.debug("TEST DEBUG LOG from movies logger")
movie_logger.info("TEST INFO LOG from movies logger")

print("--- FINISHED LOGGING TEST ---")
