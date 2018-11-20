from flask import Blueprint, Response, request, render_template
import _config as config
import markdown
from flask import Markup

routes = Blueprint('routes', __name__)


@routes.route('/')
def index():
    return render_template('index.html', title='SKOS Styler')


@routes.route('/home')
def vochome():
    return render_template('vochome.html', title='SKOS Styler')


@routes.route('/conceptscheme/')
def conceptschemes():
    return render_template('register.html', title='Concept Schemes', register_class='Concept Schemes')


@routes.route('/collection/')
def collections():
    return render_template('register.html', title='Collections', register_class='Collections')


@routes.route('/concept/')
def concepts():
    return render_template('register.html', title='Concepts', register_class='Concepts')


@routes.route('/about')
def about():
    import os

    # using basic Markdown method from http://flask.pocoo.org/snippets/19/
    with open(os.path.join(config.APP_DIR, 'README.md')) as f:
        content = f.read()

    content = Markup(markdown.markdown(content))
    return render_template('about.html', title='About', content=content)
