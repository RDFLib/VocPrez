import logging
import _config
from flask import Flask
from controller import routes
import helper
from data.source_FILE import FILE
from data.source_RVA import RVA
from data.source_VOCBENCH import VOCBENCH

app = Flask(__name__, template_folder=_config.TEMPLATES_DIR, static_folder=_config.STATIC_DIR)

app.register_blueprint(routes.routes)


@app.before_first_request
def start_up_tasks():
    VOCBENCH.init()
    RVA.init()
    FILE.init()
    # extend this instances' list of vocabs by using the known sources
    VOCABS = {**_config.VOCABS, **FILE.list_vocabularies()}  # picks up all vocab RDF (turtle) files in data/
    # VOCABS = {**VOCABS, **VOCBENCH.list_vocabularies()}  # picks up all vocabs at the relevant VocBench instance
    print('Finished startup tasks.')


@app.context_processor
def context_processor():
    """
    A set of global variables available to 'globally' for jinja templates.
    :return: A dictionary of variables
    :rtype: dict
    """
    return dict(h=helper)


# run the Flask app
if __name__ == '__main__':
    logging.basicConfig(filename=_config.LOGFILE,
                        level=logging.DEBUG,
                        datefmt='%Y-%m-%d %H:%M:%S',
                        format='%(asctime)s %(levelname)s %(filename)s:%(lineno)s %(message)s')

    app.run(debug=_config.DEBUG, threaded=True)
