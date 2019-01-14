from os import path
from data.source_FILE import FILE
from data.source_RVA import RVA
# RVA doesnt need to be imported as it's list_vocabularies method isn't used- vocabs from that are statically listed
from data.source_VOCBENCH import VOCBENCH

APP_DIR = path.dirname(path.dirname(path.realpath(__file__)))
TEMPLATES_DIR = path.join(APP_DIR, 'view', 'templates')
STATIC_DIR = path.join(APP_DIR, 'view', 'static')
LOGFILE = APP_DIR + '/flask.log'
DEBUG = True


#
# -- VocPrez Settings --------------------------------------------------------------------------------------------------
#

# Home title
TITLE = 'VocPrez'


#
#   Vocabulary data sources
#
# Here is the list of vocabulary sources that this instance uses. FILE, SPARQL, RVA & VOCBENCH are implemented already
# and are on by default (e.g. VOCBENCH = None) but other sources, such as GitHub can be added. To enable them, add a new
# like like VocBench.XXX = None
class VocabSource:
    FILE = 1
    SPARQL = 2
    RVA = 3
    VOCBENCH = 4
    # GITHUB = 5

# VOCBANCH credentials
VB_ENDPOINT = ''
VB_USER = ''
VB_PASSWORD = ''

#
#   Instance vocabularies
#
# Here you list the vocabularies that this instance of VocPrez knows about. Note that some vocab data sources, like
# VOCBENCH auto list vocabularies by implementing the list_vocabularies method and thus their vocabularies don't need to
# be listed here. FILE vocabularies too don't need to be listed here as they are automatically picked up by the system
# if the files are added to the data/ folder, as described in the DATA_SOURCES.md documentation file.
VOCABS = {
    'rva-50': {
        'source': VocabSource.RVA,
        'title': 'Geologic Unit Type',
        'sparql': 'http://vocabs.ands.org.au/repository/api/sparql/ga_geologic-unit-type_v0-1',
        'download': 'https://vocabs.ands.org.au/registry/api/resource/downloads/196/ga_geologic-unit-type_v0-1.ttl'
    },
    'rva-52': {
        'source': VocabSource.RVA,
        'title': 'Contact Type',
        'sparql': 'http://vocabs.ands.org.au/repository/api/sparql/ga_contact-type_v0-1',
        'download': 'https://vocabs.ands.org.au/registry/api/resource/downloads/202/ga_contact-type_v0-1.ttl'
    },
    'rva-57': {
        'source': VocabSource.RVA,
        'title': 'Stratigraphic Rank',
        'sparql': 'http://vocabs.ands.org.au/repository/api/sparql/ga_stratigraphic-rank_v0-1',
        'download': 'https://vocabs.ands.org.au/registry/api/resource/downloads/217/ga_stratigraphic-rank_v0-1.ttl'
    },
    # 'assoc': {
    #     'source': VocabSource.FILE,
    #     'title': 'ISO19115-1 Association Type Codes - File'
    # },
    # 'tenement_type': {
    #     'source': VocabSource.FILE,
    #     'title': 'Tenement Type'
    # },
    'Test_Rock_Types_Vocabulary': {
        'source': VocabSource.VOCBENCH,
        'title': 'Test Rock Types'
    },
    'contact_type': {
        'source': VocabSource.FILE,
        'title': 'Contact Type - File'
    },
    'stratigraphic_rank': {
        'source': VocabSource.FILE,
        'title': 'Stratigraphic Rank - File'
    }
}

#
# -- Startup tasks -----------------------------------------------------------------------------------------------------
#

# read in RDF vocab files on startup in vocab_files directory
FILE.init()
RVA.init()

# extend this instances' list of vocabs by using the known sources
VOCABS = {**VOCABS, **FILE.list_vocabularies()}  # picks up all vocab RDF (turtle) files in data/
# VOCABS = {**VOCABS, **VOCBENCH.list_vocabularies()}  # picks up all vocabs at the relevant VocBench instance


