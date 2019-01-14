from data.source import Source
from os.path import dirname, realpath, join, abspath
import _config as config
from rdflib import Graph, URIRef, RDF
from rdflib.namespace import SKOS, DCTERMS, DC
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
        # q = '''PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        #     SELECT *
        #     WHERE {
        #       ?c a skos:Concept .
        #       ?c skos:prefLabel ?pl .
        #     }'''
        # return [(x['c'], x['pl']) for x in self.g.query(q)]

        vocabs = []
        for s, p, o in self.g.triples((None, SKOS.inScheme, None)):
            label = ' '.join(str(s).split('#')[-1].split('/')[-1].split('_'))
            vocabs.append((str(s), label))

        return vocabs

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
            self.uri = r['s']
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
        v.conceptHierarchy = self.get_concept_hierarchy()
        return v

    def get_collection(self, uri):
        pass

    def get_concept(self, uri):
        g = Graph().parse(uri + '.ttl', format='turtle')

        # -- altLabels
        altLabels = []
        for s, p, o in g.triples((URIRef(uri), SKOS.altLabel, None)):
            if o:
                altLabels.append(str(o))
        altLabels.sort()

        # -- broaders
        broaders = []
        for s, p, o in g.triples((URIRef(uri), SKOS.broader, None)):
            if o:
                label = ' '.join(str(o).split('#')[-1].split('/')[-1].split('_'))
                broaders.append(
                    {
                        'uri': o,
                        'prefLabel': label
                    }
                )
        broaders.sort(key= lambda x: x['prefLabel'])

        # -- contributor
        contributor = None
        for s, p, o in g.triples((URIRef(uri), DCTERMS.contributor, None)):
            if o:
                contributor = str(o)
        if not contributor: # if we didn't find a dct:contributor, look for a dc:contributor
            for s, p, o in g.triples((URIRef(uri), DC.contributor, None)):
                if o:
                    contributor = str(o)

       # -- definition
        definition = None
        for s, p, o in g.triples((URIRef(uri), SKOS.definition, None)):
            if o:
                definition = str(o)

        # -- hiddenLabels
        hiddenLabels = []
        for s, p, o in g.triples((URIRef(uri), SKOS.hiddenLabel, None)):
            if o:
                hiddenLabels.append(str(o))
        hiddenLabels.sort()

        # -- narrowers
        narrowers = []
        for s, p, o in g.triples((URIRef(uri), SKOS.narrower, None)):
            if o:
                label = ' '.join(str(o).split('#')[-1].split('/')[-1].split('_'))
                narrowers.append(
                    {
                        'uri': o,
                        'prefLabel': label
                    }
                )
        narrowers.sort(key=lambda x:  x['prefLabel'])

        # -- prefLabel
        prefLabel = None
        for s, p, o in g.triples((URIRef(uri), SKOS.prefLabel, None)):
            if o:
                prefLabel = str(o)
                break

        # -- semantic_properties TODO: Not sure what to do here
        semantic_properties = None

        # # -- source
        # source = None
        # for s, p, o in g.triples((URIRef(uri), DCTERMS.source, None)):
        #     if o:
        #         source = str(o)
        #         break

        # get the concept's source
        q = g.query('''PREFIX dct: <http://purl.org/dc/terms/>
                            SELECT *
                            WHERE {
                              ?a dct:source ?source .
                            }''')
        source = None
        for row in q:
            source = row['source']
            break

        from model.concept import Concept
        return Concept(
            self.vocab_id,
            uri,
            prefLabel,
            definition,
            altLabels,
            hiddenLabels,
            source,
            contributor,
            broaders,
            narrowers,
            semantic_properties
        )

    def get_concept_hierarchy(self):
        # get TopConcept
        topConcept = None
        for s, p, o in self.g.triples((URIRef(self.uri), SKOS.hasTopConcept, None)):
            topConcept = str(o)
            break

        hierarchy = []
        if topConcept:
            hierarchy.append((1, topConcept, FILE.get_prefLabel_from_uri(topConcept)))
            hierarchy += FILE.get_narrowers(topConcept, 1)
            return hierarchy
        else:
            raise Exception(f'topConcept not found')

    @staticmethod
    def get_prefLabel_from_uri(uri):
        return ' '.join(str(uri).split('#')[-1].split('/')[-1].split('_'))

    @staticmethod
    def get_narrowers(uri, depth):
        """
        Recursively get all skos:narrower properties as a list.

        :param uri: URI node
        :param depth: The current depth
        :return: list of tuples(tree_depth, uri, prefLabel)
        :rtype: list
        """
        depth += 1
        g = Graph().parse(uri + '.ttl', format='turtle')
        items = []
        for s, p, o in g.triples((None, SKOS.broader, URIRef(uri))):
            items.append((depth, str(s), FILE.get_prefLabel_from_uri(s)))
        items.sort(key=lambda x: x[2])
        count = 0
        for item in items:
            count += 1
            new_items = FILE.get_narrowers(item[1], item[0])
            items = items[:count] + new_items + items[count:]
            count += len(new_items)
        return items

    def get_object_class(self, uri):
        g = Graph()
        g.parse(uri + '.ttl', format='turtle')
        for s, p, o in g.triples((URIRef(uri), RDF.type, SKOS.Concept)):
            if o:
                return str(o)