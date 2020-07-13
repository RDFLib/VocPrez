import sys
sys.path.insert(0, '../../')
sys.path.insert(0, '../vocprez/')

import io
import json
import requests
from rdflib import Graph
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
from vocprez.source.utils import cache_read, cache_write, sparql_query
from pyldapi import Renderer, ContainerRenderer
import datetime
import logging
import vocprez.source as source
import markdown
import re


app = Flask(
    __name__, template_folder=config.TEMPLATES_DIR, static_folder=config.STATIC_DIR
)


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
    A set of variables available globally for all Jinja templates.
    :return: A dictionary of variables
    :rtype: dict
    """

    MEDIATYPE_NAMES = {
        "text/html": "HTML",
        "application/json": "JSON",
        "text/turtle": "Turtle",
        "application/rdf+xml": "RDX/XML",
        "application/ld+json": "JSON-LD",
        "text/n3": "Notation-3",
        "application/n-triples": "N-Triples",
    }

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
    import vocprez.source.utils as u
    return dict(
        utils=u,
        LOCAL_URLS=config.LOCAL_URLS,
        MEDIATYPE_NAMES=MEDIATYPE_NAMES,
        STATUSES=STATUSES
    )


@app.context_processor
def inject_date():
    return {"date": datetime.date.today()}


@app.route("/")
def index():
    return render_template(
        "index.html",
    )


@app.route("/vocab/")
def vocabularies():
    page = (
        int(request.values.get("page")) if request.values.get("page") is not None else 1
    )
    per_page = (
        int(request.values.get("per_page"))
        if request.values.get("per_page") is not None
        else 20
    )

    vocabs = []  # local copy (to this request) for sorting

    # get this instance's list of vocabs
    for k, voc in g.VOCABS.items():
        # respond to a filter
        if request.values.get("filter") is not None:
            if request.values.get("filter") in voc.title:
                vocabs.append((url_for("object", uri=k), voc.title))
        else:
            # no filter: list all
            vocabs.append((url_for("object", uri=k), voc.title))
    vocabs.sort(key=lambda tup: tup[1])
    total = len(vocabs)
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

    return ContainerRenderer(
        request,
        config.VOCS_URI if config.VOCS_URI is not None else url_for("vocabularies"),
        config.VOCS_TITLE if config.VOCS_TITLE is not None else 'Vocabularies',
        config.VOCS_DESC if config.VOCS_DESC is not None else None,
        None,
        None,
        vocabs,
        total
    ).render()


def translate_vocab_id_to_vocab_uri(vocab_id):
    vocab_ids = {}

    for x in g.VOCABS.keys():
        vocab_ids[x.split("#")[-1].split("/")[-1].lower()] = x

    if vocab_id in vocab_ids.keys():
        return vocab_ids[vocab_id]
    else:
        return None


def make_vocab_id_list():
    return [x.split("#")[-1].split("/")[-1].lower() for x in g.VOCABS.keys()]


@app.route("/vocab/<string:vocab_id>/")
def vocabulary(vocab_id):
    vocab_uri = translate_vocab_id_to_vocab_uri(vocab_id)

    if vocab_uri is None:
        return return_vocrez_error(
            "vocab_id not valid",
            400,
            markdown.markdown(
                "The 'vocab_id' you supplied could not be translated to a valid vocab's URI. Valid vocab_ids are:\n\n"                
                "{}".format("".join(["* [{id}]({uri})   \n".format(**{"uri": url_for("vocabulary", vocab_id=x), "id": x}) for x in make_vocab_id_list()]))
                # "{}".format(",".join(make_vocab_id_list()))
            ),
        )

    return return_vocab(vocab_uri)


@app.route("/vocab/<vocab_id>/concept/")
def concepts(vocab_id):
    return "/concept/"

    # check the vocab id is valid
    vocab_ids = {}
    for x in g.VOCABS.keys():
        vocab_ids[x.split("#")[-1].split("/")[-1]] = x

    if vocab_id not in vocab_ids.keys():
        msg = "The vocabulary ID that was supplied was not known. " \
              "It must be one of these: {}".format(", ".join(vocab_ids.keys()))
        return Response(
            msg,
            status=400,
            mimetype="text/plain"
        )

    try:
        vocab_source = getattr(source, g.VOCABS[vocab_id].source)(vocab_id, request)
        concepts = vocab_source.list_concepts()
        # concepts.sort(key=lambda x: x["prefLabel"]) -- sort not needed when receiving pre-sorted tuples
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
        members = concepts[start:end]
    except Exception as e:
        return Response(
            str(e),
            status=500,
            mimetype="text/plain"
        )

    return ContainerRenderer(
        request,
        url_for("concepts", vocab_id=vocab_id),
        "All Concepts",
        'All Concepts within Vocab {}'.format(vocab_id),
        None,
        None,
        members,
        total
    ).render()


@app.route("/collection/")
def collections():
    return render_template(
        "members.html",
        title="Collections",
        register_class="Collections",
    )


def return_vocab(uri):
    if uri in g.VOCABS.keys():
        # get vocab details using appropriate source handler
        vocab = getattr(source, g.VOCABS[uri].source) \
            (uri, request, language=request.values.get("lang")).get_vocabulary()
        return VocabularyRenderer(request, vocab).render()
    else:
        return None


# TODO: make this use the main cache directly, not via Vocab's source
def return_collection_or_concept_from_main_cache(uri):
    q = """
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

        SELECT DISTINCT *
        WHERE {{ 
            GRAPH ?g {{
                <{uri}> a ?c .
                OPTIONAL {{
                    <{uri}> skos:inScheme ?cs .
                }}

                BIND (COALESCE(?cs, ?g) AS ?x)
            }}                
        }}
        """.format(uri=uri)
    for r in sparql_query(q):
        if r["c"]["value"] in source.Source.VOC_TYPES:
            # if we find it and it's of a known class, return it
            # since, for a Concept or a Collection, we know the relevant vocab as vocab ==  CS ==  graph
            # in VocPrez's models of a vocabs
            vocab_uri = r["x"]["value"]
            if r["c"]["value"] == "http://www.w3.org/2004/02/skos/core#Collection":
                try:
                    c = source.Source(vocab_uri, request).get_collection(uri)
                    return CollectionRenderer(request, c).render()
                except:
                    pass
            elif r["c"]["value"] == "http://www.w3.org/2004/02/skos/core#Concept":
                try:
                    c = source.Source(vocab_uri, request).get_concept(uri)
                    return ConceptRenderer(request, c).render()
                except:
                    pass
    return None


def return_collection_or_concept_from_vocab_source(vocab_uri, uri):
    try:
        c = getattr(source, g.VOCABS[vocab_uri].source) \
            (vocab_uri, request, language=request.values.get("lang")).get_collection(uri)

        return CollectionRenderer(request, c).render()
    except:
        pass

    try:
        c = getattr(source, g.VOCABS[vocab_uri].source) \
            (vocab_uri, request, language=request.values.get("lang")).get_concept(uri)

        return ConceptRenderer(request, c).render()
    except:
        pass

    return None


# TODO: review the logic in this function regarding use of uri, vocab_uri or uri & vocab_uri
@app.route("/object")
def object():
    """
    This is the general RESTful endpoint and corresponding Python function to handle requests for individual objects,
    be they a Vocabulary, Concept Scheme, Collection or Concept. Only those 4 classes of object are supported for the
    moment.

    An HTTP URI query string argument parameter 'vocab_uri' may be supplied, indicating the vocab this object is within
    An HTTP URI query string argument parameter 'uri' must be supplied, indicating the URI of the object being requested

    :return: A Flask Response object
    :rtype: :class:`flask.Response`
    """

    uri = request.values.get("uri")
    vocab_uri = request.values.get("vocab_uri")

    uri_is_empty = True if uri is None or uri == "" else False
    vocab_uri_is_empty = True if vocab_uri is None or vocab_uri == "" else False

    # must have a URI or Vocab URI supplied, for any scenario
    if uri_is_empty and vocab_uri_is_empty:
        return return_vocrez_error(
            "Input Error",
            400,
            "A Query String Argument of 'uri' and/or 'vocab_uri' must be supplied for this endpoint"
        )
    elif uri_is_empty and not vocab_uri_is_empty:
        # we only have a vocab_uri, so it must be a vocab
        v = return_vocab(vocab_uri)
        if v is not None:
            return v
        # if we haven't returned already, the vocab_uri was unknown but that's all we have so error
        return return_vocrez_error(
            "vocab_uri error",
            400,
            markdown.markdown(
                "You have supplied an unknown 'vocab_uri'. If one is supplied, "
                "it must be one of:\n\n"
                "{}".format("".join(["* " + str(x) + "   \n" for x in g.VOCABS.keys()]))
            ),
        )
    elif not uri_is_empty and vocab_uri_is_empty:
        # we have no vocab_uri so we must be able to return a result from the main cache or error
        # if it's a vocab, return that
        v = return_vocab(uri)
        if v is not None:
            return v
        # if we get here, it's not a vocab so try to return a Collection or Concept from the main cache
        c = return_collection_or_concept_from_main_cache(uri)
        if c is not None:
            return c
        # if we get here, it's neither a vocab nor a Concept of Collection so return error
        return return_vocrez_error(
            "Input Error",
            400,
            "The 'uri' you supplied is not known to this instance of VocPrez. You may consider supplying a 'vocab_uri' "
            "parameter with that same 'uri' to see if VocPrez can use that vocab URI to look up information about "
            "the 'uri' object' from a remote source."
        )
    else:  # both uri & vocab_uri are set
        # look up URI at vocab_uri source. If not found, return error

        # we have a vocab_uri, so it must be a real one
        if vocab_uri not in g.VOCABS.keys():
            return return_vocrez_error(
                "Input Error",
                400,
                markdown.markdown(
                    "You have supplied an unknown 'vocab_uri'. If one is supplied, "
                    "it must be one of:\n\n"
                    "{}".format("".join(["* " + str(x) + "   \n" for x in g.VOCABS.keys()]))
                ),
            )

        # the vocab_uri is valid so query that vocab's source for the object
        # the uri is either a Concept or Collection.
        c = return_collection_or_concept_from_vocab_source(vocab_uri, uri)
        if c is not None:
            return c

        # if we get here, neither a Collection nor a Concept could be found at that vocab's source so error
        return return_vocrez_error(
            "Input Error",
            400,
            "You supplied a valid 'vocab_uri' but when VocPrez queried the relevant vocab, no information about the "
            "object you identified with 'uri' was found.",
        )


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
        title="About",
        navs={},
        content=content
    )


# the SPARQL UI
@app.route("/sparql", methods=["GET", "POST"])
def sparql():
    return render_template(
        "sparql.html",
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


# TODO: use for all errors
# TODO: allow conneg - at least text v. HTML
def return_vocrez_error(title, status, message):
    return render_template(
        "error.html",
        title=title,
        status=status,
        msg=message
    ), status


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
        title="Error - Object Class URI",
        heading="Concept Class Type Error",
        msg=msg,
    )


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
