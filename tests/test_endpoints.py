import requests
import json
import re

BASE_URL = "http://dawe.surroundaustralia.com"
# BASE_URL = "https://vocabs.gsq.digital/"
VOCABS_LIST_URI_SEG = "/vocabulary/"

N_TRIPLES_PATTERN = (
    r'(_:(.+)|<.+>) (_:(.+)|<.+>) ("(.+)"@en)|(_:(.+)|(".+"\^\^)?<.+>) .'
)


#
# -- Test static pages -------------------------------------------------------------------------------------------------
#
def test_index_html():
    content = requests.get(BASE_URL).content.decode("utf-8")
    assert '<div id="vocprez">' in content, BASE_URL


def test_about_html():
    content = requests.get(BASE_URL + "/about").content.decode("utf-8")
    assert "<p>VocPrez is used by:</p>" in content, BASE_URL


def test_search_html():
    content = requests.get(BASE_URL + "/search").content.decode("utf-8")
    assert "<h1>Search</h1>" in content, BASE_URL


def test_sparql_html():
    content = requests.get(BASE_URL + "/sparql").content.decode("utf-8")
    assert "<h1>SPARQL</h1>" in content, BASE_URL


#
# -- Test system dataset -----------------------------------------------------------------------------------------------
#
def test_index_default_rdf():  # SDO
    r = requests.get(BASE_URL, headers={"Accept": "text/turtle"})
    content = r.content.decode("utf-8")
    assert "text/turtle" in r.headers["Content-Type"]
    assert "a sdo:Dataset ;" in content, BASE_URL


def test_index_dcat_rdf():
    r = requests.get(
        BASE_URL,
        headers={"Accept": "text/turtle", "Accept-Profile": "<https://www.w3.org/TR/vocab-dcat/>"}
    )
    content = r.content.decode("utf-8")
    assert "text/turtle" in r.headers["Content-Type"]
    assert "a dcat:Dataset ;" in content, BASE_URL


def test_index_alt_html():
    content = requests.get(BASE_URL + "?_profile=alt").content.decode("utf-8")
    assert '<h1>Alternate Profiles</h1>' in content, BASE_URL


def test_index_alt_rdf():
    r = requests.get(
        BASE_URL,
        headers={"Accept": "text/turtle", "Accept-Profile": "<http://www.w3.org/ns/dx/conneg/altr>"}
    )
    content = r.content.decode("utf-8")
    assert "text/turtle" in r.headers["Content-Type"]
    assert "<https://www.w3.org/TR/vocab-dcat/> a prof:Profile ;" in content, BASE_URL


#
# -- Test vocabulary register ------------------------------------------------------------------------------------------
#
def test_vocab_list_default_html():
    content = requests.get(BASE_URL + VOCABS_LIST_URI_SEG).content.decode("utf-8")
    assert "<h3>Filter</h3>" in content, BASE_URL


def test_vocab_list_default_rdf():  # DCAT Catalogue
    r = requests.get(
        BASE_URL + VOCABS_LIST_URI_SEG,
        headers={"Accept": "text/turtle"}
    )
    content = r.content.decode("utf-8")
    assert "text/turtle" in r.headers["Content-Type"]
    assert "a dcat:Catalogue ;" in content, BASE_URL


def test_vocab_list_mem_rdf():
    r = requests.get(
        BASE_URL + VOCABS_LIST_URI_SEG,
        headers={"Accept": "text/turtle", "Accept-Profile": "<https://w3id.org/profile/mem>"}
    )
    content = r.content.decode("utf-8")
    assert "text/turtle" in r.headers["content-type"]
    assert "a rdf:Bag ;" in content, BASE_URL


#
# -- Test Vocabulary Instance ------------------------------------------------------------------------------------------
#
def test_vocab_skos_html():
    # get the list of vocabs to get the URI of one vocab
    vocabs_rdf = requests.get(BASE_URL + "/vocab/?_profile=mem&_mediatype=text/turtle").content.decode("utf-8")
    m = re.findall(r"<(.*)> rdfs:label \"(.*)\" .", vocabs_rdf)
    vocab_eg_uri = m[0][0]

    # get one vocab
    content = requests.get(
        BASE_URL + "/object?vocab_uri=" + vocab_eg_uri
    ).content.decode("utf-8")

    assert '<th><a href="http://www.w3.org/2004/02/skos/core#hasTopConcept">Concept Hierarchy</a></th>' in content


def test_vocab_skos_rdf():
    # get the list of vocabs to get the URI of one vocab
    vocabs_rdf = requests.get(BASE_URL + "/vocab/?_profile=mem&_mediatype=text/turtle").content.decode("utf-8")
    m = re.findall(r"<(.*)> rdfs:label \"(.*)\" .", vocabs_rdf)
    vocab_eg_uri = m[0][0]

    # get one vocab
    r = requests.get(
        BASE_URL + "/object?vocab_uri=" + vocab_eg_uri + "&_mediatype=text/turtle"
    )
    content = r.content.decode("utf-8")

    assert "text/turtle" in r.headers["Content-Type"]
    assert "a skos:ConceptScheme ;" in content


def test_vocab_rdf_alt():
    # get the list of vocabs to get the URI of one vocab
    vocabs_rdf = requests.get(BASE_URL + "/vocab/?_profile=mem&_mediatype=text/turtle").content.decode("utf-8")
    m = re.findall(r"<(.*)> rdfs:label \"(.*)\" .", vocabs_rdf)
    vocab_eg_uri = m[0][0]

    # get one vocab
    r = requests.get(
        BASE_URL + "/object?vocab_uri=" + vocab_eg_uri + "&_profile=alt&_mediatype=text/turtle"
    )
    content = r.content.decode("utf-8")

    assert "text/turtle" in r.headers["Content-Type"]
    assert "<{}> altr:hasDefaultRepresentation".format(vocab_eg_uri) in content
