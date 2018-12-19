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

    def get_vocabulary(self):
        r = self.s.post(
            config.VB_ENDPOINT + '/SPARQL/evaluateQuery',
            data={
                'query':
                    '''PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
                    PREFIX dct: <http://purl.org/dc/terms/>
                    PREFIX owl: <http://www.w3.org/2002/07/owl#>
                    SELECT *
                    WHERE {
                      ?s a skos:ConceptScheme ;
                      skos:prefLabel ?t .
                      OPTIONAL {?s dct:description ?d }
                      OPTIONAL {?s dct:creator ?c }
                      OPTIONAL {?s dct:created ?cr }
                      OPTIONAL {?s dct:modified ?m }
                      OPTIONAL {?s owl:versionInfo ?v }
                    }''',
                'ctx_project': self.vocab_id
            }
        )

        r2 = self.s.post(
            config.VB_ENDPOINT + '/SPARQL/evaluateQuery',
            data={
                'query':
                    '''PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
                    SELECT *
                    WHERE {
                      ?tc skos:topConceptOf ?s ;
                          skos:prefLabel ?pl .
                    }''',
                'ctx_project': self.vocab_id
            }
        )
        top_concepts = json.loads(r2.content.decode('utf-8'))['result']['sparql']['results']['bindings']
        if r.status_code == 200:
            metadata = json.loads(r.content.decode('utf-8'))['result']['sparql']['results']['bindings'][0]

            from model.vocabulary import Vocabulary
            return Vocabulary(
                self.vocab_id,
                metadata['s']['value'],
                metadata['t']['value'],
                metadata['d']['value']
                if metadata.get('d') is not None else None,
                metadata.get('c').get('value')
                if metadata.get('c') is not None else None,
                metadata.get('cr').get('value')
                if metadata.get('cr') is not None else None,
                metadata.get('m').get('value')
                if metadata.get('m') is not None else None,
                metadata.get('v').get('value')
                if metadata.get('v') is not None else None,
                [(x.get('tc').get('value'), x.get('pl').get('value')) for x in top_concepts],
                None,
                None
            )
        else:
            raise VbException('There was an error: ' + r.content.decode('utf-8'))

    def get_collection(self, uri):
        pass

    def get_concept(self, uri):
        q = '''PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT *
            WHERE {{
              <{0}> skos:prefLabel ?pl .
              OPTIONAL {{<{0}> skos:definition ?d }}
            }}'''.format(uri)
        r = self.s.post(
            config.VB_ENDPOINT + '/SPARQL/evaluateQuery',
            data={
                'query': q,
                'ctx_project': self.vocab_id
            }
        )
        metadata = json.loads(r.content.decode('utf-8'))['result']['sparql']['results']['bindings'][0]

        # get the concept's altLabels
        q = '''PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT *
            WHERE {{
              <{}> skos:altLabel ?al .
            }}'''.format(uri)
        r = self.s.post(
            config.VB_ENDPOINT + '/SPARQL/evaluateQuery',
            data={
                'query': q,
                'ctx_project': self.vocab_id
            }
        )
        altLabels = json.loads(r.content.decode('utf-8'))['result']['sparql']['results']['bindings']

        # get the concept's hiddenLabels
        q = '''PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT *
            WHERE {{
              <{}> skos:hiddenLabel ?hl .
            }}'''.format(uri)
        r = self.s.post(
            config.VB_ENDPOINT + '/SPARQL/evaluateQuery',
            data={
                'query': q,
                'ctx_project': self.vocab_id
            }
        )
        hiddenLabels = json.loads(r.content.decode('utf-8'))['result']['sparql']['results']['bindings']

        # get the concept's broaders
        q = ''' PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT *
            WHERE {{
              <{}> skos:broader ?b .
              ?b skos:prefLabel ?pl .
            }}'''.format(uri)
        r = self.s.post(
            config.VB_ENDPOINT + '/SPARQL/evaluateQuery',
            data={
                'query': q,
                'ctx_project': self.vocab_id
            }
        )
        broaders = json.loads(r.content.decode('utf-8'))['result']['sparql']['results']['bindings']

        # get the concept's narrowers
        q = '''PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT *
            WHERE {{
              <{}> skos:narrower ?n .
              ?n skos:prefLabel ?pl .
            }}'''.format(uri)
        r = self.s.post(
            config.VB_ENDPOINT + '/SPARQL/evaluateQuery',
            data={
                'query': q,
                'ctx_project': self.vocab_id
            }
        )
        narrowers = json.loads(r.content.decode('utf-8'))['result']['sparql']['results']['bindings']

        from model.concept import Concept
        return Concept(
            self.vocab_id,
            uri,
            metadata['pl']['value'],
            metadata.get('d').get('value') if metadata.get('d') is not None else None,
            [x.get('al').get('value') for x in altLabels],
            [x.get('hl').get('value') for x in hiddenLabels],
            metadata.get('sc').get('value') if metadata.get('sc') is not None else None,
            metadata.get('cn').get('value') if metadata.get('cn') is not None else None,
            [{'uri': x.get('b').get('value'), 'prefLabel': x.get('pl').get('value')} for x in broaders],
            [{'uri': x.get('n').get('value'), 'prefLabel': x.get('pl').get('value')} for x in narrowers],
            None  # TODO: replace Sem Properties sub
        )

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

    def get_concept_hierarchy(self, vocab):
        r = self.s.post(
            config.VB_ENDPOINT + '/SPARQL/evaluateQuery',
            data={
                'query':
                    '''
                    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

                    SELECT ?super ?sub ?pl (COUNT(?mid) as ?dist) 
                    WHERE { 
                      ?super skos:narrower* ?mid .
                      ?mid skos:narrower+ ?sub .
                      ?sub skos:prefLabel ?pl .
                    }
                    GROUP BY ?super ?sub ?pl''',
                'ctx_project': self.vocab_id
            }
        )

        if r.status_code == 200:
            cs = json.loads(r.content.decode('utf-8'))['result']['sparql']['results']['bindings']
            return [
                (
                    c['super']['value'],
                    c['sub']['value'],
                    c['pl']['value'],
                    c['dist']['value']
                 ) for c in cs
            ]
        else:
            raise VbException('There was an error: ' + r.content.decode('utf-8'))

    def get_object_class(self, uri):
        """Gets the class of the object.

        Classes restricted to being one of voaf:Vocabulary, skos:ConceptScheme, skos:Collection or skos:Collection

        :param uri: the URI of the object

        :return: the URI of the class of the object
        :rtype: :class:`string`
        """
        q = '''
            SELECT ?c
            WHERE {{
                <{}> a ?c .
            }}
        '''.format(uri)
        r = self.s.post(
            config.VB_ENDPOINT + '/SPARQL/evaluateQuery',
            data={
                'query': q,
                'ctx_project': self.vocab_id
            }
        )

        for c in json.loads(r.content.decode('utf-8'))['result']['sparql']['results']['bindings']:
            if c.get('c')['value'] in self.VOC_TYPES:
                return c.get('c')['value']

        return None


if __name__ == '__main__':
    # print(VB('Test_Rock_Types_Vocabulary').list_vocabularies())
    import pprint
    # pprint.pprint(VB('x').list_vocabularies())
    pprint.pprint(VB('Test_Rock_Types_Vocabulary').get_vocabulary())
    # pprint.pprint(VB('Test_Rock_Types')._get_narrower('http://pid.geoscience.gov.au/def/voc/test-rock-types/igneous'))
