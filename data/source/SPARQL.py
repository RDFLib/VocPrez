import logging
import dateutil.parser
from flask import g
from data.source._source import Source
from model.vocabulary import Vocabulary
import _config as config
import re

if hasattr(config, 'DEFAULT_LANGUAGE:'):
    DEFAULT_LANGUAGE = config.DEFAULT_LANGUAGE
else:
    DEFAULT_LANGUAGE = 'en'

class SPARQL(Source):
    """Source for a generic SPARQL endpoint
    """

    def __init__(self, vocab_id, request, language=None):
        super().__init__(vocab_id, request, language)

    @staticmethod
    def collect(details):
        """
        For this source, one SPARQL endpoint is given for a series of vocabs which are all separate ConceptSchemes

        'gsq-graphdb': {
            'source': VocabSource.SPARQL,
            'sparql_endpoint': 'http://graphdb.gsq.digital:7200/repositories/GSQ_Vocabularies_core'
        },
        """
        logging.debug('SPARQL collect()...')
        
        # Get all the ConceptSchemes from the SPARQL endpoint
        # Interpret each CS as a Vocab
        q = '''
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX dcterms: <http://purl.org/dc/terms/>
            SELECT * WHERE {{
                GRAPH ?g {{
                    ?cs a skos:ConceptScheme .
                    OPTIONAL {{ ?cs skos:prefLabel ?title .
                        FILTER(lang(?title) = "{language}" || lang(?title) = "") }}
                    OPTIONAL {{ ?cs dcterms:created ?created }}
                    OPTIONAL {{ ?cs dcterms:issued ?issued }}
                    OPTIONAL {{ ?cs dcterms:modified ?modified }}
                    OPTIONAL {{ ?cs skos:definition ?description .
                        FILTER(lang(?description) = "{language}" || lang(?description) = "") }}
                }}
            }} 
            ORDER BY ?l
        '''.format(language=DEFAULT_LANGUAGE)
        # record just the IDs & title for the VocPrez in-memory vocabs list
        concept_schemes = Source.sparql_query(details['sparql_endpoint'], q, 
                                              sparql_username=details.get('sparql_username'), sparql_password=details.get('sparql_password')
                                              ) or {}
        sparql_vocabs = {}
        for cs in concept_schemes:
            # handling CS URIs that end with '/'
            vocab_id = cs['cs']['value'].replace('/conceptScheme', '').split('/')[-1]
            
            #print("re.search('{}', '{}')".format(details.get('uri_filter_regex'), cs['cs']['value']))
            if details.get('uri_filter_regex') and not re.search(details['uri_filter_regex'], cs['cs']['value']):
                logging.debug('Skipping vocabulary {}'.format(vocab_id))
                continue
            
            if len(vocab_id) < 2:
                vocab_id = cs['cs']['value'].split('/')[-2]
                
            sparql_vocabs[vocab_id] = Vocabulary(
                vocab_id,
                cs['cs']['value'].replace('/conceptScheme', ''),
                cs['title'].get('value') or vocab_id if cs.get('title') else vocab_id, # Need string value for sorting, not None
                cs['description'].get('value') if cs.get('description') is not None else None,
                None,  # none of these SPARQL vocabs have creator info yet # TODO: add creator info to GSQ vocabs
                dateutil.parser.parse(cs.get('created').get('value')) if cs.get('created') is not None else None,
                # dct:issued not in Vocabulary
                # dateutil.parser.parse(cs.get('issued').get('value')) if cs.get('issued') is not None else None,
                dateutil.parser.parse(cs.get('modified').get('value')) if cs.get('modified') is not None else None,
                None,  # versionInfo
                config.VocabSource.SPARQL,
                cs['cs']['value'],
                sparql_endpoint=details['sparql_endpoint'],
                sparql_username=details['sparql_username'],
                sparql_password=details['sparql_password']
            )
        g.VOCABS = {**g.VOCABS, **sparql_vocabs}
        logging.debug('SPARQL collect() complete.')
