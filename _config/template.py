from os.path import dirname, realpath, join, abspath
from enum import Enum


APP_DIR = dirname(dirname(realpath(__file__)))
TEMPLATES_DIR = join(dirname(dirname(abspath(__file__))), 'view', 'templates')
STATIC_DIR = join(dirname(dirname(abspath(__file__))), 'view', 'static')
LOGFILE = APP_DIR + '/flask.log'
DEBUG = True


class VocabSource(Enum):
    FILE = 0
    SPARQL = 1
    RVA = 2
    VOCBENCH = 3
    # extend as needed


VOCABS = {

}
