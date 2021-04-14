import sys
import logging
from os.path import *

THIS_DIR = dirname(realpath(__file__))
sys.path.insert(0, THIS_DIR)
sys.path.insert(0, join(THIS_DIR, 'vocprez'))
logging.basicConfig(stream=sys.stderr)

from vocprez.app import app as application
