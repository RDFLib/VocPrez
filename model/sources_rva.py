from .source import Source
from SPARQLWrapper import SPARQLWrapper, JSON


class RVA(Source):
    """Source for Research Vocabularies Australia
    """
    SPARQL_ENDPOINTS = {
        'rva-50': 'http://vocabs.ands.org.au/repository/api/sparql/ga_geologic-unit-type_v0-1',
        'rva-52': 'http://vocabs.ands.org.au/repository/api/sparql/ga_contact-type_v0-1',
        'rva-57': 'http://vocabs.ands.org.au/repository/api/sparql/ga_stratigraphic-rank_v0-1',
        'rva-178': 'http://vocabs.ands.org.au/repository/api/sparql/ga_feature-of-interest-type_v0-1',
        'rva-185': 'http://vocabs.ands.org.au/repository/api/sparql/ga_sample-type_v1-0',
        'rva-186': 'http://vocabs.ands.org.au/repository/api/sparql/ga_ga-data-classification_v1-0'
    }

    def list_vocabularies(self):
        vocabs = [
            ('/vocabulary/rva-50', 'Geologic Unit Type'),
            ('/vocabulary/rva-52', 'Contact Type'),
            ('/vocabulary/rva-57', 'Stratigraphic Rank'),
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
        sparql = SPARQLWrapper(self.SPARQL_ENDPOINTS.get(vocab_id))
        sparql.setQuery('''PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
                           SELECT * 
                           WHERE {
                             ?s a skos:ConceptScheme .
                           }''')
        sparql.setReturnFormat(JSON)
        concept_scheme_uri = sparql.query().convert()['results']['bindings'][0]['s']['value']

        return ''

    def get_collection(self, collection_id):
        pass

    def get_concept(self, concept_id):
        pass

    def get_concept_hierarchy(self, concept_id):
        pass
