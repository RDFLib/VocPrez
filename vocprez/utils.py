import base64
import logging
import os
import pickle
import time
import markdown
import requests
from SPARQLWrapper import SPARQLWrapper, JSON, BASIC
from flask import g
from rdflib import Graph, SKOS, URIRef
from xml.dom.minidom import Document as xml_Document
import urllib
import re
from bs4 import BeautifulSoup
import vocprez._config as config
from . import source


__all__ = [
    "cache_write",
    "url_encode",
    "sparql_query",
    "draw_concept_hierarchy",
    "get_graph",
    "url_decode"
]


def cache_write(cache_object):
    """
    Function to write object to cache if cache file is older than cache_hours.
    """
    logging.debug("cache_write({})".format(cache_object))

    # create dir if not there
    if not os.path.isdir(os.path.dirname(config.CACHE_FILE)):
        os.makedirs(os.path.dirname(config.CACHE_FILE))

    with open(config.CACHE_FILE, "wb") as cache_file:
        pickle.dump(cache_object, cache_file)


def cache_clear():
    logging.debug("cache_clear()")

    # clear the Flask cache
    if hasattr(g, "VOCABS"):
        g.VOCABS = None

    # remove the pickle cache
    if os.path.isfile(config.CACHE_FILE):
        os.unlink(config.CACHE_FILE)


def cache_load():
    logging.debug("cache_load()")

    if config.DEBUG:
        logging.debug("DEBUG so purge cache")
        cache_clear()

    if hasattr(g, "VOCABS"):
        logging.debug("have g, doing nothing")
        pass
    elif os.path.isfile(config.CACHE_FILE):
        logging.debug("rebuild g from CACHE_FILE")
        g.VOCABS = {}
        cache_file_age = time.time() - os.stat(config.CACHE_FILE).st_mtime
        if cache_file_age < config.CACHE_HOURS * 3600:
            with open(config.CACHE_FILE, "rb") as f:
                g.VOCABS = pickle.load(f)
        else:  # old cache file
            logging.debug("rebuild g & CACHE_FILE from collect() methods")
            cache_clear()

            for source_details in config.DATA_SOURCES.values():
                getattr(source, source_details["source"]).collect(source_details)
            cache_write(g.VOCABS)
    else:
        logging.debug("build g & CACHE_FILE from collect() methods")
        g.VOCABS = {}
        for source_details in config.DATA_SOURCES.values():
            getattr(source, source_details["source"]).collect(source_details)
        cache_write(g.VOCABS)


def cache_reload():
    """Cache purging function used in multiple places"""
    logging.debug("cache_reload()")

    cache_clear()

    cache_load()


def draw_concept_hierarchy(hierarchy, request, vocab_uri):
        tab = "\t"
        previous_length = 1

        text = ""
        tracked_items = []
        for item in hierarchy:
            mult = None

            if item[0] > previous_length + 2:  # SPARQL query error on length value
                for tracked_item in tracked_items:
                    if tracked_item["name"] == item[3]:
                        mult = tracked_item["indent"] + 1

            if mult is None:
                found = False
                for tracked_item in tracked_items:
                    if tracked_item["name"] == item[3]:
                        found = True
                if not found:
                    mult = 0

            if mult is None:  # else: # everything is normal
                mult = item[0] - 1

            # Default to showing local URLs unless told otherwise
            if (not hasattr(config, "LOCAL_URLS")) or config.USE_SYSTEM_URIS:
                uri = (
                        request.url_root
                        + "object?vocab_uri="
                        + vocab_uri
                        + "&uri="
                        + url_encode(item[1])
                )
            else:
                uri = item[1]

            t = tab * mult + "* [" + item[2] + "](" + uri + ")\n"
            text += t
            previous_length = mult
            tracked_items.append({"name": item[1], "indent": mult})

        return markdown.markdown(text)


def render_concept_tree(html_doc):
    soup = BeautifulSoup(html_doc, "html.parser")

    # concept_hierarchy = soup.find(id='concept-hierarchy')

    uls = soup.find_all("ul")

    for i, ul in enumerate(uls):
        # Don't add HTML class nested to the first 'ul' found.
        if not i == 0:
            ul["class"] = "nested"
            if ul.parent.name == "li":
                temp = BeautifulSoup(str(ul.parent.a.extract()), "html.parser")
                ul.parent.insert(
                    0, BeautifulSoup('<span class="caret">', "html.parser")
                )
                ul.parent.span.insert(0, temp)
    return soup


def get_graph(endpoint, q, sparql_username=None, sparql_password=None):
    """
    Function to return an rdflib Graph object containing the results of a query
    """
    result_graph = Graph()
    response = submit_sparql_query(
        endpoint,
        q,
        sparql_username=sparql_username,
        sparql_password=sparql_password,
        accept_format="xml",
    )
    result_graph.parse(data=response)
    return result_graph


def sparql_query(q, sparql_endpoint=config.SPARQL_ENDPOINT, sparql_username=None, sparql_password=None):
    sparql = SPARQLWrapper(sparql_endpoint)
    sparql.setQuery(q)
    sparql.setReturnFormat(JSON)

    if sparql_username and sparql_password:
        sparql.setHTTPAuth(BASIC)
        sparql.setCredentials(sparql_username, sparql_password)

    try:
        r = sparql.queryAndConvert()

        if isinstance(r, xml_Document):
            def getText(node):
                nodelist = node.childNodes
                result = []
                for node in nodelist:
                    if node.nodeType == node.TEXT_NODE:
                        result.append(node.data)
                return ''.join(result)

            results = []
            for result in r.getElementsByTagName('result'):
                bindings = {}
                for binding in result.getElementsByTagName('binding'):
                    for val in binding.childNodes:
                        bindings[binding.getAttribute("name")] = {
                            "type": "uri" if val.tagName == "uri" else "literal",
                            "value": getText(val)
                        }
                results.append(bindings)
            return results
        elif isinstance(r, dict):
            # JSON
            return r["results"]["bindings"]
        else:
            raise Exception("Could not convert results from SPARQL endpoint")
    except Exception as e:
        logging.debug("SPARQL query failed: {}".format(e))
        logging.debug(
            "endpoint={}\nsparql_username={}\nsparql_password={}\n{}".format(
               q,  sparql_endpoint, sparql_username, sparql_password
            )
        )
        return None


def submit_sparql_query(
        endpoint, q, sparql_username=None, sparql_password=None, accept_format="json"
):
    """
    Function to submit a sparql query and return the textual response
    """
    accept_format = {
                        "json": "application/json",
                        "xml": "application/rdf+xml",
                        "turtle": "application/turtle",
                    }.get(accept_format) or "application/json"
    headers = {
        "Accept": accept_format,
        "Content-Type": "application/sparql-query",
        "Accept-Encoding": "UTF-8",
    }
    if sparql_username and sparql_password:
        # logging.debug('Authenticating with username {} and password {}'.format(sparql_username, sparql_password))
        headers["Authorization"] = "Basic " + base64.encodebytes(
            "{}:{}".format(sparql_username, sparql_password).encode("utf-8")
        ).strip().decode("utf-8")

    params = None

    retries = 0
    while True:
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                params=params,
                data=q,
                timeout=config.SPARQL_TIMEOUT,
            )
            # logging.debug('Response content: {}'.format(str(response.content)))
            assert (
                    response.status_code == 200
            ), "Response status code {} != 200".format(response.status_code)
            return response.text
        except Exception as e:
            logging.warning("SPARQL query failed: {}".format(e))
            retries += 1
            if retries <= config.MAX_RETRIES:
                time.sleep(config.RETRY_SLEEP_SECONDS)
                continue  # Go around again
            else:
                break

    raise (BaseException("SPARQL query failed"))


def get_prefLabel_from_uri(uri):
    return " ".join(str(uri).split("#")[-1].split("/")[-1].split("_"))


def get_narrowers(uri, depth):
    """
    Recursively get all skos:narrower properties as a list.

    :param uri: URI node
    :param depth: The current depth
    :param g: The graph
    :return: list of tuples(tree_depth, uri, prefLabel)
    :rtype: list
    """
    depth += 1

    # Some RVA sources won't load on first try, so ..
    # if failed, try load again.
    g = None
    max_attempts = 10
    for i in range(max_attempts):
        try:
            g = Graph().parse(uri + ".ttl", format="turtle")
            break
        except:
            logging.warning(
                "Failed to load resource at URI {}. Attempt: {}.".format(uri, i + 1)
            )
    if not g:
        raise Exception(
            "Failed to load Graph from {}. Maximum attempts exceeded {}.".format(
                uri, max_attempts
            )
        )

    items = []
    for s, p, o in g.triples((None, SKOS.broader, URIRef(uri))):
        items.append((depth, str(s), get_prefLabel_from_uri(s)))
    items.sort(key=lambda x: x[2])
    count = 0
    for item in items:
        count += 1
        new_items = get_narrowers(item[1], item[0])
        items = items[:count] + new_items + items[count:]
        count += len(new_items)
    return items


def url_decode(s):
    try:
        return urllib.parse.unquote(s)
    except:
        pass


def url_encode(s):
    try:
        return urllib.parse.quote(s)
    except:
        pass


def make_title(s):
    # make title from URI
    title = " ".join(s.split("#")[-1].split("/")[-1].split("_")).title()

    # replace dashes and periods with whitespace
    title = re.sub("[-.]+", " ", title).title()

    return title


def version():
    from vocprez import __version__ as v
    return v


def is_email(email):
    """
    Check if the email is a valid email.
    :param email: The email to be tested.
    :return: True if the email matches the static regular expression, else false.
    :rtype: bool
    """
    pattern = r"[a-z0-9!#$%&'*+\/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+\/=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"
    return True if re.search(pattern, email) is not None else False


def strip_mailto(email):
    return email[7:]


def contains_mailto(email):
    if email[:7] == "mailto:":
        return True
    return False


def is_url(url):
    """
    Check if the url is a valid url.
    :param url: The url to be tested.
    :type url: str
    :return: True if the url passes the validation, else false.
    :rtype: bool
    """
    if isinstance(url, URIRef):
        return True

    pattern = re.compile(
        r"^(?:http|ftp)s?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain...
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )
    return True if re.search(pattern, url) is not None else False


def get_a_vocab_key():
    """
    Get the first key from the g.VOCABS dictionary.

    :return: Key name
    :rtype: str
    """
    try:
        return next(iter(g.VOCABS))
    except:
        return None


def get_a_vocab_source_key():
    """
    Get the first key from the config.VOCABS dictionary.

    :return: Key name
    :rtype: str
    """
    try:
        return next(iter(g.VOCABS))
    except:
        return None


def match(vocabs, query):
    """
    Generate a generator of vocabulary items that match the search query

    :param vocabs: The vocabulary list of items.
    :param query: The search query string.
    :return: A generator of words that match the search query.
    :rtype: generator
    """
    for word in vocabs:
        if query.lower() in word.title.lower():
            yield word


def parse_markdown(s):
    return markdown.markdown(s)


def get_system_uri(absolute_uri, system_uri_override):
    if system_uri_override is not None:
        return system_uri_override
    else:
        return "{}/object?uri={}".format(config.SYSTEM_URI_BASE, url_encode(absolute_uri))


def get_absolute_uri(uri):
    if "uri=" in uri:
        uri = uri.split("uri=")[1]
    return url_decode(uri)


def get_content_uri(uri, system_uri_override=None):
    if config.USE_SYSTEM_URIS:
        return get_system_uri(uri, system_uri_override)
    else:
        return get_absolute_uri(uri)


def get_pretty_mediatype(mediatype):
    MEDIATYPE_NAMES = {
        "text/html": "HTML",
        "application/json": "JSON",
        "text/turtle": "Turtle",
        "application/rdf+xml": "RDF/XML",
        "application/ld+json": "JSON-LD",
        "text/n3": "Notation-3",
        "application/n-triples": "N-Triples",
    }
    return MEDIATYPE_NAMES.get(mediatype, mediatype)


def get_status_label(mediatype):
    STATUSES = {
        "http://www.opengis.net/def/status/accepted": "accepted",
        "http://www.opengis.net/def/status/deprecated": "deprecated",
        "http://www.opengis.net/def/status/experimental": "experimental",
        "http://www.opengis.net/def/status/invalid": "invalid",
        "http://www.opengis.net/def/status/notAccepted": "notAccepted",
        "http://www.opengis.net/def/status/reserved": "reserved",
        "http://www.opengis.net/def/status/retired": "retired",
        "http://www.opengis.net/def/status/stable": "stable",
        "http://www.opengis.net/def/status/submitted": "submitted",
        "http://www.opengis.net/def/status/superseded": "superseded",
        "http://www.opengis.net/def/status/valid": "valid",
    }
    return STATUSES.get(mediatype, mediatype)
