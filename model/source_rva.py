from model.source import Source
from SPARQLWrapper import SPARQLWrapper, JSON, TURTLE
import rdflib


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
            'download': 'https://vocabs.ands.org.au/registry/api/resource/downloads/741/ga_association-type_v1-2.ttl'
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

    def list_vocabularies(self):
        vocabs = [
            ('/vocabulary/rva-50', 'Geologic Unit Type'),
            ('/vocabulary/rva-52', 'Contact Type'),
            ('/vocabulary/rva-57', 'Stratigraphic Rank'),
            ('/vocabulary/rva-177', 'Association Type'),
            ('/vocabulary/rva-178', 'Feature of Interest Type'),
            ('/vocabulary/rva-185', 'Sample Type'),
            ('/vocabulary/rva-186', 'GA Data Classification')
        ]

        return sorted(vocabs, key=lambda tup: tup[1])

    def list_collections(self, vocab_id):
        pass

    def list_concepts(self, vocab_id):
        pass

    def get_vocabulary(self, vocab_id):
        print('get_vocabulary')
        sparql = SPARQLWrapper(self.VOCAB_ENDPOINTS.get(vocab_id).get('sparql'))

        # get the basic vocab metadata
        # PREFIX%20skos%3A%20%3Chttp%3A%2F%2Fwww.w3.org%2F2004%2F02%2Fskos%2Fcore%23%3E%0APREFIX%20dct%3A%20%3Chttp%3A%2F%2Fpurl.org%2Fdc%2Fterms%2F%3E%0APREFIX%20owl%3A%20%3Chttp%3A%2F%2Fwww.w3.org%2F2002%2F07%2Fowl%23%3E%0ASELECT%20*%0AWHERE%20%7B%0A%3Fs%20a%20skos%3AConceptScheme%20%3B%0Adct%3Atitle%20%3Ft%20%3B%0Adct%3Adescription%20%3Fd%20%3B%0Adct%3Acreator%20%3Fc%20%3B%0Adct%3Acreated%20%3Fcr%20%3B%0Adct%3Amodified%20%3Fm%20%3B%0Aowl%3AversionInfo%20%3Fv%20.%0A%7D
        sparql.setQuery('''PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX dct: <http://purl.org/dc/terms/>
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            SELECT *
            WHERE {
              ?s a skos:ConceptScheme ;
              dct:title ?t ;
              dct:description ?d .
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

        from model.vocabulary import Vocabulary
        v = Vocabulary(
            vocab_id,
            metadata['results']['bindings'][0]['s']['value'],
            metadata['results']['bindings'][0]['t']['value'],
            metadata['results']['bindings'][0]['d']['value'],
            metadata['results']['bindings'][0].get('c').get('value') if metadata['results']['bindings'][0].get('c') is not None else None,
            metadata['results']['bindings'][0].get('cr').get('value') if metadata['results']['bindings'][0].get('cr') is not None else None,
            metadata['results']['bindings'][0].get('m').get('value') if metadata['results']['bindings'][0].get('m') is not None else None,
            metadata['results']['bindings'][0].get('v').get('value') if metadata['results']['bindings'][0].get('v') is not None else None,
            [(x.get('tc').get('value'), x.get('pl').get('value')) for x in top_concepts],
            None,
            self.VOCAB_ENDPOINTS.get(vocab_id).get('download'),
        )
        return v

    def get_vocabulary_rdf(self, vocab_id, uri):
        sparql = SPARQLWrapper(self.VOCAB_ENDPOINTS.get(vocab_id).get('sparql'))
        sparql.setQuery('''DESCRIBE <{}>'''.format(uri))
        sparql.setReturnFormat(TURTLE)

        return sparql.query().convert()

    def get_collection(self, collection_id):
        pass

    def get_concept(self, concept_id):
        pass

    def get_concept_hierarchy(self, concept_id):
        pass


if __name__ == '__main__':
    RVA().get_vocabulary('rva-177')
