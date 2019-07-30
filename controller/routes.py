from flask import Blueprint, Response, request, render_template, Markup, g, redirect, url_for, send_file
from model.vocabulary import VocabularyRenderer
from model.concept import ConceptRenderer
from model.collection import CollectionRenderer
from model.skos_register import SkosRegisterRenderer
import _config as config
import markdown
from data.source._source import Source
from data.source.VOCBENCH import VbException
import json
from pyldapi import Renderer
import controller.sparql_endpoint_functions
import datetime
import logging

routes = Blueprint('routes', __name__)


def render_invalid_vocab_id_response():
    msg = """The vocabulary ID that was supplied was not known. It must be one of these: \n\n* """ + '\n* '.join(g.VOCABS.keys())
    msg = Markup(markdown.markdown(msg))
    return render_template('error.html', title='Error - invalid vocab id', heading='Invalid Vocab ID', msg=msg)
    # return Response(
    #     'The vocabulary ID you\'ve supplied is not known. Must be one of:\n ' +
    #     '\n'.join(g.VOCABS.keys()),
    #     status=400,
    #     mimetype='text/plain'
    # )


def render_vb_exception_response(e):
    e = json.loads(str(e))
    msg = e['stresponse']['msg']
    if 'not an open project' in msg:
        invalid_vocab_id = msg.split('not an open project:')[-1]
        msg = 'The VocBench instance returned with an error: **{}** is not an open project.'.format(invalid_vocab_id)
        msg = Markup(markdown.markdown(msg))
    return render_template('error.html', title='Error', heading='VocBench Error', msg=msg)


def render_invalid_object_class_response(vocab_id, uri, c_type):
    msg = """No valid *Object Class URI* found for vocab_id **{}** and uri **{}** 
    
Instead, found **{}**.""".format(vocab_id, uri, c_type)
    msg = Markup(markdown.markdown(msg))
    return render_template('error.html', title='Error - Object Class URI', heading='Concept Class Type Error', msg=msg)


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


@routes.context_processor
def inject_date():
    return {'date': datetime.date.today()}


@routes.route('/')
def index():
    return render_template(
        'index.html',
        title=config.TITLE,
        navs={},
        config=config,
        voc_key=get_a_vocab_source_key()
    )


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


@routes.route('/vocabulary/')
def vocabularies():
    page = int(request.values.get('page')) if request.values.get('page') is not None else 1
    per_page = int(request.values.get('per_page')) if request.values.get('per_page') is not None else 20

    # TODO: replace this logic with the following
    #   1. read all static vocabs from g.VOCABS
    # get this instance's list of vocabs
    vocabs = []  # local copy (to this request) for sorting
    for k, voc in g.VOCABS.items():
        vocabs.append(voc)
    vocabs.sort(key=lambda v: v.title)
    total = len(g.VOCABS.items())

    # Search
    query = request.values.get('search')
    results = []
    if query:
        for m in match(vocabs, query):
            results.append(m)
        vocabs[:] = results
        vocabs.sort(key=lambda v: v.title)
        total = len(vocabs)

    # generate vocabs list for requested page and per_page
    start = (page-1)*per_page
    end = start + per_page
    vocabs = vocabs[start:end]

    # render the list of vocabs
    return SkosRegisterRenderer(
        request,
        [],
        vocabs,
        'Vocabularies',
        total,
        search_query=query,
        search_enabled=True,
        vocabulary_url=['http://www.w3.org/2004/02/skos/core#ConceptScheme']
    ).render()


@routes.route('/vocabulary/<vocab_id>')
def vocabulary(vocab_id):
    language = request.values.get('lang') or config.DEFAULT_LANGUAGE

    if vocab_id not in g.VOCABS.keys():
        return render_invalid_vocab_id_response()

    # get vocab details using appropriate source handler
    try:
        vocab = Source(vocab_id, request, language).get_vocabulary()
    except VbException as e:
        return render_vb_exception_response(e)

    return VocabularyRenderer(
        request,
        vocab
    ).render()


@routes.route('/vocabulary/<vocab_id>/concept/')
def vocabulary_list(vocab_id):
    language = request.values.get('lang') or config.DEFAULT_LANGUAGE

    if vocab_id not in g.VOCABS.keys():
        return render_invalid_vocab_id_response()
    
    vocab_source = Source(vocab_id, request, language)
    concepts = vocab_source.list_concepts()
    concepts.sort(key=lambda x: x['title'])
    total = len(concepts)

    # Search
    query = request.values.get('search')
    results = []
    if query:
        for m in match(concepts, query):
            results.append(m)
        concepts[:] = results
        concepts.sort(key=lambda x: x['title'])
        total = len(concepts)

    page = int(request.values.get('page')) if request.values.get('page') is not None else 1
    per_page = int(request.values.get('per_page')) if request.values.get('per_page') is not None else 20
    start = (page - 1) * per_page
    end = start + per_page
    concepts = concepts[start:end]

    test = SkosRegisterRenderer(
        request,
        [],
        concepts,
        g.VOCABS[vocab_id].title + ' concepts',
        total,
        search_query=query,
        search_enabled=True,
        vocabulary_url=[request.url_root + 'vocabulary/' + vocab_id],
        vocab_id=vocab_id
    )
    return test.render()


@routes.route('/collection/')
def collections():
    return render_template(
        'register.html',
        title='Collections',
        register_class='Collections',
        navs={}
    )


@routes.route('/object')
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
    print(request.values)
    language = request.values.get('lang') or config.DEFAULT_LANGUAGE
    vocab_id = request.values.get('vocab_id')
    uri = request.values.get('uri')
    _view = request.values.get('_view')
    _format = request.values.get('_format')

    # check this vocab ID is known
    if vocab_id not in g.VOCABS.keys():
        return Response(
            'The vocabulary ID you\'ve supplied is not known. Must be one of:\n ' +
            '\n'.join(g.VOCABS.keys()),
            status=400,
            mimetype='text/plain'
        )

    if uri is None:
        return Response(
            'A Query String Argument \'uri\' must be supplied for this endpoint, '
            'indicating an object within a vocabulary',
            status=400,
            mimetype='text/plain'
        )
        
    vocab_source = Source(vocab_id, request, language)

    try:
        # TODO reuse object within if, rather than re-loading graph
        c = vocab_source.get_object_class()
        #print(c)

        if c == 'http://www.w3.org/2004/02/skos/core#Concept':
            concept = vocab_source.get_concept()
            return ConceptRenderer(
                request,
                concept
            ).render()
            
        elif c == 'http://www.w3.org/2004/02/skos/core#ConceptScheme':
            vocabulary = vocab_source.get_vocabulary()

            return VocabularyRenderer(
                request,
                vocabulary
            ).render()

        elif c == 'http://www.w3.org/2004/02/skos/core#Collection':
            collection = vocab_source.get_collection(uri)

            return CollectionRenderer(
                request,
                collection
            ).render()
        else:
            return render_invalid_object_class_response(vocab_id, uri, c)
    except VbException as e:
        return render_vb_exception_response(e)



@routes.route('/geosciml')
def geosciml():
    return render_template(
        'geosciml_home.html'
    )


@routes.route('/about')
def about():
    import os

    # using basic Markdown method from http://flask.pocoo.org/snippets/19/
    with open(os.path.join(config.APP_DIR, 'README.md')) as f:
        content = f.read()

    # make images come from wed dir
    content = content.replace('view/static/system.svg',
                              request.url_root + 'static/system.svg')
    content = Markup(markdown.markdown(content))

    return render_template(
        'about.html',
        title='About',
        navs={},
        content=content
    )


# the SPARQL UI
@routes.route('/sparql', methods=['GET', 'POST'])
def sparql():
    return render_template('sparql.html')


# the SPARQL endpoint under-the-hood
@routes.route('/endpoint', methods=['GET', 'POST'])
def endpoint():
    '''
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

    '''
    logging.debug('request: {}'.format(request.__dict__))
    
    #TODO: Find a slightly less hacky way of getting the format_mimetime value
    format_mimetype = request.__dict__['environ']['HTTP_ACCEPT']
    
    # Query submitted
    if request.method == 'POST':
        '''Pass on the SPARQL query to the underlying endpoint defined in config
        '''
        if 'application/x-www-form-urlencoded' in request.content_type:
            '''
            https://www.w3.org/TR/2013/REC-sparql11-protocol-20130321/#query-via-post-urlencoded

            2.1.2 query via POST with URL-encoded parameters

            Protocol clients may send protocol requests via the HTTP POST method by URL encoding the parameters. When
            using this method, clients must URL percent encode all parameters and include them as parameters within the
            request body via the application/x-www-form-urlencoded media type with the name given above. Parameters must
            be separated with the ampersand (&) character. Clients may include the parameters in any order. The content
            type header of the HTTP request must be set to application/x-www-form-urlencoded.
            '''
            if request.values.get('query') is None or len(request.values.get('query')) < 5:
                return Response(
                    'Your POST request to the SPARQL endpoint must contain a \'query\' parameter if form posting '
                    'is used.',
                    status=400,
                    mimetype='text/plain'
                )
            else:
                query = request.values.get('query')
        elif 'application/sparql-query' in request.content_type:
            '''
            https://www.w3.org/TR/2013/REC-sparql11-protocol-20130321/#query-via-post-direct

            2.1.3 query via POST directly

            Protocol clients may send protocol requests via the HTTP POST method by including the query directly and
            unencoded as the HTTP request message body. When using this approach, clients must include the SPARQL query
            string, unencoded, and nothing else as the message body of the request. Clients must set the content type
            header of the HTTP request to application/sparql-query. Clients may include the optional default-graph-uri
            and named-graph-uri parameters as HTTP query string parameters in the request URI. Note that UTF-8 is the
            only valid charset here.
            '''
            query = request.data.decode('utf-8')  # get the raw request
            if query is None:
                return Response(
                    'Your POST request to this SPARQL endpoint must contain the query in plain text in the '
                    'POST body if the Content-Type \'application/sparql-query\' is used.',
                    status=400
                )
        else:
            return Response(
                'Your POST request to this SPARQL endpoint must either the \'application/x-www-form-urlencoded\' or'
                '\'application/sparql-query\' ContentType.',
                status=400
            )

        try:
            if 'CONSTRUCT' in query:
                format_mimetype = 'text/turtle'
                return Response(
                    controller.sparql_endpoint_functions.sparql_query(query, format_mimetype=format_mimetype),
                    status=200,
                    mimetype=format_mimetype
                )
            else:
                return Response(
                    controller.sparql_endpoint_functions.sparql_query(query, format_mimetype),
                    status=200
                )
        except ValueError as e:
            return Response(
                'Input error for query {}.\n\nError message: {}'.format(query, str(e)),
                status=400,
                mimetype='text/plain'
            )
        except ConnectionError as e:
            return Response(str(e), status=500)
    else:  # GET
        if request.args.get('query') is not None:
            # SPARQL GET request
            '''
            https://www.w3.org/TR/2013/REC-sparql11-protocol-20130321/#query-via-get

            2.1.1 query via GET

            Protocol clients may send protocol requests via the HTTP GET method. When using the GET method, clients must
            URL percent encode all parameters and include them as query parameter strings with the names given above.

            HTTP query string parameters must be separated with the ampersand (&) character. Clients may include the
            query string parameters in any order.

            The HTTP request MUST NOT include a message body.
            '''
            query = request.args.get('query')
            if 'CONSTRUCT' in query:
                acceptable_mimes = [x for x in Renderer.RDF_MIMETYPES]
                best = request.accept_mimetypes.best_match(acceptable_mimes)
                query_result = controller.sparql_endpoint_functions.sparql_query(query, format_mimetype=best)
                file_ext = {
                    'text/turtle': 'ttl',
                    'application/rdf+xml': 'rdf',
                    'application/ld+json': 'json',
                    'text/n3': 'n3',
                    'application/n-triples': 'nt'
                }
                return Response(
                    query_result,
                    status=200,
                    mimetype=best,
                    headers={
                        'Content-Disposition': 'attachment; filename=query_result.{}'.format(file_ext[best])
                    }
                )
            else:
                query_result = controller.sparql_endpoint_functions.sparql_query(query)
                return Response(query_result, status=200, mimetype='application/sparql-results+json')
        else:
            # SPARQL Service Description
            '''
            https://www.w3.org/TR/sparql11-service-description/#accessing

            SPARQL services made available via the SPARQL Protocol should return a service description document at the
            service endpoint when dereferenced using the HTTP GET operation without any query parameter strings
            provided. This service description must be made available in an RDF serialization, may be embedded in
            (X)HTML by way of RDFa, and should use content negotiation if available in other RDF representations.
            '''

            acceptable_mimes = [x for x in Renderer.RDF_MIMETYPES] + ['text/html']
            best = request.accept_mimetypes.best_match(acceptable_mimes)
            if best == 'text/html':
                # show the SPARQL query form
                return redirect(url_for('routes.sparql'))
            elif best is not None:
                for item in Renderer.RDF_MIMETYPES:
                    if item == best:
                        rdf_format = best
                        return Response(
                            controller.sparql_endpoint_functions.get_sparql_service_description(
                                rdf_format=rdf_format
                            ),
                            status=200,
                            mimetype=best)

                return Response(
                    'Accept header must be one of ' + ', '.join(acceptable_mimes) + '.',
                    status=400
                )
            else:
                return Response(
                    'Accept header must be one of ' + ', '.join(acceptable_mimes) + '.',
                    status=400
                )
