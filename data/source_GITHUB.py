from data.source import Source
from os.path import dirname, realpath, join, abspath
import _config as config
from rdflib import Graph


# TODO: implement GITHUB source
class GITHUB(Source):
    def __init__(self, vocab_id):
        super().__init__(vocab_id)

    def _parse_vocab(self):
        self.g = Graph().parse(join(config.APP_DIR, 'data', self.vocab_id + '.ttl'), format='turtle')

    @classmethod
    def list_vocabularies(self):
        # iterate through all GitHub vocabs in some way
        # make this the list
        return NotImplementedError

    def list_collections(self):
        q = '''
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT *
            WHERE {
              ?c a skos:Concept .
              ?c rdfs:label ?l .
            }'''
        return [(x['c'], x['l']) for x in self.g.query(q)]

    def list_concepts(self):
        q = '''PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT *
            WHERE {
              ?c a skos:Concept .
              ?c skos:prefLabel ?pl .
            }'''
        return [(x['c'], x['pl']) for x in self.g.query(q)]

    def get_vocabulary(self):
        from model.vocabulary import Vocabulary

        q = '''PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
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
            }'''
        for r in self.g.query(q):
            v = Vocabulary(
                self.vocab_id,
                r['s'],
                r['t'],
                r['d'],
                r['c'],
                r['cr'],
                r['m'],
                r['v'],
                [],
                None,
                None
            )

        q2 = '''PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT *
            WHERE {
              ?s skos:hasTopConcept ?tc .
              ?tc skos:prefLabel ?pl .
            }'''
        # add the top concepts to the Vocabulary class instance
        v.hasTopConcepts = [(x['tc'], x['pl']) for x in self.g.query(q2)]
        # sort the top concepts by prefLabel
        v.hasTopConcepts.sort(key=lambda tup: tup[1])
        return v

    def get_collection(self, uri):
        return NotImplementedError

    def get_concept(self, uri):
        pass

    def get_concept_hierarchy(self, uri):
        return NotImplementedError

    def get_object_class(self, uri):
        return NotImplementedError