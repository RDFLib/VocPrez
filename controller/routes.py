from flask import Blueprint, Response, request, render_template
from model.vocabulary import VocabularyRenderer
from model.concept import ConceptRenderer
from model.collection import CollectionRenderer
from model.skos_register import SkosRegisterRenderer
import _config as config
import markdown
from flask import Markup
from data.source import Source

routes = Blueprint('routes', __name__)


@routes.route('/')
def index():
    return render_template(
        'index.html',
        title='SKOS Styler',
        navs={}
    )


@routes.route('/vocabulary/')
def vocabularies():
    # TODO: replace this logic with the following
    #   1. read all static vocabs from config.VOCABS
    # get this instance's list of vocabs
    vocabs = []
    for k, v in config.VOCABS.items():
        vocabs.append(('/vocabulary/' + k, v['title']))
    vocabs.sort(key=lambda tup: tup[1])

    # render the list of vocabs
    return SkosRegisterRenderer(
        request,
        [],
        vocabs,
        'Vocabularies',
        len(vocabs)
    ).render()


@routes.route('/vocabulary/<vocab_id>')
def vocabulary(vocab_id):
    # check this vocab ID is known
    if vocab_id not in config.VOCABS.keys():
        return Response(
            'The vocabulary ID you\'ve supplied is not known. Must be one of:\n ' +
            '\n'.join(config.VOCABS.keys()),
            status=400,
            mimetype='text/plain'
        )

    # get vocab details using appropriate source handler

    v = Source(vocab_id).get_vocabulary()

    return VocabularyRenderer(
        request,
        v
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

    # TODO reuse object within if, rather than re-loading graph
    c = Source(vocab_id).get_object_class(uri)

    if c == 'http://www.w3.org/2004/02/skos/core#Concept':
        concept = Source(vocab_id).get_concept(uri)
        print('concept')
        print(concept)
        return ConceptRenderer(
            request,
            concept
        ).render()
    elif c == 'http://www.w3.org/2004/02/skos/core#Collection':
        collection = Source(vocab_id).get_collection(uri)

        return CollectionRenderer(
            request,
            collection
        ).render()


@routes.route('/about')
def about():
    import os

    # using basic Markdown method from http://flask.pocoo.org/snippets/19/
    with open(os.path.join(config.APP_DIR, 'README.md')) as f:
        content = f.read()

    # make images come from wed dir
    content = content.replace('view/static/system.svg',
                              '/static/system.svg')
    content = Markup(markdown.markdown(content))

    return render_template(
        'about.html',
        title='About',
        navs={},
        content=content
    )
