from os import path

APP_DIR = path.dirname(path.dirname(path.realpath(__file__)))
TEMPLATES_DIR = path.join(APP_DIR, 'view', 'templates')
STATIC_DIR = path.join(APP_DIR, 'view', 'static')
LOGFILE = APP_DIR + '/flask.log'
DEBUG = True


TITLE = 'VocPrez'


#
#   Vocabulary data sources
#
# Here is the list of vocabulary sources that this instance uses. FILE, SPARQL, RVA & VOCBENCH are implemented already
# and are on by default (e.g. VOCBENCH = None) but other sources, such as GitHub can be added. To enable them, add a new
# like like VocBench.XXX = None
class VocabSource:
    FILE = 'FILE'
    SPARQL = 'SPARQL'
    RVA = 'RVA'
    VOCBENCH = 'VOCBENCH'
    GITHUB = 'GITHUB'


VOCAB_SOURCES = {
    'graphdb': {
        'source': VocabSource.SPARQL,
        'endpoint': 'http://graphdb.gsq.digital:7200/repositories/GSQ_Vocabularies_core'
    },
    'rva': {
        'source': VocabSource.RVA,
        'vocab_ids': [50, 52, 57]
    }
}
