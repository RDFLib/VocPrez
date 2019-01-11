from data.source import Source
from os.path import dirname, realpath, join, abspath
import _config as config
from rdflib import Graph
from rdflib.namespace import SKOS
import os
import pickle

class PickleLoadException(Exception):
    pass

class FILE(Source):

    # file extensions mapped to rdflib-supported formats
    # see supported rdflib formats at https://rdflib.readthedocs.io/en/stable/plugin_parsers.html?highlight=format
    MAPPER = {
        'ttl': 'turtle',
        'rdf': 'xml'
    }

    def __init__(self, vocab_id):
        super().__init__(vocab_id)
        self.g = FILE.load_pickle(vocab_id)


    @staticmethod
    def load_pickle(vocab_id):
        try:
            with open(join(config.APP_DIR, 'vocab_files', vocab_id + '.p'), 'rb') as f:
                g = pickle.load(f)
                return g
        except Exception as e:
            raise Exception(e)

    @staticmethod
    def init():
        # find all files in project_directory/vocab_files
        for path, subdirs, files in os.walk(join(config.APP_DIR, 'vocab_files')):
            for name in files:
                if name.split('.')[-1] in FILE.MAPPER:
                    # load file
                    file_path = os.path.join(path, name)
                    file_format = FILE.MAPPER[name.split('.')[-1]]
                    # load graph
                    g = Graph().parse(file_path, format=file_format)
                    file_name = name.split('.')[0]
                    # pickle to directory/vocab_files/
                    with open(join(path, file_name + '.p'), 'wb') as f:
                        pickle.dump(g, f)

    @classmethod
    def list_vocabularies(self):
        # TODO: extract id (URI) & title from each file in data/
        # def load_graph(graph_file):
        #     # just return None if there's no file
        #     try:
        #         g = pickle.load(open(path.join(config.APP_DIR, graph_file), 'rb'))
        #         return g
        #     except IOError:
        #
        # return None

        # TODO: Move this to list_concepts() method
        # list concepts
        vocabs = {}
        # for v in config.VOCABS:
        #     if config.VOCABS[v]['source'] == config.VocabSource.FILE:
        #         g = FILE.load_pickle(v)
        #         for s, p, o in g.triples((None, SKOS.inScheme, None)):
        #             if s not in vocabs:
        #                 vocabs[str(s)] = {
        #                     'source': config.VocabSource.RVA,
        #                     'title': ' '.join(str(s).split('#')[-1].split('/')[-1].split('_')).title()
        #                 }

        return vocabs

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
        # v.hasTopConcepts = [(x['tc'], x['pl']) for x in self.g.query(q2)] # this doesn't work
        for s, p, o in self.g.triples((v.uri, SKOS.hasTopConcept, None)):
            v.hasTopConcepts.append((str(o), ' '.join(str(o).split('#')[-1].split('/')[-1].split('_'))))

        # sort the top concepts by prefLabel
        v.hasTopConcepts.sort(key=lambda tup: tup[1])
        return v

    def get_collection(self, uri):
        pass

    def get_concept(self, uri):
        pass

    def get_concept_hierarchy(self, concept_scheme_uri):
        return NotImplementedError

    def get_object_class(self, uri):
        return NotImplementedError
