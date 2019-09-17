import _config as config
from rdflib import Graph, URIRef
from rdflib.namespace import SKOS
import markdown
from flask import g
from SPARQLWrapper import SPARQLWrapper, JSON, BASIC
import dateutil
from model.concept import Concept
from collections import OrderedDict
from helper import make_title, url_decode, cache_read, cache_write
import logging
import base64
import requests
from time import sleep
import helper as h

# Default to English if no DEFAULT_LANGUAGE in config
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

    def __init__(self, vocab_id, request, language=None):
        self.vocab_id = vocab_id
        self.request = request
        self.language = language or DEFAULT_LANGUAGE
        
        self._graph = None # Property for rdflib Graph object to be populated on demand

    @staticmethod
    def collect(details):
        """
        Specialised Sources must implement a collect method to get all the vocabs of their sort, listed in
        _config/__init__.py, at startup
        """
        pass

    def list_collections(self):
        vocab = g.VOCABS[self.vocab_id]
        q = '''PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT *
WHERE {{
    {{ GRAPH ?g {{
        ?c a skos:Collection .
        {{?c (rdfs:label | skos:prefLabel) ?l .
        FILTER(lang(?l) = "{language}" || lang(?l) = "") 
        }}
    }} }}
    UNION
    {{
        ?c a skos:Collection .
        {{?c (rdfs:label | skos:prefLabel) ?l .
        FILTER(lang(?l) = "{language}" || lang(?l) = "") 
        }}
    }} 
}}'''.format(language=self.language)
        collections = Source.sparql_query(vocab.sparql_endpoint, q, vocab.sparql_username, vocab.sparql_password)

        return [(x.get('c').get('value'), x.get('l').get('value')) for x in collections]

    def list_concepts(self):
        vocab = g.VOCABS[self.vocab_id]
        q = '''PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX dct: <http://purl.org/dc/terms/>
SELECT DISTINCT *
WHERE {{
    {{ GRAPH ?g {{
        ?c skos:inScheme <{concept_scheme_uri}> . 
        {{ ?c skos:prefLabel ?pl .
        FILTER(lang(?pl) = "{language}" || lang(?pl) = "") 
        }}
        OPTIONAL {{ ?c skos:definition ?d .
        FILTER(lang(?d) = "{language}" || lang(?d) = "") 
        }}
        OPTIONAL {{ ?c dct:created ?created . }}
        OPTIONAL {{ ?c dct:modified ?modified . }}
    }} }}
    UNION
    {{
        ?c skos:inScheme <{concept_scheme_uri}> . 
        {{ ?c skos:prefLabel ?pl .
        FILTER(lang(?pl) = "{language}" || lang(?pl) = "") 
        }}
        OPTIONAL {{ ?c skos:definition ?d .
        FILTER(lang(?d) = "{language}" || lang(?d) = "") 
        }}
        OPTIONAL {{ ?c dct:created ?created . }}
        OPTIONAL {{ ?c dct:modified ?modified . }}
    }}
}}
ORDER BY ?pl'''.format(concept_scheme_uri=vocab.concept_scheme_uri, 
                        language=self.language)
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
        vocab.source = self
        return vocab

    def get_collection(self, uri):
        vocab = g.VOCABS[self.vocab_id]
        q = '''PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT *
WHERE {{ 
    {{ GRAPH ?g {{
        {{ <{collection_uri}> (rdfs:label | skos:prefLabel) ?l .
        FILTER(lang(?l) = "{language}" || lang(?l) = "") }}
        OPTIONAL {{?s rdfs:comment ?c .
        FILTER(lang(?c) = "{language}" || lang(?c) = "") }}
    }} }}
    UNION
    {{
        {{ <{collection_uri}> (rdfs:label | skos:prefLabel) ?l .
        FILTER(lang(?l) = "{language}" || lang(?l) = "") }}
        OPTIONAL {{?s rdfs:comment ?c .
        FILTER(lang(?c) = "{language}" || lang(?c) = "") }}
    }}
}}'''.format(collection_uri=uri, 
                language=self.language)
        metadata = Source.sparql_query(vocab.sparql_endpoint, q, vocab.sparql_username, vocab.sparql_password)

        # get the collection's members
        q = '''PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT DISTINCT *
WHERE {{
    {{ GRAPH ?g {{
        <{}> skos:member ?m .
        {{ ?n skos:prefLabel ?pl .
        FILTER(lang(?pl) = "{language}" || lang(?pl) = "") }}
    }} }}
    UNION
    {{
        <{}> skos:member ?m .
        {{ ?n skos:prefLabel ?pl .
        FILTER(lang(?pl) = "{language}" || lang(?pl) = "") }}
    }}
}}'''.format(collection_uri=uri, 
                            language=self.language)
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
        concept_uri=self.request.values.get('uri')
        vocab = g.VOCABS[self.vocab_id]
        q = """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX dct: <http://purl.org/dc/terms/>

select *

WHERE {{
    {{ GRAPH ?graph {{
        <{concept_uri}> ?predicate ?object .
        optional {{GRAPH ?predicateGraph {{?predicate rdfs:label ?predicateLabel .}} 
            FILTER(lang(?predicateLabel) = "{language}" || lang(?predicateLabel) = "")
            }}
        optional {{?object skos:prefLabel | rdfs:label ?objectLabel .
            FILTER(?prefLabel = skos:prefLabel || lang(?objectLabel) = "{language}" || lang(?objectLabel) = "") # Don't filter prefLabel language
        }}
    }} }}
    UNION
    {{
        <{concept_uri}> ?predicate ?object .
        optional {{GRAPH ?predicateGraph {{?predicate rdfs:label ?predicateLabel .}} 
            FILTER(lang(?predicateLabel) = "{language}" || lang(?predicateLabel) = "")
            }}
        optional {{?object skos:prefLabel | rdfs:label ?objectLabel .
            FILTER(?prefLabel = skos:prefLabel || lang(?objectLabel) = "{language}" || lang(?objectLabel) = "") # Don't filter prefLabel language
        }}
    }}
}}""".format(concept_uri=concept_uri, 
             language=self.language)   
        #print(q)
        result = Source.sparql_query(vocab.sparql_endpoint, q, vocab.sparql_username, vocab.sparql_password)
        
        assert result, 'Unable to query concepts for {}'.format(self.request.values.get('uri'))
        
        #print(str(result).encode('utf-8'))

        prefLabel = None
        
        related_objects = {}
        
        for row in result:
            predicateUri = row['predicate']['value']
                
            # Special case for prefLabels
            if predicateUri == 'http://www.w3.org/2004/02/skos/core#prefLabel':
                predicateLabel = 'Multilingual Labels'
                preflabel_lang = row['object'].get('xml:lang')
                
                # Use default language or no language prefLabel as primary
                if ((not prefLabel and not preflabel_lang) or 
                    (preflabel_lang == self.language)
                    ):
                    prefLabel = row['object']['value'] # Set current language prefLabel
                    
                # Omit current language string from list (remove this if we want to show all)
                if preflabel_lang in ['', self.language]:
                    continue
                    
                # Apend language code to prefLabel literal
                related_object = '{} ({})'.format(row['object']['value'], preflabel_lang)
                related_objectLabel = None
            else:
                predicateLabel = (row['predicateLabel']['value'] if row.get('predicateLabel') and row['predicateLabel'].get('value') 
                                  else make_title(row['predicate']['value']))
            
                if row['object']['type'] == 'literal':
                    related_object = row['object']['value']
                    related_objectLabel = None
                elif row['object']['type'] == 'uri':
                    related_object = row['object']['value']
                    related_objectLabel = (row['objectLabel']['value'] if row.get('objectLabel') and row['objectLabel'].get('value') 
                                           else make_title(row['object']['value'])) 
            
            relationship_dict = related_objects.get(predicateUri)
            if relationship_dict is None:
                relationship_dict = {'label': predicateLabel,
                                     'objects': {}}
                related_objects[predicateUri] = relationship_dict
                
            relationship_dict['objects'][related_object] = related_objectLabel
            
        
        related_objects = OrderedDict([(predicate, {'label': related_objects[predicate]['label'],
                                                    'objects': OrderedDict([(key, related_objects[predicate]['objects'][key]) 
                                                                            for key in sorted(related_objects[predicate]['objects'].keys())
                                                                            ])
                                                    }
                                        )
                                       for predicate in sorted(related_objects.keys())
                                       ])
        
        #print(repr(related_objects).encode('utf-8'))
        
        return Concept(
            vocab_id=self.vocab_id,
            uri=concept_uri,
            prefLabel=prefLabel,
            related_objects=related_objects,
            semantic_properties=None,
            source=self,
        )


    def get_concept_hierarchy(self):
        '''
        Function to draw concept hierarchy for vocabulary
        '''
        def build_hierarchy(bindings_list, broader_concept=None, level=0):
            '''
            Recursive helper function to build hierarchy list from a bindings list
            Returns list of tuples: (<level>, <concept>, <concept_preflabel>, <broader_concept>)
            '''
            level += 1 # Start with level 1 for top concepts
            hierarchy = []
            
            narrower_list = sorted([binding_dict 
                                    for binding_dict in bindings_list
                                    if 
                                        # Top concept
                                        ((broader_concept is None) 
                                         and (binding_dict.get('broader_concept') is None))
                                    or 
                                        # Narrower concept
                                        ((binding_dict.get('broader_concept') is not None) 
                                         and (binding_dict['broader_concept']['value'] == broader_concept))
                             ], key=lambda binding_dict: binding_dict['concept_preflabel']['value']) 
            #print(broader_concept, narrower_list)
            for binding_dict in narrower_list: 
                concept = binding_dict['concept']['value']              
                hierarchy += [(level,
                               concept,
                               binding_dict['concept_preflabel']['value'],
                               binding_dict['broader_concept']['value'] if binding_dict.get('broader_concept') else None,
                               )
                              ] + build_hierarchy(bindings_list, concept, level)
            #print(level, hierarchy)
            return hierarchy
        
        
        vocab = g.VOCABS[self.vocab_id]
                 
        query = '''PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX dct: <http://purl.org/dc/terms/>
SELECT distinct ?concept ?concept_preflabel ?broader_concept
WHERE {{
    {{ GRAPH ?graph {{
        ?concept skos:inScheme <{vocab_uri}> .
        ?concept skos:prefLabel ?concept_preflabel .
        OPTIONAL {{ ?concept skos:broader ?broader_concept .
            ?broader_concept skos:inScheme <{vocab_uri}> .
            }}
        FILTER(lang(?concept_preflabel) = "{language}" || lang(?concept_preflabel) = "")
    }} }}
    UNION
    {{
        ?concept skos:inScheme <{vocab_uri}> .
        ?concept skos:prefLabel ?concept_preflabel .
        OPTIONAL {{ ?concept skos:broader ?broader_concept .
            ?broader_concept skos:inScheme <{vocab_uri}> .
            }}
        FILTER(lang(?concept_preflabel) = "{language}" || lang(?concept_preflabel) = "")
    }}
}}
ORDER BY ?concept_preflabel'''.format(vocab_uri=vocab.concept_scheme_uri, language=self.language)
        #print(query)
        bindings_list = Source.sparql_query(vocab.sparql_endpoint, query, vocab.sparql_username, vocab.sparql_password)
        #print(bindings_list)
        assert bindings_list is not None, 'SPARQL concept hierarchy query failed'
         
        hierarchy = build_hierarchy(bindings_list)
        #print(hierarchy)
 
        return Source.draw_concept_hierarchy(hierarchy, self.request, self.vocab_id)


    def get_object_class(self):
        #print('get_object_class uri = {}'.format(url_decode(self.request.values.get('uri'))))
        vocab = g.VOCABS[self.vocab_id]
        q = '''SELECT DISTINCT * 
WHERE {{ 
    {{ GRAPH ?g {{
        <{uri}> a ?c .
    }} }}
    UNION
    {{
        <{uri}> a ?c .
    }}
}}'''.format(uri=url_decode(self.request.values.get('uri')))
        clses = Source.sparql_query(vocab.sparql_endpoint, q, vocab.sparql_username, vocab.sparql_password)
        assert clses is not None, 'SPARQL class query failed'
        #print(clses)
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
                logging.warning('Failed to load resource at URI {}. Attempt: {}.'.format(uri, i+1))
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
    def draw_concept_hierarchy(hierarchy, request, vocab_id):
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

            # Default to showing local URLs unless told otherwise
            if (not hasattr(config, 'LOCAL_URLS')) or config.LOCAL_URLS:
                uri = request.url_root + 'object?vocab_id=' + vocab_id + '&uri=' + h.url_encode(item[1])
            else:
                uri = item[1]

            t = tab * mult + '* [' + item[2] + '](' + uri + ')\n'
            text += t
            previous_length = mult
            tracked_items.append({'name': item[1], 'indent': mult})

        return markdown.markdown(text)

    def get_top_concepts(self):
        vocab = g.VOCABS[self.vocab_id]
        q = '''PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT DISTINCT ?tc ?pl
WHERE {{
    {{ GRAPH ?g 
        {{
            {{
                <{concept_scheme_uri}> skos:hasTopConcept ?tc .                
            }}
            UNION 
            {{
                ?tc skos:topConceptOf <{concept_scheme_uri}> .
            }}
            {{ ?tc skos:prefLabel ?pl .
                FILTER(lang(?pl) = "{language}" || lang(?pl) = "") 
            }}
        }}
    }}
    UNION
    {{
        {{
            <{concept_scheme_uri}> skos:hasTopConcept ?tc .                
        }}
        UNION 
        {{
            ?tc skos:topConceptOf <{concept_scheme_uri}> .
        }}
        {{ ?tc skos:prefLabel ?pl .
            FILTER(lang(?pl) = "{language}" || lang(?pl) = "")
        }}
    }}
}}
ORDER BY ?pl
'''.format(concept_scheme_uri=vocab.concept_scheme_uri,
                                   language=self.language)
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
                q = '''PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT DISTINCT ?tc ?pl
WHERE {{
    {{ GRAPH ?g {{
        {{
            <{concept_scheme_uri}> skos:hasTopConcept ?tc .                
        }}
        UNION 
        {{
            ?tc skos:inScheme <{concept_scheme_uri}> .
        }}
        {{ ?tc skos:prefLabel ?pl .
            FILTER(lang(?pl) = "{language}" || lang(?pl) = "") 
        }}
    }} }}
    UNION
    {{
        {{
            <{concept_scheme_uri}> skos:hasTopConcept ?tc .                
        }}
        UNION 
        {{
            ?tc skos:inScheme <{concept_scheme_uri}> .
        }}
        {{ ?tc skos:prefLabel ?pl .
            FILTER(lang(?pl) = "{language}" || lang(?pl) = "")
        }}
    }}
}}
ORDER BY ?pl
'''.format(concept_scheme_uri=vocab.concept_scheme_uri,
                                           language=self.language)
                #print(q)
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
            return sparql.query().convert()['results']['bindings']
        except Exception as e:
            logging.debug('SPARQL query failed: {}'.format(e))
            logging.debug('endpoint={}\nsparql_username={}\nsparql_password={}\n{}'.format(endpoint, sparql_username, sparql_password, q))
            return None
        
    
    @staticmethod
    def submit_sparql_query(endpoint, q, sparql_username=None, sparql_password=None, accept_format='json'):
        '''
        Function to submit a sparql query and return the textual response
        '''
        #logging.debug('sparql_query = {}'.format(sparql_query))
        accept_format = {'json': 'application/json',
                         'xml': 'application/rdf+xml',
                         'turtle': 'application/turtle'
                         }.get(accept_format) or 'application/json'
        headers = {'Accept': accept_format,
                   'Content-Type': 'application/sparql-query',
                   'Accept-Encoding': 'UTF-8'
                   }
        if (sparql_username and sparql_password):
            #logging.debug('Authenticating with username {} and password {}'.format(sparql_username, sparql_password))
            headers['Authorization'] = 'Basic ' + base64.encodebytes('{}:{}'.format(sparql_username, sparql_password).encode('utf-8')).strip().decode('utf-8')
            
        params = None
        
        retries = 0
        while True:
            try:
                response = requests.post(endpoint, 
                                       headers=headers, 
                                       params=params, 
                                       data=q, 
                                       timeout=config.SPARQL_TIMEOUT)
                #logging.debug('Response content: {}'.format(str(response.content)))
                assert response.status_code == 200, 'Response status code {} != 200'.format(response.status_code)
                return response.text
            except Exception as e:
                logging.warning('SPARQL query failed: {}'.format(e))
                retries += 1
                if retries <= config.MAX_RETRIES:
                    sleep(config.RETRY_SLEEP_SECONDS)
                    continue # Go around again
                else:
                    break
                
        raise(BaseException('SPARQL query failed'))

    @staticmethod
    def get_graph(endpoint, q, sparql_username=None, sparql_password=None):
        '''
        Function to return an rdflib Graph object containing the results of a query
        '''
        result_graph = Graph()
        response = Source.submit_sparql_query(endpoint, q, sparql_username=sparql_username, sparql_password=sparql_password, accept_format='xml')
        #print(response.encode('utf-8'))
        result_graph.parse(data=response)
        return result_graph
    
    @property
    def graph(self):
        cache_file_name = self.vocab_id + '.p'
        
        if self._graph is not None:
            return self._graph
        
        self._graph = cache_read(cache_file_name)        
        if self._graph is not None:
            return self._graph
        
        vocab = g.VOCABS[self.vocab_id]
        
        q = '''PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX rdfs: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

CONSTRUCT {{ ?subject ?predicate ?object }}
WHERE  {{ 
    {{ GRAPH ?graph {{
        {{    # conceptScheme
            ?subject ?predicate ?object .
            ?subject a skos:ConceptScheme .
            <{uri}> a skos:ConceptScheme .
        }}
        union
        {{    # conceptScheme members as subjects
            ?subject ?predicate ?object .
            ?subject skos:inScheme <{uri}> .
        }}
        union
        {{    # conceptScheme members as objects
            ?subject ?predicate ?object .
            ?object skos:inScheme <{uri}> .
        }}
    }} }}
    UNION
    {{
        {{    # conceptScheme
            ?subject ?predicate ?object .
            ?subject a skos:ConceptScheme .
            <{uri}> a skos:ConceptScheme .
        }}
        union
        {{    # conceptScheme members as subjects
            ?subject ?predicate ?object .
            ?subject skos:inScheme <{uri}> .
        }}
        union
        {{    # conceptScheme members as objects
            ?subject ?predicate ?object .
            ?object skos:inScheme <{uri}> .
        }}
    }}
    FILTER(STRSTARTS(STR(?predicate), STR(rdfs:))
        || STRSTARTS(STR(?predicate), STR(skos:))
        || STRSTARTS(STR(?predicate), STR(dct:))
        || STRSTARTS(STR(?predicate), STR(owl:))
        )
}}'''.format(uri=vocab.uri)
        #print(q)
            
        self._graph = Source.get_graph(vocab.sparql_endpoint, q, sparql_username=vocab.sparql_username, sparql_password=vocab.sparql_password)
        cache_write(self._graph, cache_file_name)
        return self._graph
            



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
