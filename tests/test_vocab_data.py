import os
from vocprez.app import app
from flask import g
import pytest
from vocprez.source.file import File
from vocprez import _config as config
from vocprez.utils import cache_write

#TODO: delete cached pickle files/vocab_files before running tests?
#TODO: loop through a set of supplied vocabs. At present only 'Airborn_Magnetic' is being used

TEST_SOURCE = {
        "source" : "File",
        "directory" : os.path.join(config.APP_DIR,'data','vocab_files')
    }

# create a pytest fixture to allow 'mounting' of vocab data for test purposes. Utilises a local file source.
@pytest.fixture
def client():
    app.testing = True
    with app.test_client() as client:
        with app.app_context():
            g.VOCABS = {}
            File.collect(TEST_SOURCE)
            cache_write(g.VOCABS)
        yield client


def test_index_html(client):
    content = client.get('/')
    assert "<h1>System Home</h1>" in content.data.decode("utf-8")


def test_about_html(client):
    content = client.get("/about")
    assert "<p>A read-only web delivery system for Simple Knowledge Organization System (SKOS)-formulated RDF vocabularies.</p>" in content.data.decode("utf-8")


def test_vocabs_list_html(client):
    content = client.get('/vocab/')
    assert '<h3>Members</h3>' in content.data.decode("utf-8")


def test_vocabs_data(client):
    content = client.get('/vocab/')
    assert '<a href="/object?uri=test_vocab">Airborn Magnetic</a>' in content.data.decode("utf-8")


def test_a_vocab_html(client):
    content = client.get('/object?uri=test_vocab')
    assert '<h1>Vocabulary</h1>' in content.data.decode("utf-8")


def test_a_vocab_data(client):
    content = client.get('/object?uri=test_vocab')
    assert '<h2>Airborn Magnetic</h2>' in content.data.decode("utf-8")


def test_a_vocab_profiles(client):
    content = client.get('/object?uri=test_vocab')
    assert '<h2>Airborn Magnetic</h2>' in content.data.decode("utf-8")


def test_alt_profiles_html(client):
    content = client.get('/vocab/?_profile=alt')
    assert '<h1>Alternate Profiles</h1>' in content.data.decode("utf-8")

# function to assist in writing tests - allows viewing of returned HTML
def manual_checker(endpoint):
    client = app.test_client()
    with app.app_context():
        g.VOCABS = {}
        File.collect(TEST_SOURCE)
        content = client.get(endpoint)
        dc = content.data.decode("utf-8")
    return dc
# a = manual_checker('/object?uri=Airborn_Magnetic')