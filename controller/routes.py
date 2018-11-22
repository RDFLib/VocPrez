from flask import Blueprint, Response, request, render_template, url_for
from pyldapi import *
import model
from model.vocabulary import VocabularyRenderer
from model.skos_register import SkosRegisterRenderer
import _config as config
import markdown
from flask import Markup

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
    vocabs = model.rva().list_vocabularies()

    return SkosRegisterRenderer(
        request,
        [],
        vocabs,
        'Vocabularies',
        len(vocabs)
    ).render()


@routes.route('/vocabulary/<voc_id>')
def vocabulary(voc_id):
    # this is always true for this dummy code
    if voc_id.startswith('rva-'):
        vocab_metadata = model.rva().get_vocabulary(voc_id)
    else:
        # here is where other vocab IDs would trigger other model calls
        pass

    navs = [
        '<a href="{{ url_for(\'routes.collections\') }}">Collections</a> |',
        '<a href="{{ url_for(\'routes.concepts\') }}">Concepts</a> |'
    ]

    return VocabularyRenderer(
        request,
        navs,
        request.base_url
    ).render()


@routes.route('/collection/')
def collections():
    return render_template(
        'register.html',
        title='Collections',
        register_class='Collections',
        navs={}
    )


@routes.route('/concept/')
def concepts():
    return render_template(
        'register.html',
        title='Concepts', register_class='Concepts',
        navs={}
    )


@routes.route('/about')
def about():
    import os

    # using basic Markdown method from http://flask.pocoo.org/snippets/19/
    with open(os.path.join(config.APP_DIR, 'README.md')) as f:
        content = f.read()

    content = Markup(markdown.markdown(content))
    return render_template(
        'about.html',
        title='About',
        navs={},
        content=content
    )
