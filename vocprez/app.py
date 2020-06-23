import io
import json
import re
import requests
from rdflib import Graph, URIRef
from vocprez import __version__
from flask import (
    Flask,
    Response,
    request,
    render_template,
    Markup,
    g,
    redirect,
    url_for,
)
from vocprez.model import *
from vocprez import _config as config
import markdown
from vocprez.source.utils import cache_read, cache_write, sparql_query
from pyldapi import Renderer, ContainerRenderer
import datetime
import logging
import vocprez.source as source

app = Flask(
    __name__, template_folder=config.TEMPLATES_DIR, static_folder=config.STATIC_DIR
)


class VbException(Exception):
    pass


@app.before_request
def before_request():
    """
    Runs before every request and populates vocab index either from disk (VOCABS.p) or from a complete reload by
    calling collect() for each of the vocab sources defined in config/__init__.py -> VOCAB_SOURCES
    :return: nothing
    """
    # check to see if g.VOCABS exists, if so, do nothing
    if hasattr(g, "VOCABS"):
        return

    # we have no g.VOCABS so try and load it from a pickled VOCABS.p file
    g.VOCABS = cache_read("VOCABS.p")

    if not g.VOCABS:
        # we haven't been able to load from VOCABS.p so run collect() on each vocab source to recreate it

        # check each vocab source and,
        # using the appropriate class (from details['source']),
        # load all the vocabs from it into this session's (g) VOCABS variable
        g.VOCABS = {}
        for source_details in config.VOCAB_SOURCES.values():
            # run the appropriate collect() for the given source(es)
            getattr(source, source_details["source"]).collect(source_details)

        # also load all vocabs into VOCABS.p on disk for future use
        cache_write(g.VOCABS, "VOCABS.p")


@app.context_processor
def context_processor():
    """
    A set of global variables available to 'globally' for jinja templates.
    :return: A dictionary of variables
    :rtype: dict
    """
    import vocprez.source.utils as u
    return dict(utils=u)


@app.context_processor
def inject_date():
    return {"date": datetime.date.today()}


@app.route("/")
def index():
    return render_template(
        "index.html",
        version=__version__,
        title="GA VocPrez",
        navs={},
        config=config,
        voc_key=get_a_vocab_source_key(),
    )


@app.route("/vocabulary/")
def vocabularies():
    page = (
        int(request.values.get("page")) if request.values.get("page") is not None else 1
    )
    per_page = (
        int(request.values.get("per_page"))
        if request.values.get("per_page") is not None
        else 20
    )
    #
    # # TODO: replace this logic with the following
    # #   1. read all static vocabs from g.VOCABS
    # get this instance's list of vocabs
    vocabs = []  # local copy (to this request) for sorting
    for k, voc in g.VOCABS.items():
        vocabs.append((url_for("vocabulary", vocab_id=k), voc.title))
    vocabs.sort(key=lambda tup: tup[1])
    total = len(g.VOCABS.items())
    #
    # # Search
    # query = request.values.get("search")
    # results = []
    # if query:
    #     for m in match(vocabs, query):
    #         results.append(m)
    #     vocabs[:] = results
    #     vocabs.sort(key=lambda v: v.title)
    #     total = len(vocabs)
    #
    # # generate vocabs list for requested page and per_page
    start = (page - 1) * per_page
    end = start + per_page
    vocabs = vocabs[start:end]
    #
    # # render the list of vocabs
    # return SkosRegisterRenderer(
    #     request,
    #     [],
    #     vocabs,
    #     "Vocabularies",
    #     total,
    #     search_query=query,
    #     search_enabled=True,
    #     vocabulary_url=["http://www.w3.org/2004/02/skos/core#ConceptScheme"],
    # ).render()

    return ContainerRenderer(
        request,
        'https://pid.geoscience.gov.au/def/voc/',
        'Vocabularies',
        'Vocabularies published by Geoscience Australia from multiple sources',
        None,
        None,
        vocabs,
        total
    ).render()


@app.route("/vocabularies/<string:set_id>/")
def vocabularies_set(set_id):
    sets = [
        "EarthResourceML",
        "GeoSciML"
    ]
    if set_id not in sets:
        return render_vocprez_response(
            "The vocab set ID supplied is invalid. It must be one of {}".format(", ".join(sets))
        )

    page = (
        int(request.values.get("page")) if request.values.get("page") is not None else 1
    )
    per_page = (
        int(request.values.get("per_page"))
        if request.values.get("per_page") is not None
        else 20
    )

    # get this set's list of vocabs
    vocabs = []
    q = """
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX dcterms: <http://purl.org/dc/terms/>
        
        SELECT ?uri ?pl ?prov
        WHERE {{
            ?uri a skos:ConceptScheme ;
                 skos:prefLabel ?pl ;
                 dcterms:provenance ?prov .
        
                FILTER REGEX(?prov, "{}", "i")
        }}
        ORDER BY ?pl
    """.format(set_id)

    desc = ""
    concept_schemes = sparql_query(
        q,
        config.VOCAB_SOURCES["cgi"]["sparql_endpoint"],
        config.VOCAB_SOURCES["cgi"].get("sparql_username"),
        config.VOCAB_SOURCES["cgi"].get("sparql_password"),
    )

    assert concept_schemes is not None, "Unable to query for ConceptSchemes"

    for cs in concept_schemes:
        vocabs.append((
            str(url_for("vocabulary", vocab_id=cs["uri"]["value"].split("/")[-1])),
            str(cs["pl"]["value"])
        ))
        desc = str(cs["prov"]["value"])

    start = (page - 1) * per_page
    end = start + per_page
    vocabs = vocabs[start:end]

    return ContainerRenderer(
        request,
        request.base_url,
        set_id + ' Vocabularies',
        desc,
        None,
        None,
        vocabs,
        len(vocabs)
    ).render()


@app.route("/vocabulary/<string:vocab_id>/")
def vocabulary(vocab_id):
    # check the vocab id is valid
    if vocab_id not in g.VOCABS.keys():
        return render_invalid_vocab_id_response()

    # get vocab details using appropriate source handler
    try:
        vocab = getattr(source, g.VOCABS[vocab_id].data_source)(vocab_id, request, language=request.values.get("lang")).get_vocabulary()
    except VbException as e:
        return render_vb_exception_response(e)

    return VocabularyRenderer(request, vocab).render()


@app.route("/vocabulary/<vocab_id>/concept/")
def concepts(vocab_id):
    language = request.values.get("lang") or config.DEFAULT_LANGUAGE

    if vocab_id not in g.VOCABS.keys():
        return render_invalid_vocab_id_response()

    vocab_source = getattr(source, g.VOCABS[vocab_id].data_source)(vocab_id, request, language=config.DEFAULT_LANGUAGE)
    concepts = vocab_source.list_concepts()
    concepts.sort(key=lambda x: x["title"])
    total = len(concepts)

    # Search
    query = request.values.get("search")
    results = []
    if query:
        for m in match(concepts, query):
            results.append(m)
        concepts[:] = results
        concepts.sort(key=lambda x: x["title"])
        total = len(concepts)

    page = (
        int(request.values.get("page")) if request.values.get("page") is not None else 1
    )
    per_page = (
        int(request.values.get("per_page"))
        if request.values.get("per_page") is not None
        else 20
    )
    start = (page - 1) * per_page
    end = start + per_page
    concepts = concepts[start:end]

    test = SkosRegisterRenderer(
        request=request,
        navs=[],
        members=concepts,
        register_item_type_string=g.VOCABS[vocab_id].title + " concepts",
        total=total,
        search_enabled=True,
        search_query=query,
        vocabulary_url=[request.url_root + "vocabulary/" + vocab_id],
        vocab_id=vocab_id,
    )
    return test.render()


@app.route("/collection/")
def collections():
    return render_template(
        "register.html",
        version=__version__,
        title="Collections",
        register_class="Collections",
        navs={}
    )


@app.route("/object")
def object():
    """
    This is the general RESTful endpoint and corresponding Python function to handle requests for individual objects,
    be they a Vocabulary, Concept Scheme, Collection or Concept. Only those 4 classes of object are supported for the
    moment.

    An HTTP URI query string argument parameter 'vocab_id' must be supplied, indicating the vocab this object is within
    An HTTP URI query string argument parameter 'uri' must be supplied, indicating the URI of the object being requested

    :return: A Flask Response object
    :rtype: :class:`flask.Response`
    """
    language = request.values.get("lang") or config.DEFAULT_LANGUAGE
    vocab_id = request.values.get("vocab_id")
    uri = request.values.get("uri")
    _view = request.values.get("_view")
    _format = request.values.get("_format")

    # check this vocab ID is known
    if vocab_id not in g.VOCABS.keys():
        return Response(
            "The vocabulary ID you've supplied is not known. Must be one of:\n "
            + "\n".join(g.VOCABS.keys()),
            status=400,
            mimetype="text/plain",
        )

    if uri is None:
        return Response(
            "A Query String Argument 'uri' must be supplied for this endpoint, "
            "indicating an object within a vocabulary",
            status=400,
            mimetype="text/plain",
        )

    # vocab_source = Source(vocab_id, request, language)
    vocab_source = getattr(source, g.VOCABS[vocab_id].data_source)(vocab_id, request, language=config.DEFAULT_LANGUAGE)

    try:
        # TODO reuse object within if, rather than re-loading graph
        c = vocab_source.get_object_class()

        if c == "http://www.w3.org/2004/02/skos/core#Concept":
            concept = vocab_source.get_concept()
            return ConceptRenderer(request, concept).render()

        elif c == "http://www.w3.org/2004/02/skos/core#ConceptScheme":
            vocabulary = vocab_source.get_vocabulary()

            return VocabularyRenderer(request, vocabulary).render()

        elif c == "http://www.w3.org/2004/02/skos/core#Collection":
            collection = vocab_source.get_collection(uri)
            return CollectionRenderer(request, collection).render()
        else:
            return render_invalid_object_class_response(vocab_id, uri, c)
    except VbException as e:
        return render_vb_exception_response(e)


@app.route("/about")
def about():
    import os

    # using basic Markdown method from http://flask.pocoo.org/snippets/19/
    with open(os.path.join(config.APP_DIR, "..", "README.md")) as f:
        content = f.read()

    # make images come from wed dir
    content = content.replace(
        "vocprez/view/style/", request.url_root + "style/"
    )
    content = Markup(markdown.markdown(content))

    return render_template(
        "about.html",
        version=__version__,
        title="About",
        navs={},
        content=content
    )


# the SPARQL UI
@app.route("/sparql", methods=["GET", "POST"])
def sparql():
    return render_template(
        "sparql.html",
        version=__version__,
    )


# the SPARQL endpoint under-the-hood
@app.route("/endpoint", methods=["GET", "POST"])
def endpoint():
    """
    TESTS

    Form POST:
    curl -X POST -d query="PREFIX%20skos%3A%20%3Chttp%3A%2F%2Fwww.w3.org%2F2004%2F02%2Fskos%2Fcore%23%3E%0ASELECT%20*%20WHERE%20%7B%3Fs%20a%20skos%3AConceptScheme%20.%7D" http://localhost:5000/endpoint

    Raw POST:
    curl -X POST -H 'Content-Type: application/sparql-query' --data-binary @query.sparql http://localhost:5000/endpoint
    using query.sparql:
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        SELECT * WHERE {?s a skos:ConceptScheme .}

    GET:
    curl http://localhost:5000/endpoint?query=PREFIX%20skos%3A%20%3Chttp%3A%2F%2Fwww.w3.org%2F2004%2F02%2Fskos%2Fcore%23%3E%0ASELECT%20*%20WHERE%20%7B%3Fs%20a%20skos%3AConceptScheme%20.%7D

    GET CONSTRUCT:
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        CONSTRUCT {?s a rdf:Resource}
        WHERE {?s a skos:ConceptScheme}
    curl -H 'Accept: application/ld+json' http://localhost:5000/endpoint?query=PREFIX%20rdf%3A%20%3Chttp%3A%2F%2Fwww.w3.org%2F1999%2F02%2F22-rdf-syntax-ns%23%3E%0APREFIX%20skos%3A%20%3Chttp%3A%2F%2Fwww.w3.org%2F2004%2F02%2Fskos%2Fco23%3E%0ACONSTRUCT%20%7B%3Fs%20a%20rdf%3AResource%7D%0AWHERE%20%7B%3Fs%20a%20skos%3AConceptScheme%7D

    """
    logging.debug("request: {}".format(request.__dict__))

    # TODO: Find a slightly less hacky way of getting the format_mimetime value
    format_mimetype = request.__dict__["environ"]["HTTP_ACCEPT"]

    # Query submitted
    if request.method == "POST":
        """Pass on the SPARQL query to the underlying endpoint defined in config
        """
        if "application/x-www-form-urlencoded" in request.content_type:
            """
            https://www.w3.org/TR/2013/REC-sparql11-protocol-20130321/#query-via-post-urlencoded

            2.1.2 query via POST with URL-encoded parameters

            Protocol clients may send protocol requests via the HTTP POST method by URL encoding the parameters. When
            using this method, clients must URL percent encode all parameters and include them as parameters within the
            request body via the application/x-www-form-urlencoded media type with the name given above. Parameters must
            be separated with the ampersand (&) character. Clients may include the parameters in any order. The content
            type header of the HTTP request must be set to application/x-www-form-urlencoded.
            """
            if (
                    request.values.get("query") is None
                    or len(request.values.get("query")) < 5
            ):
                return Response(
                    "Your POST request to the SPARQL endpoint must contain a 'query' parameter if form posting "
                    "is used.",
                    status=400,
                    mimetype="text/plain",
                )
            else:
                query = request.values.get("query")
        elif "application/sparql-query" in request.content_type:
            """
            https://www.w3.org/TR/2013/REC-sparql11-protocol-20130321/#query-via-post-direct

            2.1.3 query via POST directly

            Protocol clients may send protocol requests via the HTTP POST method by including the query directly and
            unencoded as the HTTP request message body. When using this approach, clients must include the SPARQL query
            string, unencoded, and nothing else as the message body of the request. Clients must set the content type
            header of the HTTP request to application/sparql-query. Clients may include the optional default-graph-uri
            and named-graph-uri parameters as HTTP query string parameters in the request URI. Note that UTF-8 is the
            only valid charset here.
            """
            query = request.data.decode("utf-8")  # get the raw request
            if query is None:
                return Response(
                    "Your POST request to this SPARQL endpoint must contain the query in plain text in the "
                    "POST body if the Content-Type 'application/sparql-query' is used.",
                    status=400,
                )
        else:
            return Response(
                "Your POST request to this SPARQL endpoint must either the 'application/x-www-form-urlencoded' or"
                "'application/sparql-query' ContentType.",
                status=400,
            )

        try:
            if "CONSTRUCT" in query:
                format_mimetype = "text/turtle"
                return Response(
                    sparql_query2(
                        query, format_mimetype=format_mimetype
                    ),
                    status=200,
                    mimetype=format_mimetype,
                )
            else:
                return Response(
                    sparql_query2(query, format_mimetype),
                    status=200,
                )
        except ValueError as e:
            return Response(
                "Input error for query {}.\n\nError message: {}".format(query, str(e)),
                status=400,
                mimetype="text/plain",
            )
        except ConnectionError as e:
            return Response(str(e), status=500)
    else:  # GET
        if request.args.get("query") is not None:
            # SPARQL GET request
            """
            https://www.w3.org/TR/2013/REC-sparql11-protocol-20130321/#query-via-get

            2.1.1 query via GET

            Protocol clients may send protocol requests via the HTTP GET method. When using the GET method, clients must
            URL percent encode all parameters and include them as query parameter strings with the names given above.

            HTTP query string parameters must be separated with the ampersand (&) character. Clients may include the
            query string parameters in any order.

            The HTTP request MUST NOT include a message body.
            """
            query = request.args.get("query")
            if "CONSTRUCT" in query:
                acceptable_mimes = [x for x in Renderer.RDF_MEDIA_TYPES]
                best = request.accept_mimetypes.best_match(acceptable_mimes)
                query_result = sparql_query2(
                    query, format_mimetype=best
                )
                file_ext = {
                    "text/turtle": "ttl",
                    "application/rdf+xml": "rdf",
                    "application/ld+json": "json",
                    "text/n3": "n3",
                    "application/n-triples": "nt",
                }
                return Response(
                    query_result,
                    status=200,
                    mimetype=best,
                    headers={
                        "Content-Disposition": "attachment; filename=query_result.{}".format(
                            file_ext[best]
                        )
                    },
                )
            else:
                query_result = sparql_query2(query)
                return Response(
                    query_result, status=200, mimetype="application/sparql-results+json"
                )
        else:
            # SPARQL Service Description
            """
            https://www.w3.org/TR/sparql11-service-description/#accessing

            SPARQL services made available via the SPARQL Protocol should return a service description document at the
            service endpoint when dereferenced using the HTTP GET operation without any query parameter strings
            provided. This service description must be made available in an RDF serialization, may be embedded in
            (X)HTML by way of RDFa, and should use content negotiation if available in other RDF representations.
            """

            acceptable_mimes = [x for x in Renderer.RDF_MEDIA_TYPES] + ["text/html"]
            best = request.accept_mimetypes.best_match(acceptable_mimes)
            if best == "text/html":
                # show the SPARQL query form
                return redirect(url_for("sparql"))
            elif best is not None:
                for item in Renderer.RDF_MEDIA_TYPES:
                    if item == best:
                        rdf_format = best
                        return Response(
                            get_sparql_service_description(
                                rdf_format=rdf_format
                            ),
                            status=200,
                            mimetype=best,
                        )

                return Response(
                    "Accept header must be one of " + ", ".join(acceptable_mimes) + ".",
                    status=400,
                )
            else:
                return Response(
                    "Accept header must be one of " + ", ".join(acceptable_mimes) + ".",
                    status=400,
                )


def get_sparql_service_description(rdf_format="turtle"):
    """Return an RDF description of PROMS' read only SPARQL endpoint in a requested format

    :param rdf_format: 'turtle', 'n3', 'xml', 'json-ld'
    :return: string of RDF in the requested format
    """
    sd_ttl = """
        @prefix rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        @prefix sd:     <http://www.w3.org/ns/sparql-service-description#> .
        @prefix sdf:    <http://www.w3.org/ns/formats/> .
        @prefix void: <http://rdfs.org/ns/void#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        <http://gnafld.net/sparql>
            a                       sd:Service ;
            sd:endpoint             <%(BASE_URI)s/function/sparql> ;
            sd:supportedLanguage    sd:SPARQL11Query ; # yes, read only, sorry!
            sd:resultFormat         sdf:SPARQL_Results_JSON ;  # yes, we only deliver JSON results, sorry!
            sd:feature sd:DereferencesURIs ;
            sd:defaultDataset [
                a sd:Dataset ;
                sd:defaultGraph [
                    a sd:Graph ;
                    void:triples "100"^^xsd:integer
                ]
            ]
        .
    """
    g = Graph().parse(io.StringIO(sd_ttl), format="turtle")
    rdf_formats = list(set([x for x in Renderer.RDF_SERIALIZER_TYPES_MAP]))
    if rdf_format[0][1] in rdf_formats:
        return g.serialize(format=rdf_format[0][1])
    else:
        raise ValueError(
            "Input parameter rdf_format must be one of: " + ", ".join(rdf_formats)
        )


def sparql_query2(query, format_mimetype="application/json"):
    """ Make a SPARQL query"""
    logging.debug("sparql_query2: {}".format(query))
    data = query

    headers = {
        "Content-Type": "application/sparql-query",
        "Accept": format_mimetype,
        "Accept-Encoding": "UTF-8",
    }
    if hasattr(config, "SPARQL_USERNAME") and hasattr(config, "SPARQL_PASSWORD"):
        auth = (config.SPARQL_USERNAME, config.SPARQL_PASSWORD)
    else:
        auth = None

    try:
        logging.debug(
            "endpoint={}\ndata={}\nheaders={}".format(
                config.SPARQL_ENDPOINT, data, headers
            )
        )
        r = requests.post(
            config.SPARQL_ENDPOINT, auth=auth, data=data, headers=headers, timeout=60
        )
        logging.debug("response: {}".format(r.__dict__))
        return r.content.decode("utf-8")
    except Exception as e:
        raise e


def render_invalid_vocab_id_response():
    msg = (
        """The vocabulary ID that was supplied was not known. It must be one of these: \n\n* """
        + "\n* ".join(g.VOCABS.keys())
    )
    msg = Markup(markdown.markdown(msg))
    return render_template(
        "error.html",
        version=__version__,
        title="Error - invalid vocab id",
        heading="Invalid Vocab ID",
        msg=msg,
    )


def render_vocprez_response(message):
    return render_template(
        "error.html",
        version=__version__,
        title="Error - invalid vocab id",
        heading="Invalid Vocab ID",
        msg=message,
    )


def render_vb_exception_response(e):
    e = json.loads(str(e))
    msg = e["stresponse"]["msg"]
    if "not an open project" in msg:
        invalid_vocab_id = msg.split("not an open project:")[-1]
        msg = "The VocBench instance returned with an error: **{}** is not an open project.".format(
            invalid_vocab_id
        )
        msg = Markup(markdown.markdown(msg))
    return render_template(
        "error.html",
        version=__version__,
        title="Error",
        heading="VocBench Error",
        msg=msg
    )


def render_invalid_object_class_response(vocab_id, uri, c_type):
    msg = """No valid *Object Class URI* found for vocab_id **{}** and uri **{}** 
    
Instead, found **{}**.""".format(
        vocab_id, uri, c_type
    )
    msg = Markup(markdown.markdown(msg))
    return render_template(
        "error.html",
        version=__version__,
        title="Error - Object Class URI",
        heading="Concept Class Type Error",
        msg=msg,
    )


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


def make_title(s):
    # make title from URI
    title = " ".join(s.split("#")[-1].split("/")[-1].split("_")).title()

    # replace dashes and periods with whitespace
    title = re.sub("[-.]+", " ", title).title()

    return title


def parse_markdown(s):
    return markdown.markdown(s)


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


# run the Flask app
if __name__ == "__main__":
    logging.basicConfig(
        filename=config.LOGFILE,
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
        format="%(asctime)s %(levelname)s %(filename)s:%(lineno)s %(message)s",
    )

    import os
    sources_folder = os.path.join(config.APP_DIR, "source")
    main_module = "__init__"
    import importlib

    def ge_sources():
        plugins = []
        possible_sources = os.listdir(sources_folder)
        for i in possible_sources:
            location = os.path.join(sources_folder, i)
            info = importlib.find_module(main_module, [location])
            plugins.append({"name": i, "info": info})
        return plugins

    def load_plugin(plugin):
        return importlib.load_module(main_module, *plugin["info"])

    app.run(debug=config.DEBUG, threaded=True, port=5000)