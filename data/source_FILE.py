from data.source import Source
from os.path import dirname, realpath, join, abspath
import _config as config
from rdflib import Graph, URIRef, RDF
from rdflib.namespace import SKOS, DCTERMS, DC, OWL
import os
import pickle
from helper import APP_DIR, make_title


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
    def init():
        print('File init ...')
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
                    print('Pickling file: {}'.format(file_name))
                    with open(join(path, file_name + '.p'), 'wb') as f:
                        pickle.dump(g, f)
                        f.close()

        # Get register item metadata
        for vocab_id in config.VOCABS:
            if vocab_id in config.VOCABS:
                if config.VOCABS[vocab_id]['source'] != config.VocabSource.FILE:
                    continue
                
                # Creators
                creators = []
                g = FILE.load_pickle_graph(vocab_id)
                for uri in g.subjects(RDF.type, SKOS.ConceptScheme):
                    for creator in g.objects(uri, DCTERMS.creator):
                        creators.append(str(creator))
                    break
                config.VOCABS[vocab_id]['creators'] = creators

                # Date Created
                date_created = None
                # dct:created
                for uri in g.subjects(RDF.type, SKOS.ConceptScheme):
                    for date in g.objects(uri, DCTERMS.created):
                        date_created = str(date)[:10]
                if not date_created:
                    # dct:date
                    for uri in g.subjects(RDF.type, SKOS.ConceptScheme):
                        for date in g.objects(uri, DCTERMS.date):
                            date_created = str(date)[:10]
                config.VOCABS[vocab_id]['date_created'] = date_created

                # Date Modified
                date_modified = None
                for uri in g.subjects(RDF.type, SKOS.ConceptScheme):
                    for date in g.objects(uri, DCTERMS.modified):
                        date_modified = str(date)[:10]
                config.VOCABS[vocab_id]['date_modified'] = date_modified

                # Version
                version = None
                for uri in g.subjects(RDF.type, SKOS.ConceptScheme):
                    for versionInfo in g.objects(uri, OWL.versionInfo):
                        version = versionInfo
                config.VOCABS[vocab_id]['version'] = version


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
        # for s, p, o in self.g.triples((None, SKOS.inScheme, None)):
        #     label = ' '.join(str(s).split('#')[-1].split('/')[-1].split('_'))
        #     vocabs.append({
        #         'uri': str(s),
        #         'title': label
        #     })
        result = self.g.query("""
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX dct: <http://purl.org/dc/terms/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT * 
            WHERE {{
                {{
                    ?s a skos:Concept .
                    ?s skos:prefLabel ?title .                    
                }}
                UNION
                {{
                    ?s a skos:Concept .
                    ?s dct:title ?title . 
                    MINUS { ?s skos:prefLabel ?prefLabel }
                }}
                UNION
                {{
                    ?s a skos:Concept .
                    ?s rdfs:label ?title . 
                    MINUS { ?s skos:prefLabel ?prefLabel }
                    MINUS { ?s dct:title ?prefLabel }
                }}
                OPTIONAL {{
                    ?s dct:created ?date_created .
                }}
                OPTIONAL {{
                    ?s dct:modified ?date_modified .
                }}
            }}
            """)

        for row in result:
            vocabs.append({
                'vocab_id': self.vocab_id,
                'uri': str(row['s']),
                'title': row['title'] if row['title'] is not None else ' '.join(str(row['s']).split('#')[-1].split('/')[-1].split('_')),
                'date_created': row['date_created'][:10] if row['date_created'] is not None else None,
                'date_modified': row['date_modified'][:10] if row['date_modified'] is not None else None,
            })

        return vocabs

    def get_vocabulary(self):
        from model.vocabulary import Vocabulary

        result = self.g.query('''PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX dct: <http://purl.org/dc/terms/>
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT DISTINCT ?s ?title ?description ?creator ?created ?modified ?version ?hasTopConcept ?topConceptLabel
            WHERE {{
                {{
                    ?s a skos:ConceptScheme .
                    ?s skos:prefLabel ?title .                    
                }}
                UNION
                {{
                    ?s a skos:ConceptScheme .
                    ?s dct:title ?title . 
                    MINUS {{ ?s skos:prefLabel ?prefLabel }}
                }}
                UNION
                {{
                    ?s a skos:ConceptScheme .
                    ?s rdfs:label ?title . 
                    MINUS {{ ?s skos:prefLabel ?prefLabel }}
                    MINUS {{ ?s dct:title ?prefLabel }}
                }}
                OPTIONAL {{ ?s dct:description ?description }}
                OPTIONAL {{ ?s dct:creator ?creator }}
                OPTIONAL {{ ?s dct:created ?created }}
                OPTIONAL {{ ?s dct:modified ?modified }}
                OPTIONAL {{ ?s owl:versionInfo ?version }}
                OPTIONAL {{ 
                    ?s skos:hasTopConcept ?hasTopConcept .
                    ?hasTopConcept skos:prefLabel ?topConceptLabel .
              }}
            }}''')

        # from helper import APP_DIR
        # print('writing to disk ' + self.vocab_id)
        # self.g.serialize(os.path.join(APP_DIR, 'vocab_files', self.vocab_id + '.ttl'), format='turtle')

        title = None
        description = None
        creator = None
        created = None
        modified = None
        version = None

        topConcepts = []

        for r in result:
            self.uri = str(r['s'])
            if title is None:
                title = r['title']
            if description is None:
                description = r['description']
            if creator is None:
                creator = r['creator']
            if created is None:
                created = r['created']
            if modified is None:
                modified = r['modified']
            if version is None:
                version = r['version']
            if r['hasTopConcept'] and r['topConceptLabel'] is not None:
                topConcepts.append((r['hasTopConcept'], r['topConceptLabel']))

        v = Vocabulary(
            self.vocab_id,
            self.uri,
            title,
            description,
            creator,
            created,
            modified,
            version,
            topConcepts
        )

        # sort the top concepts by prefLabel
        v.hasTopConcepts = topConcepts
        if v.hasTopConcepts:
            v.hasTopConcepts.sort(key=lambda tup: tup[1])
        v.conceptHierarchy = self.get_concept_hierarchy()
        return v

    def get_collection(self, uri):
        pass

    def get_concept(self, uri):
        if config.VOCABS[self.vocab_id].get('turtle'):
            g = Graph().parse(config.VOCABS[self.vocab_id]['turtle'])
        else:
            g = Graph().parse(os.path.join(APP_DIR, 'vocab_files', self.vocab_id + '.ttl'), format='turtle')

        query = """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX dct: <http://purl.org/dc/terms/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX dc: <http://purl.org/dc/elements/1.1/>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT DISTINCT ?s ?prefLabel ?definition ?altLabel ?hiddenLabel ?source ?contributor ?broader ?narrower ?exactMatch ?closeMatch ?broadMatch ?narrowMatch ?relatedMatch ?created ?modified
            WHERE 
            {{
                {{
                    <{0}> a skos:Concept .
                    <{0}> skos:prefLabel ?prefLabel .
                }} UNION {{
                    <{0}> a skos:Concept .
                    <{0}> dct:title ?prefLabel .
                    MINUS {{ <{0}> skos:prefLabel ?pl }}
                }} UNION {{
                    <{0}> a skos:Concept .
                    <{0}> rdfs:label ?prefLabel .
                    MINUS {{ <{0}> skos:prefLabel ?pl }}
                    MINUS {{ <{0}> dct:title ?pl }}
                }}
                
            }} LIMIT 1
            """.format(uri)
        result = g.query(query)

        prefLabel = None
        for row in result:
            prefLabel = row['prefLabel']
        if prefLabel is None:
            prefLabel = make_title(uri)
        print('prefLabel: {}'.format(prefLabel))

        # TODO: Get the prefLabels of the concept's narrowers, broaders, etc. Currently we are just making the
        #       label from the URI in the jinja template.
        query = """PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX dct: <http://purl.org/dc/terms/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX dc: <http://purl.org/dc/elements/1.1/>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT DISTINCT ?s ?prefLabel ?definition ?altLabel ?hiddenLabel ?source ?contributor ?broader ?narrower ?exactMatch ?closeMatch ?broadMatch ?narrowMatch ?relatedMatch ?created ?modified
            WHERE  {{
                    
                    <{0}> a skos:Concept .
                    OPTIONAL {{ <{0}> skos:definition ?definition }}
                    OPTIONAL {{ <{0}> skos:altLabel ?altLabel }}
                    OPTIONAL {{ <{0}> skos:hiddenLabel ?hiddenLabel }}
                    OPTIONAL {{ <{0}> dct:source ?source }}
                    OPTIONAL {{ <{0}> dct:contributor ?contributor }}
                    OPTIONAL {{ <{0}> skos:broader ?broader }}
                    OPTIONAL {{ <{0}> skos:narrower ?narrower }}
                    OPTIONAL {{ <{0}> skos:exactMatch ?exactMatch }}
                    OPTIONAL {{ <{0}> skos:closeMatch ?closeMatch }}
                    OPTIONAL {{ <{0}> skos:broadMatch ?broadMatch }}
                    OPTIONAL {{ <{0}> skos:narrowMatch ?narrowMatch }}
                    OPTIONAL {{ <{0}> skos:relatedMatch ?relatedMatch }}
                    OPTIONAL {{ <{0}> dct:created ?created }}
                    OPTIONAL {{ <{0}> dct:modified ?modified }}
            }}""".format(uri)
        result = g.query(query)

        definition = None
        altLabels = []
        hiddenLabels = []
        source = None
        contributors = []
        broaders = []
        narrowers = []
        exactMatches = []
        closeMatches = []
        broadMatches = []
        narrowMatches = []
        relatedMatches = []
        for row in result:
            if prefLabel is None:
                prefLabel = row['prefLabel']

            if definition is None:
                definition = row['definition']

            if row['altLabel'] is not None and row['altLabel'] not in altLabels:
                altLabels.append(row['altLabel'])

            if row['hiddenLabel'] is not None and row['hiddenLabel'] not in hiddenLabels:
                hiddenLabels.append(row['hiddenLabel'])

            if source is None:
                source = row['source']

            if row['contributor'] is not None and row['contributor'] not in contributors:
                contributors.append(row['contributor'])

            if row['broader'] is not None and row['broader'] not in broaders:
                broaders.append(row['broader'])

            if row['narrower'] is not None and row['narrower'] not in narrowers:
                narrowers.append(row['narrower'])

            if row['exactMatch'] is not None and row['exactMatch'] not in exactMatches:
                exactMatches.append(row['exactMatch'])

            if row['closeMatch'] is not None and row['closeMatch'] not in closeMatches:
                closeMatches.append(row['closeMatch'])

            if row['broadMatch'] is not None and row['broadMatch'] not in broadMatches:
                broadMatches.append(row['broadMatch'])

            if row['narrowMatch'] is not None and row['narrowMatch'] not in narrowMatches:
                narrowMatches.append(row['narrowMatch'])

            if row['relatedMatch'] is not None and row['relatedMatch'] not in relatedMatches:
                relatedMatches.append(row['relatedMatch'])

        altLabels.sort()
        hiddenLabels.sort()
        contributors.sort()
        broaders.sort()
        narrowers.sort()
        exactMatches.sort()
        closeMatches.sort()
        broadMatches.sort()
        narrowMatches.sort()
        relatedMatches.sort()


        from model.concept import Concept
        return Concept(
            self.vocab_id,
            uri,
            prefLabel,
            definition,
            altLabels,
            hiddenLabels,
            source,
            contributors,
            broaders,
            narrowers,
            exactMatches,
            closeMatches,
            broadMatches,
            narrowMatches,
            relatedMatches,
            None,
            None,
            None,
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
        if config.VOCABS[self.vocab_id].get('turtle'):
            g = Graph().parse(config.VOCABS[self.vocab_id]['turtle'], format='turtle')
        else:
            g = Graph().parse(os.path.join(APP_DIR, 'vocab_files', self.vocab_id + '.ttl'), format='turtle')
        for s, p, o in g.triples((URIRef(uri), RDF.type, SKOS.Concept)):
                return str(o)