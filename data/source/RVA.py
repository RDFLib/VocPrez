import logging
import requests
import json
import dateutil.parser
from flask import g
from data.source._source import Source
import _config as config


class RVA(Source):
    """Source for Research Vocabularies Australia
    """

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
                    'uri': vocab['uri'],
                    'concept_scheme': vocab['uri'],
                    'source': config.VocabSource.RVA,
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
