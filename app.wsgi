from os.path import *
import sys
import logging


THIS_DIR = dirname(realpath(__file__))
sys.path.insert(0, THIS_DIR)
sys.path.insert(0, join(THIS_DIR, 'vocprez'))
logging.basicConfig(stream=sys.stderr)

from app import app as application
