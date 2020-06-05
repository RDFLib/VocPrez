import logging
import dateutil.parser
from flask import g
from data.source._source import Source
from model.vocabulary import Vocabulary
import _config as config

if hasattr(config, "DEFAULT_LANGUAGE:"):
    DEFAULT_LANGUAGE = config.DEFAULT_LANGUAGE
else:
    DEFAULT_LANGUAGE = "en"


class OGC(Source):
    """Source for a generic SPARQL endpoint
    """

    def __init__(self, vocab_id, request, language=None):
        super().__init__(vocab_id, request, language)

    @staticmethod
    def collect(details):
        """
        For this source, one SPARQL endpoint is given for a series of vocabs which are all separate ConceptSchemes

        'ga-jena-fuseki': {
            'source': VocabSource.SPARQL,
            'sparql_endpoint': 'http://dev2.nextgen.vocabs.ga.gov.au/fuseki/vocabs',
            'sparql_username': '<sparql_user>', # Optional username for SPARQL endpoint
            'sparql_password': '<sparql_password>', # Optional password for SPARQL endpoint
            #'uri_filter_regex': '.*', # Regular expression to filter vocabulary URIs - Everything
            #'uri_filter_regex': '^http(s?)://pid.geoscience.gov.au/def/voc/ga/', # Regular expression to filter vocabulary URIs - GA
            #'uri_filter_regex': '^https://gcmdservices.gsfc.nasa.gov', # Regular expression to filter vocabulary URIs - GCMD
            'uri_filter_regex': '^http(s?)://resource.geosciml.org/', # Regular expression to filter vocabulary URIs - CGI

        },
        """
        logging.debug("SPARQL collect()...")

        # Get all the ConceptSchemes from the SPARQL endpoint
        # Interpret each CS as a Vocab
        q = """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX dc: <http://purl.org/dc/elements/1.1/>
            PREFIX dcterms: <http://purl.org/dc/terms/>
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT * 
            WHERE {
              ?cs a skos:ConceptScheme .
              OPTIONAL { 
                { ?cs skos:prefLabel ?title }
                UNION
                { ?cs rdfs:label ?title }  
              }
              OPTIONAL { 
                { ?cs dcterms:created ?created }
                UNION
                { ?cs dc:date ?created }  
              }
              OPTIONAL { ?cs dcterms:issued ?issued }
              OPTIONAL { ?cs dcterms:modified ?modified }
              OPTIONAL { ?cs owl:versionInfo ?version }
              OPTIONAL { ?cs skos:definition ?description }
            }
            ORDER BY ?title
            """
        from SPARQLWrapper import SPARQLWrapper
        sparql = SPARQLWrapper(config.VOCAB_SOURCES["ogc"]["sparql_endpoint"])
        sparql.setQuery(q)

        results = sparql.query().convert().getElementsByTagName('result')

        def get_node_text(node):
            nodelist = node.childNodes
            result = []
            for node in nodelist:
                if node.nodeType == node.TEXT_NODE:
                    result.append(node.data)
            return ''.join(result)

        vocabs = {}
        for result in results:
            uri_xml = result.getElementsByTagName('uri')[0]
            uri = get_node_text(uri_xml)
            vocab_id = uri[uri.rfind("/")+1:]

            title = None
            description = None
            created = None
            bindings = result.getElementsByTagName('binding')
            for binding in bindings:
                name = binding.getAttribute("name")
                if name == "title":
                    title_xml = binding.getElementsByTagName('literal')[0]
                    title = get_node_text(title_xml)
                if name == "description":
                    description_xml = binding.getElementsByTagName('literal')[0]
                    description = get_node_text(description_xml)
                if name == "created":
                    created_xml = binding.getElementsByTagName('literal')[0]
                    created = get_node_text(created_xml)

            vocabs[vocab_id] = Vocabulary(
                vocab_id,
                uri,
                title if title is not None else "x",
                description,
                None,
                created,
                None,
                None,
                config.VocabSource.OGC,
                uri
            )

        g.VOCABS = {**g.VOCABS, **vocabs}
        logging.debug("SPARQL collect() complete.")
