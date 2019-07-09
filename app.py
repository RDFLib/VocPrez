import logging
import _config as config
from flask import Flask, g
from controller import routes
import helper
import data.source as source
import os
import pickle
import time

app = Flask(__name__, template_folder=config.TEMPLATES_DIR, static_folder=config.STATIC_DIR)

app.register_blueprint(routes.routes)


@app.before_request
def before_request():
    """
    Runs before every request and populates vocab index either from disk (VOCABS.p) or from a complete reload by
    calling collect() for each of the vocab sources defined in config/__init__.py -> VOCAB_SOURCES
    :return: nothing
    """
    # check to see if g.VOCABS exists, if so, do nothing
    if hasattr(g, 'VOCABS'):
        return

    # we have no g.VOCABS so try and load it from a pickled VOCABS.pickle file
    vocabs_file_path = os.path.join(config.APP_DIR, 'VOCABS.p')
    if os.path.isfile(vocabs_file_path):
        # if the VOCABS.pickle file is more than one day old, delete it and run collect()
        vocab_file_creation_time = os.stat(vocabs_file_path).st_mtime
        if vocab_file_creation_time < time.time() - 86400:  # now less 1 day (in seconds)
            os.remove(vocabs_file_path)
        # the file is less than a day old so use it
        else:
            with open(vocabs_file_path, 'rb') as f:
                g.VOCABS = pickle.load(f)
                f.close()
            if g.VOCABS: # Ignore empty file
                return

    # we haven't been able to load from VOCABS.pickle so run collect() on each vocab source to recreate it

    # check each vocab source and,
    # using the appropriate class (from details['source']),
    # load all the vocabs from it into this session's (g) VOCABS variable
    g.VOCABS = {}
    for name, details in config.VOCAB_SOURCES.items():
        getattr(source, details['source']).collect(details)

    # also load all vocabs into VOCABS.p on disk for future use
    if g.VOCABS: # Don't write empty file
        with open(vocabs_file_path, 'wb') as f:
            pickle.dump(g.VOCABS, f)
            f.close()


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
    logging.basicConfig(filename=config.LOGFILE,
                        level=logging.DEBUG,
                        datefmt='%Y-%m-%d %H:%M:%S',
                        format='%(asctime)s %(levelname)s %(filename)s:%(lineno)s %(message)s')

    app.run(debug=config.DEBUG, threaded=True)
