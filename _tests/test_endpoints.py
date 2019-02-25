import requests
import json
import re

BASE_URLS = ['http://localhost:5000', 'http://vocabs.gsq.cat']

N_TRIPLES_PATTERN = r'(_:(.+)|<.+>) (_:(.+)|<.+>) (_:(.+)|(".+"\^\^)?<.+>) .'


#
# -- Test static pages -------------------------------------------------------------------------------------------------
#
def test_index_html():
    for BASE_URL in BASE_URLS:
        content = requests.get(BASE_URL).content.decode('utf-8')
        assert '<h1>System Home</h1>' in content, BASE_URL


def test_about_html():
    for BASE_URL in BASE_URLS:
        content = requests.get(BASE_URL + '/about').content.decode('utf-8')
        assert '<p>A read-only web delivery system for Simple Knowledge Organization System (SKOS)-formulated RDF ' \
               'vocabularies.</p>' in content, BASE_URL


#
# -- Test vocabulary register ------------------------------------------------------------------------------------------
#

def test_vocabulary_register_ckan_view_json():
    for BASE_URL in BASE_URLS:
        content = requests.get(BASE_URL + '/vocabulary/?vocab_id=&_view=ckan&_format=application/json&uri=' + BASE_URL
                               + '/vocabulary/').content.decode('utf-8')
        content = json.loads(content)
        assert 'head' and 'results' in content, BASE_URL
        assert 's' and 'pl' in content['head']['vars'], BASE_URL


def test_vocabulary_register_reg_view_html():
    for BASE_URL in BASE_URLS:
        content = requests.get(BASE_URL + '/vocabulary/').content.decode('utf-8')
        assert 'Search <em>Vocabularies:</em><br>' in content, BASE_URL


def test_vocabulary_register_reg_view_turtle():
    for BASE_URL in BASE_URLS:
        content = requests.get(BASE_URL + '/vocabulary/?vocab_id=&_view=reg&_format=text/turtle&uri=' + BASE_URL +
                               '/vocabulary/').content.decode('utf-8')
        assert """@prefix ereg: <https://promsns.org/def/eregistry#> .
@prefix ldp: <http://www.w3.org/ns/ldp#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix reg: <http://purl.org/linked-data/registry#> .
@prefix xhv: <https://www.w3.org/1999/xhtml/vocab#> .
@prefix xml: <http://www.w3.org/XML/1998/namespace> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .""" in content, BASE_URL


def test_vocabulary_register_reg_view_xml():
    for BASE_URL in BASE_URLS:
        content = requests.get(BASE_URL + '/vocabulary/?vocab_id=&_view=reg&_format=application/rdf+xml&uri=' +
                               BASE_URL + '/vocabulary/').content.decode('utf-8')
        assert """<?xml version="1.0" encoding="UTF-8"?>
<rdf:RDF
   xmlns:ldp="http://www.w3.org/ns/ldp#"
   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
   xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
   xmlns:reg="http://purl.org/linked-data/registry#"
   xmlns:xhv="https://www.w3.org/1999/xhtml/vocab#"
>""" in content, BASE_URL


def test_vocabulary_register_reg_view_app_json():
    for BASE_URL in BASE_URLS:
        content = requests.get(BASE_URL + '/vocabulary/?vocab_id=&_view=reg&_format=application/json&uri=' + BASE_URL +
                               '/vocabulary/').content.decode('utf-8')
        content = json.loads(content)
        assert 'uri' and 'label' and 'comment' and 'contained_item_classes' and 'default_view' and 'register_items' \
               and 'views' in content, BASE_URL


def test_vocabulary_register_reg_view_ld_json():
    for BASE_URL in BASE_URLS:
        content = requests.get(BASE_URL + '/vocabulary/?vocab_id=&_view=reg&_format=application/ld+json&uri=' + BASE_URL +
                               '/vocabulary/').content.decode('utf-8')
        content = json.loads(content)
        assert '@id' in content[0].keys(), BASE_URL


def test_vocabulary_register_reg_view_text_n3():
    for BASE_URL in BASE_URLS:
        content = requests.get(BASE_URL + '/vocabulary/?vocab_id=&_view=reg&_format=text/n3&uri=' + BASE_URL +
                               '/vocabulary/').content.decode('utf-8')
    assert """@prefix ereg: <https://promsns.org/def/eregistry#> .
@prefix ldp: <http://www.w3.org/ns/ldp#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix reg: <http://purl.org/linked-data/registry#> .
@prefix xhv: <https://www.w3.org/1999/xhtml/vocab#> .
@prefix xml: <http://www.w3.org/XML/1998/namespace> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .""" in content, BASE_URL


def test_vocabulary_register_reg_view_app_n3():
    for BASE_URL in BASE_URLS:
        content = requests.get(BASE_URL + '/vocabulary/?vocab_id=&_view=reg&_format=application/n-triples&uri=' +
                               BASE_URL + '/vocabulary/').content.decode('utf-8')
        content = content.split('\n')
        for line in content:
            line = line.strip()
            if line != '':
                result = re.search(N_TRIPLES_PATTERN, line)
                assert result is not None, 'URL: {} \n\nLine: {}'.format(BASE_URL, line)


def test_vocabulary_register_alternates_view_html():
    for BASE_URL in BASE_URLS:
        content = requests.get(BASE_URL + '/vocabulary/?_view=alternates').content.decode('utf-8')
        assert '<td><a href="https://promsns.org/def/alt">https://promsns.org/def/alt</a></td>' in content
        assert '<h1>Alternates View</h1>' in content, BASE_URL


def test_vocabulary_register_alternates_view_app_json():
    for BASE_URL in BASE_URLS:
        content = requests.get(BASE_URL + '/vocabulary/?_view=alternates&_format=application/json&uri=' + BASE_URL +
                               '/vocabulary/').content.decode('utf-8')
        content = json.loads(content)
        assert content['uri'] == BASE_URL + '/vocabulary/'
        assert content['default_view'] == 'reg'
        assert 'ckan' and 'reg' and 'alternates' in content['views'], BASE_URL


def test_vocabulary_register_alternates_view_turtle():
    for BASE_URL in BASE_URLS:
        content = requests.get(BASE_URL + '/vocabulary/?_view=alternates&_format=text/turtle&uri=' + BASE_URL +
                               '/vocabulary/').content.decode('utf-8')
        assert """@prefix alt: <http://promsns.org/def/alt#> .
@prefix dct: <http://purl.org/dc/terms/> .
@prefix prof: <https://w3c.github.io/dxwg/profiledesc#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xml: <http://www.w3.org/XML/1998/namespace> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .""" in content, BASE_URL


def test_vocabulary_register_alternates_view_xml():
    for BASE_URL in BASE_URLS:
        content = requests.get(BASE_URL + '/vocabulary/?_view=alternates&_format=application/rdf+xml&uri=' + BASE_URL +
                               '/vocabulary/').content.decode('utf-8')
        assert """<?xml version="1.0" encoding="UTF-8"?>
<rdf:RDF
   xmlns:alt="http://promsns.org/def/alt#"
   xmlns:dct="http://purl.org/dc/terms/"
   xmlns:prof="https://w3c.github.io/dxwg/profiledesc#"
   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
   xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
>""" in content, BASE_URL


def test_vocabulary_register_alternates_view_ld_json():
    for BASE_URL in BASE_URLS:
        content = requests.get(BASE_URL + '/vocabulary/?_view=alternates&_format=application/ld+json&uri=' + BASE_URL +
                               '/vocabulary/').content.decode('utf-8')
        content = json.loads(content)
        assert '@id' in content[0].keys(), BASE_URL


def test_vocabulary_register_alternates_view_text_n3():
    for BASE_URL in BASE_URLS:
        content = requests.get(BASE_URL + '/vocabulary/?_view=alternates&_format=text/n3&uri=' + BASE_URL +
                               '/vocabulary/').content.decode('utf-8')
        assert """@prefix alt: <http://promsns.org/def/alt#> .
@prefix dct: <http://purl.org/dc/terms/> .
@prefix prof: <https://w3c.github.io/dxwg/profiledesc#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xml: <http://www.w3.org/XML/1998/namespace> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .""" in content, BASE_URL


def test_vocabulary_register_alternates_view_app_n_triples():
    for BASE_URL in BASE_URLS:
        content = requests.get(BASE_URL + '/vocabulary/?_view=alternates&_format=application/n-triples&uri=' + BASE_URL +
                               '/vocabulary/').content.decode('utf-8')
        content = content.split('\n')
        for line in content:
            line = line.strip()
            if line != '':
                result = re.search(N_TRIPLES_PATTERN, line)
                assert result is not None, 'URL: {} \n\nLine: {}'.format(BASE_URL, line)