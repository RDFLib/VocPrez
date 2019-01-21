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
    hierarchy = {}

    # file extensions mapped to rdflib-supported formats
    # see supported rdflib formats at https://rdflib.readthedocs.io/en/stable/plugin_parsers.html?highlight=format
    MAPPER = {
        'ttl': 'turtle',
        'rdf': 'xml'
    }

    def __init__(self, vocab_id, request):
        super().__init__(vocab_id, request)
        self.g = FILE.load_pickle_graph(vocab_id)


    @staticmethod
    def load_pickle_graph(vocab_id):
        try:
            with open(join(config.APP_DIR, 'vocab_files', vocab_id + '.p'), 'rb') as f:
                g = pickle.load(f)
                return g
        except Exception as e:
            raise Exception(e)

    @staticmethod
    def init():
        print('Finding vocabulary files ...')
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

        # print('Building concept hierarchy for source type FILE ...')
        # # build conceptHierarchy
        # for item in config.VOCABS:
        #     if config.VOCABS[item]['source'] == config.VocabSource.FILE:
        #         FILE.hierarchy[item] = FILE.build_concept_hierarchy(item)

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
            self.uri = str(r['s'])
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

        # top concepts
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
            altLabels.append(str(o))
        altLabels.sort()

        # -- broaders
        broaders = []
        for s, p, o in g.triples((URIRef(uri), SKOS.broader, None)):
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
            contributor = str(o)
        if not contributor: # if we didn't find a dct:contributor, look for a dc:contributor
            for s, p, o in g.triples((URIRef(uri), DC.contributor, None)):
                contributor = str(o)

       # -- definition
        definition = None
        for s, p, o in g.triples((URIRef(uri), SKOS.definition, None)):
            definition = str(o)

        # -- hiddenLabels
        hiddenLabels = []
        for s, p, o in g.triples((URIRef(uri), SKOS.hiddenLabel, None)):
            hiddenLabels.append(str(o))
        hiddenLabels.sort()

        # -- narrowers
        narrowers = []
        for s, p, o in g.triples((URIRef(uri), SKOS.narrower, None)):
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
        # return FILE.hierarchy[self.vocab_id]
        pass
        g = FILE.load_pickle_graph(self.vocab_id)
        result = g.query(
            """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

            SELECT (COUNT(?mid) AS ?length) ?c ?pl ?parent
            WHERE {{ 
                ?c      a                                       skos:Concept .   
                ?cs     (skos:hasTopConcept | skos:narrower)*   ?mid .
                ?mid    (skos:hasTopConcept | skos:narrower)+   ?c .                      
                ?c      skos:prefLabel                          ?pl .
                ?c		(skos:topConceptOf | skos:broader)		?parent .
                FILTER (?cs = <{}>)
            }}
            GROUP BY ?c ?pl ?parent
            ORDER BY ?length ?parent ?pl
            """.format(self.uri)
        )

        cs = []
        for row in result:
            cs.append({
                'length': {'value': row['length']},
                'c': {'value': row['c']},
                'pl': {'value': row['pl']},
                'parent': {'value': row['parent']}
            })

        hierarchy = []
        previous_parent_uri = None
        last_index = 0

        for c in cs:
            # insert all topConceptOf directly
            if str(c['parent']['value']) == self.uri:
                hierarchy.append((
                    int(c['length']['value']),
                    c['c']['value'],
                    c['pl']['value'],
                    None
                ))
            else:
                # If this is not a topConcept, see if it has the same URI as the previous inserted Concept
                # If so, use that Concept's index + 1
                this_parent = c['parent']['value']
                if this_parent == previous_parent_uri:
                    # use last inserted index
                    hierarchy.insert(last_index + 1, (
                        int(c['length']['value']),
                        c['c']['value'],
                        c['pl']['value'],
                        c['parent']['value']
                    ))
                    last_index += 1
                # This is not a TopConcept and it has a differnt parent from the previous insert
                # So insert it after it's parent
                else:
                    i = 0
                    parent_index = 0
                    for t in hierarchy:
                        if this_parent in t[1]:
                            parent_index = i
                        i += 1

                    hierarchy.insert(parent_index + 1, (
                        int(c['length']['value']),
                        c['c']['value'],
                        c['pl']['value'],
                        c['parent']['value']
                    ))

                    last_index = parent_index + 1
                previous_parent_uri = this_parent
        return Source.draw_concept_hierarchy(hierarchy, self.request, self.vocab_id)

    @staticmethod
    def build_concept_hierarchy(vocab_id):
        g = FILE.load_pickle_graph(vocab_id)

        # get uri
        uri = None
        for s, p, o in g.triples((None, RDF.type, SKOS.ConceptScheme)):
            uri = str(s)

        # get TopConcept
        topConcepts = []
        for s, p, o in g.triples((URIRef(uri), SKOS.hasTopConcept, None)):
            topConcepts.append(str(o))

        hierarchy = []
        if topConcepts:
            topConcepts.sort()
            for tc in topConcepts:
                hierarchy.append((1, tc, Source.get_prefLabel_from_uri(tc)))
                hierarchy += Source.get_narrowers(tc, 1)
            return hierarchy
        else:
            raise Exception('topConcept not found')

    def get_object_class(self, uri):
        g = Graph().parse(uri + '.ttl', format='turtle')
        for s, p, o in g.triples((URIRef(uri), RDF.type, SKOS.Concept)):
            if o:
                return str(o)