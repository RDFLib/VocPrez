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
VB_ENDPOINT = 'http://vocbench.gsq.cat/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services'
VB_USER = 'nicholas.car@csiro.au'
VB_PASSWORD = 'vocaliser'

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
        'title': 'GA Geologic Unit Type',
        'sparql': 'http://vocabs.ands.org.au/repository/api/sparql/ga_geologic-unit-type_v0-1',
        'download': 'https://vocabs.ands.org.au/registry/api/resource/downloads/196/ga_geologic-unit-type_v0-1.ttl'
    },
    #'rva-55': {
    #    'source': VocabSource.RVA,
    #    'title': 'CGI Stratigraphic Rank',
    #    'sparql': 'http://vocabs.ands.org.au/repository/api/sparql/ga_stratigraphic-rank_v0-1',
    #    'download': 'https://vocabs.ands.org.au/registry/api/resource/downloads/217/ga_stratigraphic-rank_v0-1.ttl'
    #},
    'rva-57': {
        'source': VocabSource.RVA,
        'title': 'CGI Stratigraphic Rank',
        'sparql': 'http://vocabs.ands.org.au/repository/api/sparql/ga_stratigraphic-rank_v0-1',
        'download': 'https://vocabs.ands.org.au/registry/api/resource/downloads/217/ga_stratigraphic-rank_v0-1.ttl'
    },
    #'rva-196': {
    #    'source': VocabSource.RVA,
    #    'title': 'CGI Stratigraphic Rank',
    #    'sparql': 'http://vocabs.ands.org.au/repository/api/sparql/ga_stratigraphic-rank_v0-1',
    #    'download': 'https://vocabs.ands.org.au/registry/api/resource/downloads/217/ga_stratigraphic-rank_v0-1.ttl'
    #},
    'age-units': {
        'source': VocabSource.VOCBENCH,
        'title': 'Age Units'
    },
    'bore-types': {
        'source': VocabSource.VOCBENCH,
        'title': 'Bore Types'
    },
    'borehole-status': {
        'source': VocabSource.VOCBENCH,
        'title': 'Borehole Status'
    },
    'Borehole_Inclination': {
        'source': VocabSource.VOCBENCH,
        'title': 'Borehole Inclination'
    },
    'dataset-themes': {
        'source': VocabSource.VOCBENCH,
        'title': 'Dataset Themes'
    },
    'geochemical-exploration': {
        'source': VocabSource.VOCBENCH,
        'title': 'Geochemical Exploration'
    },
    'geophysical-survey': {
        'source': VocabSource.VOCBENCH,
        'title': 'Geophysical Survey'
    },
    'lithology': {
        'source': VocabSource.VOCBENCH,
        'title': 'Lithology'
    },
    'material-type': {
        'source': VocabSource.VOCBENCH,
        'title': 'Material Type'
    },
    'method-type': {
        'source': VocabSource.VOCBENCH,
        'title': 'Method Type'
    },
    'mineral-exploration': {
        'source': VocabSource.VOCBENCH,
        'title': 'Mineral Exploration'
    },
    'petroleum-exploration': {
        'source': VocabSource.VOCBENCH,
        'title': 'Petroleum Exploration'
    },
    'sample-type': {
        'source': VocabSource.VOCBENCH,
        'title': 'Sample Type'
    },
    'start-type': {
        'source': VocabSource.VOCBENCH,
        'title': 'Start Type'
    },
    'test-rock-types': {
        'source': VocabSource.VOCBENCH,
        'title': 'Test Rock Types'
    },

    # Used by pytest
    'contact_type': {
        'source': VocabSource.FILE,
        'title': 'Contact Type (file)'
    }
}