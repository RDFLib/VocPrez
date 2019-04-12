import logging
import dateutil.parser
from data.source._source import Source
import requests
import _config as config
from rdflib import Graph, URIRef, RDF
from rdflib.namespace import SKOS
import os
import json
from helper import APP_DIR, make_title
from flask import g
from SPARQLWrapper import SPARQLWrapper, JSON


class PickleLoadException(Exception):
    pass


class SPARQL(Source):
    hierarchy = {}

    def __init__(self, vocab_id, request):
        super().__init__(vocab_id, request)

    @staticmethod
    def collect(details):
        logging.debug('SPARQL collect()...')
        # Treat each skos:ConceptScheme discoverable at this endpoint as a vocab
        #
        # get all the ConceptSchemes from the SPARQL endpoint
        # interpret a CS as a Vocab
        q = '''
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX dcterms: <http://purl.org/dc/terms/>
            SELECT * WHERE {
                GRAPH ?g {
                    ?cs a skos:ConceptScheme .
                    OPTIONAL { ?cs skos:prefLabel ?title }
                    OPTIONAL { ?cs dcterms:created ?created }
                    OPTIONAL { ?cs dcterms:issued ?issued }
                    OPTIONAL { ?cs dcterms:modified ?modified }
                    OPTIONAL { ?cs skos:definition ?description }
                }
            } 
            ORDER BY ?l
        '''
        # record just the IDs & title for the VocPrez in-memory vocabs list
        concept_schemes = SPARQL.sparql_query(details['endpoint'], q)
        sparql_vocabs = {}
        for cs in concept_schemes:
            # handling CS URIs that end with '/'
            vocab_id = cs['cs']['value'].replace('/conceptScheme', '').split('/')[-1]
            if len(vocab_id) < 2:
                vocab_id = cs['cs']['value'].split('/')[-2]

            sparql_vocabs[vocab_id] = {
                'uri': cs['cs']['value'],
                'source': config.VocabSource.SPARQL,
                'title': cs.get('title').get('value') if cs.get('title') is not None else None,
                'date_created': dateutil.parser.parse(cs.get('created').get('value')) if cs.get('created') is not None else None,
                'date_issued': dateutil.parser.parse(cs.get('issued').get('value')) if cs.get('issued') is not None else None,
                'date_modified': dateutil.parser.parse(cs.get('modified').get('value')) if cs.get('modified') is not None else None,
                'description': cs.get('description').get('value') if cs.get('description') is not None else None,
                'sparql_endpoint': details['endpoint']
                # version
                # creators
            }
        g.VOCABS = {**g.VOCABS, **sparql_vocabs}
        logging.debug('SPARQL collect() complete.')

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

        # get the vocab's top concepts
        sparql = SPARQLWrapper(g.VOCABS.get(self.vocab_id).get('sparql_endpoint'))
        sparql.setQuery('''
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT *
            WHERE {{
              <{}> skos:hasTopConcept ?tc .
              ?tc skos:prefLabel ?pl .
            }}'''.format(g.VOCABS.get(self.vocab_id).get('uri')))
        sparql.setReturnFormat(JSON)
        top_concepts = sparql.query().convert()['results']['bindings']

        return Vocabulary(
            self.vocab_id,
            g.VOCABS[self.vocab_id]['uri'],
            g.VOCABS[self.vocab_id]['title'],
            g.VOCABS[self.vocab_id].get('description'),
            None,  # we don't yet have creator info stored for GSQ vocabs
            g.VOCABS[self.vocab_id].get('date_created'),
            g.VOCABS[self.vocab_id].get('date_modified'),
            g.VOCABS[self.vocab_id].get('version'),
            hasTopConcepts=[(x.get('tc').get('value'), x.get('pl').get('value')) for x in top_concepts],
            conceptHierarchy=self.get_concept_hierarchy()
        )

    def get_concept_hierarchy(self):
        sparql = SPARQLWrapper(g.VOCABS.get(self.vocab_id).get('sparql_endpoint'))
        sparql.setQuery(
            """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

            SELECT (COUNT(?mid) AS ?length) ?c ?pl ?parent
            WHERE {{ 
                ?c      a                                       skos:Concept .   
                <{}>    (skos:hasTopConcept | skos:narrower)*   ?mid .
                ?mid    (skos:hasTopConcept | skos:narrower)+   ?c .                      
                ?c      skos:prefLabel                          ?pl .
                ?c		(skos:topConceptOf | skos:broader)		?parent .
            }}
            GROUP BY ?c ?pl ?parent
            ORDER BY ?length ?parent ?pl
            """.format(g.VOCABS.get(self.vocab_id).get('uri'))
        )
        sparql.setReturnFormat(JSON)
        cs = sparql.query().convert()['results']['bindings']

        hierarchy = []
        previous_parent_uri = None
        last_index = 0

        for c in cs:
            # insert all topConceptOf directly
            if str(c['parent']['value']) == g.VOCABS.get(self.vocab_id).get('uri'):
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

    def get_collection(self, uri):
        pass

    def get_concept(self, uri):
        if g.VOCABS[self.vocab_id].get('turtle'):
            g = Graph().parse(g.VOCABS[self.vocab_id]['turtle'])
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

    @staticmethod
    def build_concept_hierarchy(vocab_id):
        g = SPARQL.load_pickle_graph(vocab_id)

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
        if g.VOCABS[self.vocab_id].get('turtle'):
            g = Graph().parse(g.VOCABS[self.vocab_id]['turtle'], format='turtle')
        else:
            g = Graph().parse(os.path.join(APP_DIR, 'vocab_files', self.vocab_id + '.ttl'), format='turtle')
        for s, p, o in g.triples((URIRef(uri), RDF.type, SKOS.Concept)):
                return str(o)

    @staticmethod
    def sparql_query(endpoint, q):
        r = requests.get(
            endpoint,
            params={'query': q},
            headers={'Accept': 'application/sparql-results+json'}
        )

        if r.status_code != 200:
            return ConnectionError('The query {} did not return a result from endpoint {}'.format(q, endpoint))
        else:
            return json.loads(r.content.decode('utf-8'))['results']['bindings']
