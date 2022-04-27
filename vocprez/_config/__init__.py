from os import path

APP_DIR = path.dirname(path.dirname(path.realpath(__file__)))
SKIN_DIR = path.join(APP_DIR, "view")
TEMPLATES_DIR = path.join(SKIN_DIR, "templates")
STATIC_DIR = path.join(SKIN_DIR, "style")
LOGFILE = APP_DIR + "/vocprez.log"
CACHE_FILE = path.join(APP_DIR, "cache", "DATA.p")
CACHE_HOURS = 1
DEFAULT_LANGUAGE = "en"
SPARQL_QUERY_LIMIT = 2000  # Maximum number of results to return per SPARQL query
MAX_RETRIES = 2
RETRY_SLEEP_SECONDS = 10
SPARQL_TIMEOUT = 60
PORT = 5000

#
#   Vocabulary data sources
#
# Here is the list of vocabulary sources that this instance uses. FILE, SPARQL, RVA & VOCBENCH are implemented already
# and are on by default (e.g. VOCBENCH = None) but other sources, such as GitHub can be added. To enable them, add a new
# like like VocBench.XXX = None
class VocabSource:
    FILE = "FILE"
    SPARQL = "SPARQL"
    OGCSPARQL = "OGCSPARQL"
    RVA = "RVA"
    VOCBENCH = "VOCBENCH"
    GITHUB = "GITHUB"


# BEGIN Instance Vars
SYSTEM_URI_BASE = "http://localhost:5000"
SYSTEM_BASE_URI = SYSTEM_URI_BASE
USE_SYSTEM_URIS = True
USE_ABS_ALT_URI = True
DEBUG = False
SPARQL_ENDPOINT = "http://defs-dev.opengis.net:8080/rdf4j-server/repositories/profiles"
SPARQL_USERNAME = ""
SPARQL_PASSWORD = ""


SOURCE_NAME = "nvs"
# END Instance Vars

DATA_SOURCES = {
    # example SPARQL source configured using variables in "Instance Vars" above
    SOURCE_NAME: {
        "source": VocabSource.SPARQL,
        "sparql_endpoint": SPARQL_ENDPOINT,
        "sparql_username": SPARQL_USERNAME,
        "sparql_password": SPARQL_PASSWORD,
    },
}

# BEGIN Vocabs list info
VOCS_URI = "http://www.opengis.net/def"
VOCS_TITLE = "OGC Vocabularies"
VOCS_DESC = "Definitions registered by OGC standardisation activities or hosted on behalf of related organisations."
# END Vocabs list info
