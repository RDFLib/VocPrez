import logging
import dateutil.parser
from data.source._source import Source
from flask import g
from SPARQLWrapper import SPARQLWrapper, JSON
import _config as config
import requests
import json


class RVA(Source):
    """Source for Research Vocabularies Australia
    """

    hierarchy = {}

    def __init__(self, vocab_id, request):
        super().__init__(vocab_id, request)

    @staticmethod
    def collect(details):
        logging.debug('RVA collect()...')
        # For this source, vocabs must be nominated via their ID (a number) in details['vocab_ids']
        rva_vocabs = {}
        for vocab in details['vocabs']:
            r = requests.get(
                    details['api_endpoint'].format(vocab['ardc_id']),
                    headers={'Accept': 'application/json'}
            )
            if r.status_code == 200:
                j = json.loads(r.text)
                rva_vocabs['rva-' + str(vocab['ardc_id'])] = {
                    'source': config.VocabSource.RVA,
                    'uri': vocab['uri'],
                    'concept_scheme': vocab['uri'],
                    'title': j.get('title'),
                    'description': j.get('description'),
                    'owner': j.get('owner'),
                    'date_created': dateutil.parser.parse(j.get('creation-date')),
                    'date_issued': None,
                    'date_modified': None,
                    # version
                    # creators
                    'sparql_endpoint': j['version'][0]['access-point'][0]['ap-api-sparql']['url']
                }
            else:
                logging.error('Could not get vocab {} from RVA'.format(vocab['ardc_id']))
        g.VOCABS = {**g.VOCABS, **rva_vocabs}
        logging.debug('RVA collect() complete')

    def list_collections(self):
        q = '''
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT *
            WHERE {
                ?c a skos:Concept .
                ?c rdfs:label ?l .
            }'''
        collections = Source.sparql_query(g.VOCABS[self.vocab_id]['details']['sparql_endpoint'], q)

        return [(x.get('c').get('value'), x.get('l').get('value')) for x in collections]

    def get_vocabulary(self):
        from model.vocabulary import Vocabulary

        return Vocabulary(
            self.vocab_id,
            g.VOCABS[self.vocab_id]['uri'],
            g.VOCABS[self.vocab_id]['title'],
            g.VOCABS[self.vocab_id].get('description'),
            g.VOCABS[self.vocab_id].get('owner'),
            g.VOCABS[self.vocab_id].get('date_created'),
            g.VOCABS[self.vocab_id].get('date_modified'),
            g.VOCABS[self.vocab_id].get('version'),
            hasTopConcepts=self.get_top_concepts(),
            conceptHierarchy=self.get_concept_hierarchy()
        )

    def get_collection(self, uri):
        sparql = SPARQLWrapper(g.VOCABS.get(self.vocab_id).get('sparql_endpoint'))
        q = '''PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT *
            WHERE {{
              <{}> rdfs:label ?l .
              OPTIONAL {{?s rdfs:comment ?c }}
            }}'''.format(uri)
        sparql.setQuery(q)
        sparql.setReturnFormat(JSON)
        metadata = sparql.query().convert()['results']['bindings']

        # get the collection's members
        q = ''' PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT *
            WHERE {{
              <{}> skos:member ?m .
              ?n skos:prefLabel ?pl .
            }}'''.format(uri)
        sparql.setQuery(q)
        sparql.setReturnFormat(JSON)
        members = sparql.query().convert()['results']['bindings']

        from model.collection import Collection
        return Collection(
            self.vocab_id,
            uri,
            metadata[0]['l']['value'],
            metadata[0].get('c').get('value') if metadata[0].get('c') is not None else None,
            [(x.get('m').get('value'), x.get('m').get('value')) for x in members]
        )

    def get_object_class(self, uri):
        sparql = SPARQLWrapper(g.VOCABS.get(self.vocab_id).get('sparql_endpoint'))
        q = '''
            SELECT ?c
            WHERE {{
                <{}> a ?c .
            }}
        '''.format(uri)
        sparql.setQuery(q)

        sparql.setReturnFormat(JSON)
        for c in sparql.query().convert()['results']['bindings']:
            if c.get('c')['value'] in self.VOC_TYPES:
                return c.get('c')['value']

        return None
