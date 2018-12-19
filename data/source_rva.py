from data.source import Source
from SPARQLWrapper import SPARQLWrapper, JSON, TURTLE


class RVA(Source):
    """Source for Research Vocabularies Australia
    """
    VOCAB_ENDPOINTS = {
        'rva-50': {
            'sparql': 'http://vocabs.ands.org.au/repository/api/sparql/ga_geologic-unit-type_v0-1',
            'download': 'https://vocabs.ands.org.au/registry/api/resource/downloads/196/ga_geologic-unit-type_v0-1.ttl'
        },
        'rva-52': {
            'sparql': 'http://vocabs.ands.org.au/repository/api/sparql/ga_contact-type_v0-1',
            'download': 'https://vocabs.ands.org.au/registry/api/resource/downloads/202/ga_contact-type_v0-1.ttl'
        },
        'rva-57': {
            'sparql': 'http://vocabs.ands.org.au/repository/api/sparql/ga_stratigraphic-rank_v0-1',
            'download': 'https://vocabs.ands.org.au/registry/api/resource/downloads/217/ga_stratigraphic-rank_v0-1.ttl'
        },
        'rva-177': {
            'sparql': 'http://vocabs.ands.org.au/repository/api/sparql/ga_association-type_v1-2',
            'download': 'https://vocabs.ands.org.au/registry/api/resource/downloads/741/assoc.ttl'
        },
        'rva-178': {
            'sparql': 'http://vocabs.ands.org.au/repository/api/sparql/ga_feature-of-interest-type_v0-1',
            'download': 'https://vocabs.ands.org.au/registry/api/resource/downloads/491/ga_feature-of-interest-type_v0-1.ttl'
        },
        'rva-185': {
            'sparql': 'http://vocabs.ands.org.au/repository/api/sparql/ga_sample-type_v1-0',
            'download': 'https://vocabs.ands.org.au/registry/api/resource/downloads/518/ga_sample-type_v1-0.ttl'
        },
        'rva-186': {
            'sparql': 'http://vocabs.ands.org.au/repository/api/sparql/ga_ga-data-classification_v1-0',
            'download': 'https://vocabs.ands.org.au/registry/api/resource/downloads/521/ga_ga-data-classification_v1-0.ttl'
        }
    }

    def __init__(self, vocab_id):
        self.vocab_id = vocab_id

    def list_vocabularies(self):
        # this needs to be a static list as we don't want all RVA vocabs
        pass

    def list_collections(self):
        sparql = SPARQLWrapper(self.VOCAB_ENDPOINTS.get(self.vocab_id).get('sparql'))
        sparql.setQuery('''
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT *
            WHERE {
              ?c a skos:Concept .
              ?c rdfs:label ?l .
            }''')
        sparql.setReturnFormat(JSON)
        concepts = sparql.query().convert()['results']['bindings']

        return [(x.get('c').get('value'), x.get('l').get('value')) for x in concepts]

    def list_concepts(self):
        sparql = SPARQLWrapper(self.VOCAB_ENDPOINTS.get(self.vocab_id).get('sparql'))
        sparql.setQuery('''
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT *
            WHERE {
              ?c a skos:Concept .
              ?c skos:prefLabel ?pl .
            }''')
        sparql.setReturnFormat(JSON)
        concepts = sparql.query().convert()['results']['bindings']

        return [(x.get('c').get('value'), x.get('pl').get('value')) for x in concepts]

    def get_vocabulary(self):
        sparql = SPARQLWrapper(self.VOCAB_ENDPOINTS.get(self.vocab_id).get('sparql'))

        # get the basic vocab metadata
        # PREFIX%20skos%3A%20%3Chttp%3A%2F%2Fwww.w3.org%2F2004%2F02%2Fskos%2Fcore%23%3E%0APREFIX%20dct%3A%20%3Chttp%3A%2F%2Fpurl.org%2Fdc%2Fterms%2F%3E%0APREFIX%20owl%3A%20%3Chttp%3A%2F%2Fwww.w3.org%2F2002%2F07%2Fowl%23%3E%0ASELECT%20*%0AWHERE%20%7B%0A%3Fs%20a%20skos%3AConceptScheme%20%3B%0Adct%3Atitle%20%3Ft%20%3B%0Adct%3Adescription%20%3Fd%20%3B%0Adct%3Acreator%20%3Fc%20%3B%0Adct%3Acreated%20%3Fcr%20%3B%0Adct%3Amodified%20%3Fm%20%3B%0Aowl%3AversionInfo%20%3Fv%20.%0A%7D
        sparql.setQuery('''PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX dct: <http://purl.org/dc/terms/>
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            SELECT *
            WHERE {
              ?s a skos:ConceptScheme ;
              dct:title ?t .
              OPTIONAL {?s dct:description ?d }
              OPTIONAL {?s dct:creator ?c }
              OPTIONAL {?s dct:created ?cr }
              OPTIONAL {?s dct:modified ?m }
              OPTIONAL {?s owl:versionInfo ?v }
            }''')
        sparql.setReturnFormat(JSON)
        metadata = sparql.query().convert()

        # get the vocab's top concepts
        sparql.setQuery('''
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT *
            WHERE {
              ?s skos:hasTopConcept ?tc .
              ?tc skos:prefLabel ?pl .
            }''')
        sparql.setReturnFormat(JSON)
        top_concepts = sparql.query().convert()['results']['bindings']

        # TODO: check if there are any common ways to ascertain if a vocab/ConceptScheme has any Collections
        # # get the vocab's collections
        # sparql.setQuery('''
        #     PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        #     SELECT *
        #     WHERE {
        #       ?s skos:hasTopConcept ?tc .
        #       ?tc skos:prefLabel ?pl .
        #     }''')
        # sparql.setReturnFormat(JSON)
        # top_concepts = sparql.query().convert()['results']['bindings']

        from model.vocabulary import Vocabulary
        return Vocabulary(
            self.vocab_id,
            metadata['results']['bindings'][0]['s']['value'],
            metadata['results']['bindings'][0]['t']['value'],
            metadata['results']['bindings'][0]['d']['value']
                if metadata['results']['bindings'][0].get('d') is not None else None,
            metadata['results']['bindings'][0].get('c').get('value')
                if metadata['results']['bindings'][0].get('c') is not None else None,
            metadata['results']['bindings'][0].get('cr').get('value')
                if metadata['results']['bindings'][0].get('cr') is not None else None,
            metadata['results']['bindings'][0].get('m').get('value')
                if metadata['results']['bindings'][0].get('m') is not None else None,
            metadata['results']['bindings'][0].get('v').get('value')
                if metadata['results']['bindings'][0].get('v') is not None else None,
            [(x.get('tc').get('value'), x.get('pl').get('value')) for x in top_concepts],
            None,
            self.VOCAB_ENDPOINTS.get(self.vocab_id).get('download')
        )

    def get_resource_rdf(self, uri):
        sparql = SPARQLWrapper(self.VOCAB_ENDPOINTS.get(self.vocab_id).get('sparql'))
        sparql.setQuery('''DESCRIBE <{}>'''.format(uri))
        sparql.setReturnFormat(TURTLE)

        return sparql.query().convert()

    def get_collection(self, uri):
        sparql = SPARQLWrapper(self.VOCAB_ENDPOINTS.get(self.vocab_id).get('sparql'))
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
            vocab,
            uri,
            metadata[0]['l']['value'],
            metadata[0].get('c').get('value') if metadata[0].get('c') is not None else None,
            [(x.get('m').get('value'), x.get('m').get('value')) for x in members]
        )

    def get_concept(self, uri):
        sparql = SPARQLWrapper(self.VOCAB_ENDPOINTS.get(self.vocab_id).get('sparql'))
        q = '''PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT *
            WHERE {{
              <{}> skos:prefLabel ?pl .
              OPTIONAL {{?s skos:definition ?d }}
            }}'''.format(uri)
        sparql.setQuery(q)
        sparql.setReturnFormat(JSON)
        metadata = sparql.query().convert()['results']['bindings']

        # get the concept's altLabels
        q = '''PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT *
            WHERE {{
              <{}> skos:altLabel ?al .
            }}'''.format(uri)
        sparql.setQuery(q)
        sparql.setReturnFormat(JSON)
        altLabels = sparql.query().convert()['results']['bindings']

        # get the concept's hiddenLabels
        q = '''PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT *
            WHERE {{
              <{}> skos:hiddenLabel ?hl .
              ?hl skos:prefLabel ?pl .
            }}'''.format(uri)
        sparql.setQuery(q)
        sparql.setReturnFormat(JSON)
        hiddenLabels = sparql.query().convert()['results']['bindings']

        # get the concept's broaders
        q = ''' PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT *
            WHERE {{
              <{}> skos:broader ?b .
              ?b skos:prefLabel ?pl .
            }}'''.format(uri)
        sparql.setQuery(q)
        sparql.setReturnFormat(JSON)
        broaders = sparql.query().convert()['results']['bindings']

        # get the concept's narrowers
        q = '''PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT *
            WHERE {{
              <{}> skos:narrower ?n .
              ?n skos:prefLabel ?pl .
            }}'''.format(uri)
        sparql.setQuery(q)
        sparql.setReturnFormat(JSON)
        narrowers = sparql.query().convert()['results']['bindings']

        from model.concept import Concept
        return Concept(
            self.vocab_id,
            uri,
            metadata[0]['pl']['value'],
            metadata[0].get('d').get('value') if metadata[0].get('d') is not None else None,
            [x.get('al').get('value') for x in altLabels],
            [x.get('hl').get('value') for x in hiddenLabels],
            metadata[0].get('sc').get('value') if metadata[0].get('sc') is not None else None,
            metadata[0].get('cn').get('value') if metadata[0].get('cn') is not None else None,
            [{'uri': x.get('b').get('value'), 'prefLabel': x.get('pl').get('value')} for x in broaders],
            [{'uri': x.get('n').get('value'), 'prefLabel': x.get('pl').get('value')} for x in narrowers],
            None  # TODO: replace Sem Properties sub
        )

    def get_concept_hierarchy(self):
        pass

    def get_object_class(self, uri):
        sparql = SPARQLWrapper(self.VOCAB_ENDPOINTS.get(self.vocab_id).get('sparql'))
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


if __name__ == '__main__':
    #RVA().get_vocabulary('rva-177')

    print(
        RVA().get_object_class('rva-177', 'http://registry.it.csiro.au/def/isotc211/DS_AssociationTypeCode/stereoMate')
    )
