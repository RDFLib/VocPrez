from data.source import Source
import requests
import json
import _config as config


class VbAuthException(Exception):
    pass


class VbException(Exception):
    pass


class VB(Source):
    def __init__(self, vocab_id):
        self.vocab_id = vocab_id
        s = requests.session()
        r = s.post(
            config.VB_ENDPOINT + '/Auth/login',
            data={
                'email': config.VB_USER,
                'password': config.VB_PASSWORD
            }
        )
        if r.status_code == 200:
            self.s = s
        else:
            raise VbAuthException('Not able to log in. Error from VB is: ' + r.content.decode('utf-8'))

    def list_vocabularies(self):
        r = self.s.get(config.VB_ENDPOINT + '/Projects/listProjects', params={'consumer': 'SYSTEM'})
        if r.status_code == 200:
            d = json.loads(r.content.decode('utf-8'))

            return [(v['baseURI'], v['name']) for v in d['result']]
        else:
            raise VbException('There was an error: ' + r.content.decode('utf-8'))

    def list_collections(self):
        pass

    def list_concepts(self):
        pass

    def _get_narrower(self, uri):
        r = self.s.get(
            config.VB_ENDPOINT + '/SKOS/getNarrowerConcepts',
            params={
                'concept': '<{}>'.format(uri),
                'schemes': '<http://pid.geoscience.gov.au/def/voc/test-rock-types#conceptScheme_633df59e>',
                'includeSubProperties': False,
                'ctx_project': self.vocab_id
            }
        )
        # http://13.54.176.245:1979/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/SKOS/getTopConcepts?schemes=<http://pid.geoscience.gov.au/def/voc/test-rock-types
        if r.status_code == 200:
            narrower = json.loads(r.content.decode('utf-8'))['result']
            # return [(x['@id'], x['show'].replace(' (en)', '')) for x in narrower]
            return narrower

        else:
            raise VbException('There was an error: ' + r.content.decode('utf-8'))

    def _get_concept_hierarchy(self, uri, more):
        if not more:
            return uri
        else:
            self._get_narrower(uri)

    def get_vocabulary(self):
        r = self.s.get(
            config.VB_ENDPOINT + '/SKOS/getTopConcepts',
            params={
                'schemes': '<http://pid.geoscience.gov.au/def/voc/test-rock-types/conceptScheme>',
                'includeSubProperties': False,
                'ctx_project': self.vocab_id
            }
        )
        # http://13.54.176.245:1979/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services/SKOS/getTopConcepts?schemes=<http://pid.geoscience.gov.au/def/voc/test-rock-types
        if r.status_code == 200:
            v = json.loads(r.content.decode('utf-8'))['result']
            return v
        else:
            raise VbException('There was an error: ' + r.content.decode('utf-8'))

    def get_collection(self, uri):
        pass

    def get_concept(self, uri):
        pass

    def get_concept_hierarchy(self, vocab):
        pass

    def get_object_class(self, uri):
        """Gets the class of the object.

        Classes restricted to being one of voaf:Vocabulary, skos:ConceptScheme, skos:Collection or skos:Collection

        :param uri: the URI of the object

        :return: the URI of the class of the object
        :rtype: :class:`string`
        """
        pass


if __name__ == '__main__':
    #print(VB('Test_Rock_Types_Vocabulary').list_vocabularies())
    import pprint
    pprint.pprint(VB('Test_Rock_Types_Vocabulary').get_vocabulary())

    #pprint.pprint(VB('Test_Rock_Types')._get_narrower('http://pid.geoscience.gov.au/def/voc/test-rock-types/igneous'))
