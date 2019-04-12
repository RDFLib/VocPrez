import logging
import dateutil.parser
from flask import g
from data.source._source import Source
import _config as config


class SPARQL(Source):
    """Source for a generic SPARQL endpoint
    """

    def __init__(self, vocab_id, request):
        super().__init__(vocab_id, request)

    @staticmethod
    def collect(details):
        logging.debug('SPARQL collect()...')
        # Treat each skos:ConceptScheme discoverable at this endpoint as a vocab
        #
        # get all the ConceptSchemes from the SPARQL endpoint
        # interpret a CS as a Vocab
        q = '''
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX dcterms: <http://purl.org/dc/terms/>
            SELECT * WHERE {
                GRAPH ?g {
                    ?cs a skos:ConceptScheme .
                    OPTIONAL { ?cs skos:prefLabel ?title }
                    OPTIONAL { ?cs dcterms:created ?created }
                    OPTIONAL { ?cs dcterms:issued ?issued }
                    OPTIONAL { ?cs dcterms:modified ?modified }
                    OPTIONAL { ?cs skos:definition ?description }
                }
            } 
            ORDER BY ?l
        '''
        # record just the IDs & title for the VocPrez in-memory vocabs list
        concept_schemes = Source.sparql_query(details['sparql_endpoint'], q)
        sparql_vocabs = {}
        for cs in concept_schemes:
            # handling CS URIs that end with '/'
            vocab_id = cs['cs']['value'].replace('/conceptScheme', '').split('/')[-1]
            if len(vocab_id) < 2:
                vocab_id = cs['cs']['value'].split('/')[-2]

            sparql_vocabs[vocab_id] = {
                'uri': cs['cs']['value'].replace('/conceptScheme', ''),
                'concept_scheme': cs['cs']['value'],
                'source': config.VocabSource.SPARQL,
                'title': cs.get('title').get('value') if cs.get('title') is not None else None,
                'date_created': dateutil.parser.parse(cs.get('created').get('value')) if cs.get('created') is not None else None,
                'date_issued': dateutil.parser.parse(cs.get('issued').get('value')) if cs.get('issued') is not None else None,
                'date_modified': dateutil.parser.parse(cs.get('modified').get('value')) if cs.get('modified') is not None else None,
                'description': cs.get('description').get('value') if cs.get('description') is not None else None,
                'sparql_endpoint': details['sparql_endpoint']
                # version
                # creators
            }
        g.VOCABS = {**g.VOCABS, **sparql_vocabs}
        logging.debug('SPARQL collect() complete.')

    def get_vocabulary(self):
        from model.vocabulary import Vocabulary

        return Vocabulary(
            self.vocab_id,
            g.VOCABS[self.vocab_id]['uri'],
            g.VOCABS[self.vocab_id]['title'],
            g.VOCABS[self.vocab_id].get('description'),
            None,  # we don't yet have creator info stored for GSQ vocabs
            g.VOCABS[self.vocab_id].get('date_created'),
            g.VOCABS[self.vocab_id].get('date_modified'),
            g.VOCABS[self.vocab_id].get('version'),
            hasTopConcepts=self.get_top_concepts(),
            conceptHierarchy=self.get_concept_hierarchy()
        )
