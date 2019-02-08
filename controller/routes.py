from flask import Blueprint, Response, request, render_template
from model.vocabulary import VocabularyRenderer
from model.concept import ConceptRenderer
from model.collection import CollectionRenderer
from model.skos_register import SkosRegisterRenderer
import _config as config
import markdown
from flask import Markup
from data.source import Source
from data.source_VOCBENCH import VbException

routes = Blueprint('routes', __name__)


def render_invalid_vocab_id_response():
    return Response(
        'The vocabulary ID you\'ve supplied is not known. Must be one of:\n ' +
        '\n'.join(config.VOCABS.keys()),
        status=400,
        mimetype='text/plain'
    )


def get_a_vocab_source_key():
    """
    Get the first key from the config.VOCABS dictionary.

    :return: Key name
    :rtype: str
    """
    return next(iter(config.VOCABS))


@routes.route('/')
def index():
    return render_template(
        'index.html',
        title=config.TITLE,
        navs={},
        config=config,
        voc_key=get_a_vocab_source_key()
    )


def match(vocabs, query):
    """
    Generate a generator of vocabulary items that match the search query

    :param vocabs: The vocabulary list of items.
    :param query: The search query string.
    :return: A generator of words that match the search query.
    :rtype: generator
    """
    for word in vocabs:
        if query.lower() in word[1].lower():
            yield word


@routes.route('/vocabulary/')
def vocabularies():
    page = int(request.values.get('page')) if request.values.get('page') is not None else 1
    per_page = int(request.values.get('per_page')) if request.values.get('per_page') is not None else 20

    # TODO: replace this logic with the following
    #   1. read all static vocabs from config.VOCABS
    # get this instance's list of vocabs
    vocabs = []
    for k, v in config.VOCABS.items():
        vocabs.append((k, v['title']))
    vocabs.sort(key=lambda tup: tup[1])
    total = len(config.VOCABS.items())

    # Search
    query = request.values.get('search')
    results = []
    if query:
        for m in match(vocabs, query):
            results.append(m)
        vocabs[:] = results
        vocabs.sort(key=lambda tup: tup[1])
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
        search_enabled=True
    ).render()


@routes.route('/vocabulary/<vocab_id>')
def vocabulary(vocab_id):
    if vocab_id not in config.VOCABS.keys():
        return render_invalid_vocab_id_response()

    # get vocab details using appropriate source handler
    try:
        v = Source(vocab_id, request).get_vocabulary()
    except VbException as e:
        return Response(response=str(e), status=400, mimetype='text/xml')

    return VocabularyRenderer(
        request,
        v
    ).render()


@routes.route('/vocabulary/<vocab_id>/concept/')
def vocabulary_list(vocab_id):
    if vocab_id not in config.VOCABS.keys():
        return render_invalid_vocab_id_response()

    v = Source(vocab_id, request)
    concepts = v.list_concepts()
    concepts.sort(key= lambda x: x[1])
    total = len(concepts)

    # Search
    query = request.values.get('search')
    results = []
    if query:
        for m in match(concepts, query):
            results.append(m)
        concepts[:] = results
        concepts.sort(key=lambda tup: tup[1])
        total = len(concepts)

    page = int(request.values.get('page')) if request.values.get('page') is not None else 1
    per_page = int(request.values.get('per_page')) if request.values.get('per_page') is not None else 20
    start = (page - 1) * per_page
    end = start + per_page
    concepts = concepts[start:end]

    return SkosRegisterRenderer(
        request,
        [],
        concepts,
        config.VOCABS[vocab_id]['title'] + ' concepts',
        total,
        search_query=query,
        search_enabled=True,
        vocabulary_url=request.url_root + 'vocabulary/' + vocab_id,
        vocab_id=vocab_id
    ).render()


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
    vocab_id = request.values.get('vocab_id')
    uri = request.values.get('uri')

    # check this vocab ID is known
    if vocab_id not in config.VOCABS.keys():
        return Response(
            'The vocabulary ID you\'ve supplied is not known. Must be one of:\n ' +
            '\n'.join(config.VOCABS.keys()),
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

    try:
        # TODO reuse object within if, rather than re-loading graph
        c = Source(vocab_id, request).get_object_class(uri)

        if c == 'http://www.w3.org/2004/02/skos/core#Concept':
            concept = Source(vocab_id, request).get_concept(uri)
            return ConceptRenderer(
                request,
                concept
            ).render()
        elif c == 'http://www.w3.org/2004/02/skos/core#Collection':
            collection = Source(vocab_id, request).get_collection(uri)

            return CollectionRenderer(
                request,
                collection
            ).render()
        else:
            return 'System error at /object endpoint: Object Class URI not found. '
    except VbException as e:
        return Response(response=str(e), status=400, mimetype='text/xml')


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
