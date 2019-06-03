import _config as config
import sys
from rdflib import Graph, URIRef
from rdflib.namespace import SKOS
import markdown
from flask import g
from SPARQLWrapper import SPARQLWrapper, JSON, BASIC
import dateutil


class Source:
    VOC_TYPES = [
        'http://purl.org/vocommons/voaf#Vocabulary',
        'http://www.w3.org/2004/02/skos/core#ConceptScheme',
        'http://www.w3.org/2004/02/skos/core#Collection',
        'http://www.w3.org/2004/02/skos/core#Concept',
    ]

    def __init__(self, vocab_id, request):
        self.vocab_id = vocab_id
        self.request = request

    @staticmethod
    def collect(details):
        """
        Specialised Sources must implement a collect method to get all the vocabs of their sort, listed in
        _config/__init__.py, at startup
        """
        pass

    def list_collections(self):
        q = '''
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT *
            WHERE {
                ?c a skos:Collection .
                ?c (rdfs:label | skos:prefLabel) ?l .
            }'''
        collections = Source.sparql_query(g.VOCABS[self.vocab_id]['details']['sparql_endpoint'], q)

        return [(x.get('c').get('value'), x.get('l').get('value')) for x in collections]

    def list_concepts(self):
        q = '''
             PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
             PREFIX dct: <http://purl.org/dc/terms/>
             SELECT *
             WHERE {{
                 ?c skos:inScheme <{0}> . 
                 ?c skos:prefLabel ?pl .
                 OPTIONAL {{ ?c skos:definition ?d . }}
                 OPTIONAL {{ ?c dct:created ?created . }}
                 OPTIONAL {{ ?c dct:modified ?modified . }}
             }}
             ORDER BY ?pl'''.format(g.VOCABS[self.vocab_id].concept_scheme_uri)
        concepts = Source.sparql_query(g.VOCABS[self.vocab_id].sparql_endpoint, q)

        concept_items = []
        for concept in concepts:
            metadata = {
                'key': self.vocab_id,
                'uri': concept['c']['value'],
                'title': concept['pl']['value'],
                'definition': concept.get('d')['value'] if concept.get('d') else None,
                'created': dateutil.parser.parse(concept['created']['value']) if concept.get('created') else None,
                'modified': dateutil.parser.parse(concept['modified']['value']) if concept.get('modified') else None
            }

            concept_items.append(metadata)

        return concept_items

    def get_vocabulary(self):
        """
        Get a vocab from the cache
        :return:
        :rtype:
        """
        v = g.VOCABS[self.vocab_id]

        v.hasTopConcept = self.get_top_concepts()
        v.concept_hierarchy = self.get_concept_hierarchy()
        return g.VOCABS[self.vocab_id]

    def get_collection(self, uri):
        sparql = SPARQLWrapper(g.VOCABS.get(self.vocab_id).sparql_endpoint)
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
            self.vocab_id,
            uri,
            metadata[0]['l']['value'],
            metadata[0].get('c').get('value') if metadata[0].get('c') is not None else None,
            [(x.get('m').get('value'), x.get('m').get('value')) for x in members]
        )

    def get_concept(self):
        q = """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX dct: <http://purl.org/dc/terms/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX dc: <http://purl.org/dc/elements/1.1/>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT DISTINCT *
            WHERE  {{
                <{0}> skos:prefLabel ?prefLabel . # ?s skos:prefLabel|dct:title|rdfs:label ?prefLabel .
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
            }}""".format(self.request.values.get('uri'))
        result = Source.sparql_query(g.VOCABS[self.vocab_id].sparql_endpoint, q)

        prefLabel = None
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
            prefLabel = row['prefLabel']['value']

            if row.get('definition'):
                definition = row['definition']['value']

            if row.get('altLabel'):
                if row['altLabel']['value'] is not None and row['altLabel']['value'] not in altLabels:
                    altLabels.append(row['altLabel']['value'])

            if row.get('hiddenLabel'):
                if row['hiddenLabel']['value'] is not None and row['hiddenLabel']['value'] not in hiddenLabels:
                    hiddenLabels.append(row['hiddenLabel']['value'])

            if row.get('source'):
                source = row['source']['value']

            if row.get('contributor'):
                if row['contributor']['value'] is not None and row['contributor']['value'] not in contributors:
                    contributors.append(row['contributor']['value'])

            if row.get('broader'):
                if row['broader']['value'] is not None and row['broader']['value'] not in broaders:
                    broaders.append(row['broader']['value'])

            if row.get('narrower'):
                if row['narrower']['value'] is not None and row['narrower']['value'] not in narrowers:
                    narrowers.append(row['narrower']['value'])

            if row.get('exactMatch'):
                if row['exactMatch']['value'] is not None and row['exactMatch']['value'] not in exactMatches:
                    exactMatches.append(row['exactMatch']['value'])

            if row.get('closeMatch'):
                if row['closeMatch']['value'] is not None and row['closeMatch']['value'] not in closeMatches:
                    closeMatches.append(row['closeMatch']['value'])

            if row.get('broadMatch'):
                if row['broadMatch']['value'] is not None and row['broadMatch']['value'] not in broadMatches:
                    broadMatches.append(row['broadMatch']['value'])

            if row.get('narrowMatch'):
                if row['narrowMatch']['value'] is not None and row['narrowMatch']['value'] not in narrowMatches:
                    narrowMatches.append(row['narrowMatch']['value'])

            if row.get('relatedMatch'):
                if row['relatedMatch']['value'] is not None and row['relatedMatch']['value'] not in relatedMatches:
                    relatedMatches.append(row['relatedMatch']['value'])

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
            g.VOCABS[self.vocab_id].uri,
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
        q = """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

            SELECT (COUNT(?mid) AS ?length) ?c ?pl ?parent
            WHERE {{   
                <{}>    (skos:hasTopConcept | skos:narrower)*   ?mid .
                ?mid    (skos:hasTopConcept | skos:narrower)+   ?c .                      
                ?c      skos:prefLabel                          ?pl .
                ?c		(skos:topConceptOf | skos:broader)		?parent .
            }}
            GROUP BY ?c ?pl ?parent
            ORDER BY ?length ?parent ?pl
            """.format(g.VOCABS.get(self.vocab_id).concept_scheme_uri)
        cs = Source.sparql_query(g.VOCABS.get(self.vocab_id).sparql_endpoint, q)

        hierarchy = []
        previous_parent_uri = None
        last_index = 0

        # cache prefLabels and do not add duplicates. This prevents Concepts with sameAs properties appearing twice
        pl_cache = []
        if cs[0].get('parent') is not None:
            for c in cs:
                # insert all topConceptOf directly
                if str(c['parent']['value']) == g.VOCABS.get(self.vocab_id).uri:
                    if c['pl']['value'] not in pl_cache:  # only add if not already in cache
                        hierarchy.append((
                            int(c['length']['value']),
                            c['c']['value'],
                            c['pl']['value'],
                            None
                        ))
                        pl_cache.append(c['pl']['value'])
                else:
                    if c['pl']['value'] not in pl_cache:  # only add if not already in cache
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
                        pl_cache.append(c['pl']['value'])
            return Source.draw_concept_hierarchy(hierarchy, self.request, self.vocab_id)
        else:
            return ''  # empty HTML

    def get_object_class(self):
        q = '''
            SELECT * 
            WHERE {{
                <{}> a ?c .
            }}
            '''.format(self.request.values.get('uri'))
        clses = Source.sparql_query(g.VOCABS.get(self.vocab_id).sparql_endpoint, q)

        # look for classes we understand (SKOS)
        for cls in clses:
            if cls['c']['value'] in Source.VOC_TYPES:
                return cls['c']['value']

        return None

    @staticmethod
    def get_prefLabel_from_uri(uri):
        return ' '.join(str(uri).split('#')[-1].split('/')[-1].split('_'))

    @staticmethod
    def get_narrowers(uri, depth):
        """
        Recursively get all skos:narrower properties as a list.

        :param uri: URI node
        :param depth: The current depth
        :param g: The graph
        :return: list of tuples(tree_depth, uri, prefLabel)
        :rtype: list
        """
        depth += 1

        # Some RVA sources won't load on first try, so ..
        # if failed, try load again.
        g = None
        max_attempts = 10
        for i in range(max_attempts):
            try:
                g = Graph().parse(uri + '.ttl', format='turtle')
                break
            except:
                print('Failed to load resource at URI {}. Attempt: {}.'.format(uri, i+1))
        if not g:
            raise Exception('Failed to load Graph from {}. Maximum attempts exceeded {}.'.format(uri, max_attempts))

        items = []
        for s, p, o in g.triples((None, SKOS.broader, URIRef(uri))):
            items.append((depth, str(s), Source.get_prefLabel_from_uri(s)))
        items.sort(key=lambda x: x[2])
        count = 0
        for item in items:
            count += 1
            new_items = Source.get_narrowers(item[1], item[0])
            items = items[:count] + new_items + items[count:]
            count += len(new_items)
        return items

    @staticmethod
    def draw_concept_hierarchy(hierarchy, request, id):
        tab = '\t'
        previous_length = 1

        text = ''
        tracked_items = []
        for item in hierarchy:
            mult = None

            if item[0] > previous_length + 2: # SPARQL query error on length value
                for tracked_item in tracked_items:
                    if tracked_item['name'] == item[3]:
                        mult = tracked_item['indent'] + 1

            if mult is None:
                found = False
                for tracked_item in tracked_items:
                    if tracked_item['name'] == item[3]:
                        found = True
                if not found:
                    mult = 0

            if mult is None: # else: # everything is normal
                mult = item[0] - 1

            import helper as h
            t = tab * mult + '* [' + item[2] + '](' + request.url_root + 'object?vocab_id=' + id + '&uri=' + h.url_encode(item[1]) + ')\n'
            text += t
            previous_length = mult
            tracked_items.append({'name': item[1], 'indent': mult})

        return markdown.markdown(text)

    def get_top_concepts(self):
        q = '''
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT DISTINCT *
            WHERE {{
              {{
                <{0}> skos:hasTopConcept ?tc .                
              }}
              UNION 
              {{
                ?tc skos:topConceptOf <{0}> .
              }}
              ?tc skos:prefLabel ?pl .
            }}
            ORDER BY ?pl'''.format(g.VOCABS.get(self.vocab_id).concept_scheme_uri)
        top_concepts = Source.sparql_query(g.VOCABS.get(self.vocab_id).sparql_endpoint, q)

        if top_concepts is not None:
            # cache prefLabels and do not add duplicates. This prevents Concepts with sameAs properties appearing twice
            pl_cache = []
            tcs = []
            for tc in top_concepts:
                if tc.get('pl').get('value') not in pl_cache:  # only add if not already in cache
                    tcs.append((tc.get('tc').get('value'), tc.get('pl').get('value')))
                    pl_cache.append(tc.get('pl').get('value'))

            if len(tcs) == 0:
                q = '''
                    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
                    SELECT DISTINCT *
                    WHERE {{
                      ?tc skos:inScheme <{0}> .
                      ?tc skos:prefLabel ?pl .
                    }}
                    ORDER BY ?pl'''.format(g.VOCABS.get(self.vocab_id).concept_scheme_uri)
                top_concepts = Source.sparql_query(g.VOCABS.get(self.vocab_id).sparql_endpoint, q)
                for tc in top_concepts:
                    if tc.get('pl').get('value') not in pl_cache:  # only add if not already in cache
                        tcs.append((tc.get('tc').get('value'), tc.get('pl').get('value')))
                        pl_cache.append(tc.get('pl').get('value'))

            return tcs
        else:
            return None

    @staticmethod
    def sparql_query(endpoint, q):
        sparql = SPARQLWrapper(endpoint)
        sparql.setQuery(q)
        sparql.setReturnFormat(JSON)
        try:
            metadata = sparql.query().convert()['results']['bindings']
        except:
            return None

        return metadata

    # @staticmethod
    # def sparql_query_in_memory_graph(vocab_id, q):
    #     # get the graph from the pickled file
    #     g = Graph()
    #     g = Source.load_pickle_graph(vocab_id)
    #
    #     # put the query to the graph
    #     for r in g.query(q):
    #
    #
    #
    # @staticmethod
    # def sparql_query_sparql_endpoint(vocab_id, q):
    #     pass
