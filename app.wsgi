import sys
import logging
sys.path.insert(0, '/var/www/vocprez-demeter')
sys.path.insert(0, '/var/www/vocprez-demeter/vocprez')
logging.basicConfig(stream=sys.stderr)

from app import app as application
