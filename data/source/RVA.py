import logging
import requests
import json
import dateutil.parser
from flask import g
from data.source._source import Source
from model.vocabulary import Vocabulary
import _config as config


class RVA(Source):
    """Source for Research Vocabularies Australia
    """

    def __init__(self, vocab_id, request):
        super().__init__(vocab_id, request)

    @staticmethod
    def collect(details):
        """
        For this source, vocabs must be nominated via their ID (a number) in details['vocab_ids']

        'rva': {
            'source': VocabSource.RVA,
            'api_endpoint': 'https://vocabs.ands.org.au/registry/api/resource/vocabularies/{}?includeAccessPoints=true',
            'vocabs': [
                {
                    'ardc_id': 50,
                    'uri': 'http://resource.geosciml.org/classifierscheme/cgi/2016.01/geologicunittype',
                },
                {
                    'ardc_id': 52,
                    'uri': 'http://resource.geosciml.org/classifierscheme/cgi/2016.01/contacttype',
                },
                {
                    'ardc_id': 57,
                    'uri': 'http://resource.geosciml.org/classifierscheme/cgi/2016.01/stratigraphicrank',
                }
            ]
        }
        """

        # Get the details for each vocab from the RVA catalogue API
        logging.debug('RVA collect()...')
        rva_vocabs = {}
        for vocab in details['vocabs']:
            r = requests.get(
                    details['api_endpoint'].format(vocab['ardc_id']),
                    headers={'Accept': 'application/json'}
            )
            if r.status_code == 200:
                j = json.loads(r.text)
                vocab_id = 'rva-' + str(vocab['ardc_id'])
                rva_vocabs[vocab_id] = Vocabulary(
                    vocab_id,
                    vocab['uri'],
                    j['title'],
                    j.get('description'),
                    j.get('creator'),
                    dateutil.parser.parse(j.get('creation-date')),
                    None,
                    j['version'][0]['title'],
                    config.VocabSource.RVA,
                    vocab['uri'],
                    sparql_endpoint=j['version'][0]['access-point'][0]['ap-api-sparql']['url']
                )
            else:
                logging.error('Could not get vocab {} from RVA'.format(vocab['ardc_id']))
        g.VOCABS = {**g.VOCABS, **rva_vocabs}
        logging.debug('RVA collect() complete')
