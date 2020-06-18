from os import path
import tempfile

APP_DIR = path.dirname(path.dirname(path.realpath(__file__)))
SKIN_DIR = path.join(APP_DIR, "view")
TEMPLATES_DIR = path.join(SKIN_DIR, "templates")
STATIC_DIR = path.join(SKIN_DIR, "style")
LOGFILE = APP_DIR + "/flask.log"
DEBUG = True
VOCAB_CACHE_DIR = path.join(tempfile.gettempdir(), "vocprez", "cache")
VOCAB_CACHE_HOURS = (
    1  # Number of hours before cache is replaced (set to zero to always replace)
)
DEFAULT_LANGUAGE = "en"
SPARQL_QUERY_LIMIT = 2000  # Maximum number of results to return per SPARQL query
MAX_RETRIES = 2
RETRY_SLEEP_SECONDS = 10
SPARQL_TIMEOUT = 60
LOCAL_URLS = True  # Parameter governing whether URLs shown are local or external


#
#   Vocabulary data sources
#
# Here is the list of vocabulary sources that this instance uses. FILE, SPARQL, RVA & VOCBENCH are implemented already
# and are on by default (e.g. VOCBENCH = None) but other sources, such as GitHub can be added. To enable them, add a new
# like like VocBench.XXX = None
class VocabSource:
    FILE = "FILE"
    SPARQL = "SPARQL"
    RVA = "RVA"
    VOCBENCH = "VOCBENCH"
    GITHUB = "GITHUB"


# vocab source instances - the particular sources used by this instance
VOCAB_SOURCES = {
    # an example of querying the ARDC RVA vocab system (https://vocabs.ands.org.au)
    "rva": {
        "source": VocabSource.RVA,
        "api_endpoint": "",
        "vocabs": [
            {"ardc_id": -99, "uri": "",},
            {"ardc_id": -99, "uri": "",},
            {"ardc_id": -99, "uri": "",},
        ],
    },
    # an example of a SPARQL source
    "ga": {
        "source": VocabSource.SPARQL,
        "sparql_endpoint": "http://some-sparql-server.org",
        "sparql_username": "",
        "sparql_password": "",
        "uri_filter_regex": ".*"
    },
}
