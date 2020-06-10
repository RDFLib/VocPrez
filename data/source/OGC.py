import logging
import dateutil.parser
from flask import g
from data.source._source import Source
from model.vocabulary import Vocabulary
import _config as config
from SPARQLWrapper import SPARQLWrapper

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

    def get_concept_hierarchy(self):
        return []
        """
        Function to draw concept hierarchy for vocabulary
        """

        def build_hierarchy(bindings_list, broader_concept=None, level=0):
            """
            Recursive helper function to build hierarchy list from a bindings list
            Returns list of tuples: (<level>, <concept>, <concept_preflabel>, <broader_concept>)
            """
            level += 1  # Start with level 1 for top concepts
            hierarchy = []

            narrower_list = sorted(
                [
                    binding_dict
                    for binding_dict in bindings_list
                    if (  # Top concept
                        (broader_concept is None)
                        and (binding_dict.get("broader_concept") is None)
                    )
                    or
                    # Narrower concept
                    (
                        (binding_dict.get("broader_concept") is not None)
                        and (
                            binding_dict["broader_concept"]["value"] == broader_concept
                        )
                    )
                ],
                key=lambda binding_dict: binding_dict["concept_preflabel"]["value"],
            )
            for binding_dict in narrower_list:
                concept = binding_dict["concept"]["value"]
                hierarchy += [
                    (
                        level,
                        concept,
                        binding_dict["concept_preflabel"]["value"],
                        binding_dict["broader_concept"]["value"]
                        if binding_dict.get("broader_concept")
                        else None,
                    )
                ] + build_hierarchy(bindings_list, concept, level)
            return hierarchy

        vocab = g.VOCABS[self.vocab_id]

        q = """
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX dct: <http://purl.org/dc/terms/>
            
            SELECT distinct ?concept ?concept_preflabel ?broader_concept
            WHERE {{
                {{
                    {{ ?concept skos:inScheme <{vocab_uri}> . }}
                    UNION
                    {{ ?concept skos:topConceptOf <{vocab_uri}> . }}
                    UNION
                    {{ <{vocab_uri}> skos:hasTopConcept ?concept . }}  
                    
                    ?concept skos:prefLabel ?concept_preflabel .
                    OPTIONAL {{ 
                        ?concept skos:broader ?broader_concept .
                        ?broader_concept skos:inScheme <{vocab_uri}> .
                    }}
                    
                    FILTER(lang(?concept_preflabel) = "{language}" || lang(?concept_preflabel) = "")
            }}
            ORDER BY ?concept_preflabel
            """.format(
            vocab_uri=vocab.concept_scheme_uri, language=self.language
        )
        sparql = SPARQLWrapper(config.VOCAB_SOURCES["ogc"]["sparql_endpoint"])
        sparql.setQuery(q)
        bindings_list = sparql.query().convert().getElementsByTagName('result')

        # bindings_list = Source.sparql_query(
        #     vocab.sparql_endpoint, query, vocab.sparql_username, vocab.sparql_password
        # )

        assert bindings_list is not None, "SPARQL concept hierarchy query failed"

        hierarchy = build_hierarchy(bindings_list)

        return Source.draw_concept_hierarchy(hierarchy, self.request, self.vocab_id)