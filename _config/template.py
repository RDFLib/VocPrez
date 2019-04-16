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
    # an example of a SPARQL endpoint - here supplied by an instance of GrpahDB
    'gsq-graphdb': {
        'source': VocabSource.SPARQL,
        'sparql_endpoint': 'http://graphdb.gsq.digital:7200/repositories/GSQ_Vocabularies_core'
    },
    # an example of querying the ARDC RVA vocab system (https://vocabs.ands.org.au)
    'rva': {
        'source': VocabSource.RVA,
        'api_endpoint': 'https://vocabs.ands.org.au/registry/api/resource/vocabularies/{}?includeAccessPoints=true',
        'vocabs': [
            {
                'ardc_id': 50,
                'uri': 'http://resource.geosciml.org/classifierscheme/cgi/2016.01/geologicunittype',
            },
            {
                'ardc_id': 52,
                'uri': 'http://resource.geosciml.org/classifierscheme/cgi/2016.01/contacttype',
            },
            {
                'ardc_id': 57,
                'uri': 'http://resource.geosciml.org/classifierscheme/cgi/2016.01/stratigraphicrank',
            }
        ]
    }
}
