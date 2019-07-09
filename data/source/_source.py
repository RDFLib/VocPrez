import _config as config
import sys
from rdflib import Graph, URIRef
from rdflib.namespace import SKOS
import markdown
from flask import g
from SPARQLWrapper import SPARQLWrapper, JSON, BASIC
import dateutil
from model.concept import Concept

if hasattr(config, 'DEFAULT_LANGUAGE:'):
    DEFAULT_LANGUAGE = config.DEFAULT_LANGUAGE
else:
    DEFAULT_LANGUAGE = 'en'


class Source:
    VOC_TYPES = [
        'http://purl.org/vocommons/voaf#Vocabulary',
        'http://www.w3.org/2004/02/skos/core#ConceptScheme',
        'http://www.w3.org/2004/02/skos/core#ConceptCollection',
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
        vocab = g.VOCABS[self.vocab_id]
        q = '''
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT *
            WHERE {{GRAPH ?g {{
                ?c a skos:Collection .
                {{?c (rdfs:label | skos:prefLabel) ?l .
                    FILTER(lang(?l) = "{language}" || lang(?l) = "") }}
            }} }}'''.format(language=DEFAULT_LANGUAGE)
        collections = Source.sparql_query(vocab.sparql_endpoint, q, vocab.sparql_username, vocab.sparql_password)

        return [(x.get('c').get('value'), x.get('l').get('value')) for x in collections]

    def list_concepts(self):
        vocab = g.VOCABS[self.vocab_id]
        q = '''
             PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
             PREFIX dct: <http://purl.org/dc/terms/>
             SELECT *
             WHERE {{GRAPH ?g {{
                 ?c skos:inScheme <{concept_scheme_uri}> . 
                 {{?c skos:prefLabel ?pl .
                    FILTER(lang(?pl) = "{language}" || lang(?pl) = "") }}
                 OPTIONAL {{ ?c skos:definition ?d .
                    FILTER(lang(?d) = "{language}" || lang(?d) = "") }}
                 OPTIONAL {{ ?c dct:created ?created . }}
                 OPTIONAL {{ ?c dct:modified ?modified . }}
             }} }}
             ORDER BY ?pl'''.format(concept_scheme_uri=vocab.concept_scheme_uri, 
                                    language=DEFAULT_LANGUAGE)
        concepts = Source.sparql_query(vocab.sparql_endpoint, q, vocab.sparql_username, vocab.sparql_password)

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
        vocab = g.VOCABS[self.vocab_id]

        vocab.hasTopConcept = self.get_top_concepts()
        vocab.concept_hierarchy = self.get_concept_hierarchy()
        return vocab

    def get_collection(self, uri):
        vocab = g.VOCABS[self.vocab_id]
        q = '''PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT *
            WHERE {{ GRAPH ?g {{
              {{ <{collection_uri}> (rdfs:label | skos:prefLabel) ?l .
                  FILTER(lang(?l) = "{language}" || lang(?l) = "") }}
              OPTIONAL {{?s rdfs:comment ?c .
                  FILTER(lang(?c) = "{language}" || lang(?c) = "") }}
            }} }}'''.format(collection_uri=uri, 
                            language=DEFAULT_LANGUAGE)
        metadata = Source.sparql_query(vocab.sparql_endpoint, q, vocab.sparql_username, vocab.sparql_password)

        # get the collection's members
        q = '''PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT *
            WHERE {{ GRAPH ?g {{
              <{}> skos:member ?m .
              {{ ?n skos:prefLabel ?pl .
                  FILTER(lang(?pl) = "{language}" || lang(?pl) = "") }}
            }} }}'''.format(collection_uri=uri, 
                            language=DEFAULT_LANGUAGE)
        members = Source.sparql_query(vocab.sparql_endpoint, q, vocab.sparql_username, vocab.sparql_password)

        from model.collection import Collection
        return Collection(
            self.vocab_id,
            uri,
            metadata[0]['l']['value'],
            metadata[0].get('c').get('value') if metadata[0].get('c') is not None else None,
            [(x.get('m').get('value'), x.get('m').get('value')) for x in members]
        )

    def get_concept(self):
        vocab = g.VOCABS[self.vocab_id]
        q = """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX dct: <http://purl.org/dc/terms/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX dc: <http://purl.org/dc/elements/1.1/>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT DISTINCT *
            WHERE  {{ GRAPH ?g {{
                <{concept_uri}> skos:prefLabel ?prefLabel . # ?s skos:prefLabel|dct:title|rdfs:label ?prefLabel .
                OPTIONAL {{ <{concept_uri}> skos:definition ?definition .
                    FILTER(lang(?definition) = "{language}" || lang(?definition) = "") }}
                OPTIONAL {{ <{concept_uri}> skos:altLabel ?altLabel .
                    FILTER(lang(?altLabel) = "{language}" || lang(?altLabel) = "") }}
                OPTIONAL {{ <{concept_uri}> skos:hiddenLabel ?hiddenLabel .
                    FILTER(lang(?hiddenLabel) = "{language}" || lang(?hiddenLabel) = "") }}
                OPTIONAL {{ <{concept_uri}> dct:source ?source }}
                    FILTER(lang(?source) = "{language}" || lang(?source) = "") }}
                OPTIONAL {{ <{concept_uri}> dct:contributor ?contributor }}
                    FILTER(lang(?contributor) = "{language}" || lang(?contributor) = "") }}
                OPTIONAL {{ <{concept_uri}> skos:broader ?broader }}
                OPTIONAL {{ <{concept_uri}> skos:narrower ?narrower }}
                OPTIONAL {{ <{concept_uri}> skos:exactMatch ?exactMatch }}
                OPTIONAL {{ <{concept_uri}> skos:closeMatch ?closeMatch }}
                OPTIONAL {{ <{concept_uri}> skos:broadMatch ?broadMatch }}
                OPTIONAL {{ <{concept_uri}> skos:narrowMatch ?narrowMatch }}
                OPTIONAL {{ <{concept_uri}> skos:relatedMatch ?relatedMatch }}
                OPTIONAL {{ <{concept_uri}> dct:created ?created }}
                OPTIONAL {{ <{concept_uri}> dct:modified ?modified }}
            }} }}""".format(concept_uri=self.request.values.get('uri'), 
                            language=DEFAULT_LANGUAGE)
        result = Source.sparql_query(vocab.sparql_endpoint, q, vocab.sparql_username, vocab.sparql_password)

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
            definition = row['definition']['value']

            if hasattr(row, 'altLabel'):
                if row['altLabel']['value'] is not None and row['altLabel']['value'] not in altLabels:
                    altLabels.append(row['altLabel']['value'])

            if hasattr(row, 'hiddenLabel'):
                if row['hiddenLabel']['value'] is not None and row['hiddenLabel']['value'] not in hiddenLabels:
                    hiddenLabels.append(row['hiddenLabel']['value'])

            if hasattr(row, 'source'):
                source = row['source']['value']

            if hasattr(row, 'contributor'):
                if row['contributor']['value'] is not None and row['contributor']['value'] not in contributors:
                    contributors.append(row['contributor']['value'])

            if hasattr(row, 'broader'):
                if row['broader']['value'] is not None and row['broader']['value'] not in broaders:
                    broaders.append(row['broader']['value'])

            if hasattr(row, 'narrower'):
                if row['narrower']['value'] is not None and row['narrower']['value'] not in narrowers:
                    narrowers.append(row['narrower']['value'])

            if hasattr(row, 'exactMatch'):
                if row['exactMatch']['value'] is not None and row['exactMatch']['value'] not in exactMatches:
                    exactMatches.append(row['exactMatch']['value'])

            if hasattr(row, 'closeMatch'):
                if row['closeMatch']['value'] is not None and row['closeMatch']['value'] not in closeMatches:
                    closeMatches.append(row['closeMatch']['value'])

            if hasattr(row, 'broadMatch'):
                if row['broadMatch']['value'] is not None and row['broadMatch']['value'] not in broadMatches:
                    broadMatches.append(row['broadMatch']['value'])

            if hasattr(row, 'narrowMatch'):
                if row['narrowMatch']['value'] is not None and row['narrowMatch']['value'] not in narrowMatches:
                    narrowMatches.append(row['narrowMatch']['value'])

            if hasattr(row, 'relatedMatch'):
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

        return Concept(
            self.vocab_id,
            vocab.uri,
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
        vocab = g.VOCABS[self.vocab_id]
        q = """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

            SELECT (COUNT(?mid) AS ?length) ?c ?pl ?parent
            WHERE {{GRAPH ?g {{   
                <{concept_scheme_uri}>    (skos:hasTopConcept | skos:narrower)*   ?mid .
                ?mid    (skos:hasTopConcept | skos:narrower)+   ?c .                      
                {{ ?c      skos:prefLabel                          ?pl .
                    FILTER(lang(?pl) = "{language}" || lang(?pl) = "") }}
                ?c		(skos:topConceptOf | skos:broader)		?parent .
            }} }}
            GROUP BY ?c ?pl ?parent
            ORDER BY ?length ?parent ?pl
            """.format(concept_scheme_uri=vocab.concept_scheme_uri, 
                       language=DEFAULT_LANGUAGE)
        cs = Source.sparql_query(vocab.sparql_endpoint, q, vocab.sparql_username, vocab.sparql_password)

        hierarchy = []
        previous_parent_uri = None
        last_index = 0

        # cache prefLabels and do not add duplicates. This prevents Concepts with sameAs properties appearing twice
        pl_cache = []
        if cs[0].get('parent') is not None:
            for c in cs:
                # insert all topConceptOf directly
                if str(c['parent']['value']) == vocab.uri:
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
        vocab = g.VOCABS[self.vocab_id]
        q = '''
            SELECT * 
            WHERE {{ GRAPH ?g {{
                <{uri}> a ?c .
            }} }}
            '''.format(uri=self.request.values.get('uri'))
        clses = Source.sparql_query(vocab.sparql_endpoint, q, vocab.sparql_username, vocab.sparql_password)

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
        vocab = g.VOCABS[self.vocab_id]
        q = '''
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT DISTINCT *
            WHERE {{ GRAPH ?g {{
              {{
                <{concept_scheme_uri}> skos:hasTopConcept ?tc .                
              }}
              UNION 
              {{
                ?tc skos:topConceptOf <{concept_scheme_uri}> .
              }}
              {{ ?tc skos:prefLabel ?pl .
                  FILTER(lang(?pl) = "{language}" || lang(?pl) = "") }}
            }} }}
            ORDER BY ?pl'''.format(concept_scheme_uri=vocab.concept_scheme_uri,
                                   language=DEFAULT_LANGUAGE)
        top_concepts = Source.sparql_query(vocab.sparql_endpoint, q, vocab.sparql_username, vocab.sparql_password)

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
                    WHERE {{ GRAPH ?g {{
                      ?tc skos:inScheme <{concept_scheme_uri}> .
                      {{ ?tc skos:prefLabel ?pl .
                          FILTER(lang(?pl) = "{language}" || lang(?pl) = "") }}
                    }} }}
                    ORDER BY ?pl'''.format(concept_scheme_uri=vocab.concept_scheme_uri,
                                           language=DEFAULT_LANGUAGE)
                top_concepts = Source.sparql_query(vocab.sparql_endpoint, q, vocab.sparql_username, vocab.sparql_password)
                for tc in top_concepts:
                    if tc.get('pl').get('value') not in pl_cache:  # only add if not already in cache
                        tcs.append((tc.get('tc').get('value'), tc.get('pl').get('value')))
                        pl_cache.append(tc.get('pl').get('value'))

            return tcs
        else:
            return None

    @staticmethod
    def sparql_query(endpoint, q, sparql_username=None, sparql_password=None):
        sparql = SPARQLWrapper(endpoint)
        sparql.setQuery(q)
        sparql.setReturnFormat(JSON)
        
        if sparql_username and sparql_password:            
            sparql.setHTTPAuth(BASIC)
            sparql.setCredentials(sparql_username, sparql_password)
            
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
