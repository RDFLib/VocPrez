from collections import OrderedDict
import dateutil
from flask import g
from vocprez.model.concept import Concept
from .utils import cache_read, cache_write, url_decode


__all__ = [
    "Source"
]


class Source:
    VOC_TYPES = [
        "http://purl.org/vocommons/voaf#Vocabulary",
        "http://www.w3.org/2004/02/skos/core#ConceptScheme",
        "http://www.w3.org/2004/02/skos/core#Collection",
        "http://www.w3.org/2004/02/skos/core#Concept",
    ]

    def __init__(self, vocab_id, request, language=None):
        self.vocab_id = vocab_id
        self.request = request
        self.language = language or DEFAULT_LANGUAGE

        self._graph = None  # Property for rdflib Graph object to be populated on demand

    @property
    def graph(self):
        # if we have a graph in memory, return that
        if self._graph is not None:
            return self._graph
        else:
            cache_file_name = self.vocab_id + ".p"
            self._graph = cache_read(cache_file_name)

            # if we got one from the cache file, return that
            if self._graph is not None:
                return self._graph
            else:
                # no graph cache file so extract graph from source and cache
                vocab = g.VOCABS[self.vocab_id]

                q = """
                        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
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
                        }}""".format(
                    uri=vocab.uri
                )

                self._graph = Source.get_graph(
                    vocab.sparql_endpoint,
                    q,
                    sparql_username=vocab.sparql_username,
                    sparql_password=vocab.sparql_password,
                )
                cache_write(self._graph, cache_file_name)
                return self._graph

    @staticmethod
    def collect(details):
        """
        Specialised Sources must implement a collect method to get all the vocabs of their sort, listed in
        _config/__init__.py, at startup
        """
        pass

    def list_collections(self):
        vocab = g.VOCABS[self.vocab_id]
        q = """PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?c ?l
WHERE {{
    {{ GRAPH ?g {{
        {{?c a skos:Collection .
        FILTER (REGEX(STR(?c), "^{vocab_uri}", "i"))
        }}
        {{?c (rdfs:label | skos:prefLabel) ?l .
        FILTER(lang(?l) = "{language}" || lang(?l) = "") 
        }}
    }} }}
    UNION
    {{
        {{?c a skos:Collection .
        FILTER (REGEX(STR(?c), "^{vocab_uri}", "i"))
        }}
        {{?c (rdfs:label | skos:prefLabel) ?l .
        FILTER(lang(?l) = "{language}" || lang(?l) = "") 
        }}
    }} 
}}""".format(
            vocab_uri=vocab.uri, language=self.language
        )
        collections = Source.sparql_query(
            vocab.sparql_endpoint, q, vocab.sparql_username, vocab.sparql_password
        )

        return [(x.get("c").get("value"), x.get("l").get("value")) for x in collections]

    def list_concepts(self):
        vocab = g.VOCABS[self.vocab_id]
        q = """PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX dct: <http://purl.org/dc/terms/>
SELECT DISTINCT ?c ?pl
WHERE {{
    {{ GRAPH ?g {{
        {{ ?c skos:inScheme <{concept_scheme_uri}> . }}
        UNION
        {{ ?c skos:topConceptOf <{concept_scheme_uri}> . }}
        UNION
        {{ <{concept_scheme_uri}> skos:hasTopConcept ?c . }}

        {{ ?c skos:prefLabel ?pl .
        FILTER(lang(?pl) = "{language}" || lang(?pl) = "") 
        }}
    }} }}
    UNION
    {{
        {{ ?c skos:inScheme <{concept_scheme_uri}> . }}
        UNION
        {{ ?c skos:topConceptOf <{concept_scheme_uri}> . }}
        UNION
        {{ <{concept_scheme_uri}> skos:hasTopConcept ?c . }}

        {{ ?c skos:prefLabel ?pl .
        FILTER(lang(?pl) = "{language}" || lang(?pl) = "") 
        }}
    }}
}}
ORDER BY ?pl""".format(
            concept_scheme_uri=vocab.concept_scheme_uri, language=self.language
        )
        concepts = Source.sparql_query(
            vocab.sparql_endpoint, q, vocab.sparql_username, vocab.sparql_password
        )

        concept_items = []
        for concept in concepts:
            metadata = {
                "key": self.vocab_id,
                "uri": concept["c"]["value"],
                "title": concept["pl"]["value"],
                "definition": concept.get("d")["value"] if concept.get("d") else None,
                "created": dateutil.parser.parse(concept["created"]["value"])
                if concept.get("created")
                else None,
                "modified": dateutil.parser.parse(concept["modified"]["value"])
                if concept.get("modified")
                else None,
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
        vocab.concepts = self.get_concepts()
        vocab.collections = self.list_collections()
        return vocab

    def get_collection(self, uri):
        vocab = g.VOCABS[self.vocab_id]
        q = """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT DISTINCT ?l ?c
WHERE {{ 
    {{ GRAPH ?g {{
        {{ <{collection_uri}> (rdfs:label|skos:prefLabel) ?l .
        FILTER(lang(?l) = "{language}" || lang(?l) = "") }}
        OPTIONAL {{<{collection_uri}> (rdfs:comment|skos:definition) ?c .
        FILTER(lang(?c) = "{language}" || lang(?c) = "") }}
    }} }}
    UNION
    {{
        {{ <{collection_uri}> (rdfs:label|skos:prefLabel) ?l .
        FILTER(lang(?l) = "{language}" || lang(?l) = "") }}
        OPTIONAL {{<{collection_uri}> (rdfs:comment|skos:definition) ?c .
        FILTER(lang(?c) = "{language}" || lang(?c) = "") }}
    }}
}}""".format(
            collection_uri=uri, language=self.language
        )
        metadata = Source.sparql_query(
            vocab.sparql_endpoint, q, vocab.sparql_username, vocab.sparql_password
        )

        # get the collection's members
        q = """
                PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
                SELECT DISTINCT ?m ?pl
                WHERE {{
                    {{ GRAPH ?g {{
                        <{collection_uri}> skos:member ?m .
                        {{ ?m skos:prefLabel ?pl .
                        FILTER(lang(?pl) = "{language}" || lang(?pl) = "") }}
                    }} }}
                    UNION
                    {{
                        <{collection_uri}> skos:member ?m .
                        {{ ?m skos:prefLabel ?pl .
                        FILTER(lang(?pl) = "{language}" || lang(?pl) = "") }}
                    }}
                }}
                ORDER BY ?pl
            """.format(
            collection_uri=uri, language=self.language
        )

        members = Source.sparql_query(
            vocab.sparql_endpoint, q, vocab.sparql_username, vocab.sparql_password
        )

        from model.collection import Collection

        return Collection(
            self.vocab_id,
            uri,
            metadata[0]["l"]["value"],
            metadata[0].get("c").get("value")
            if metadata[0].get("c") is not None
            else None,
            [(x.get("m").get("value"), x.get("pl").get("value")) for x in members],
        )

    def get_concept(self):
        concept_uri = self.request.values.get("uri")
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
}}""".format(
            concept_uri=concept_uri, language=self.language
        )
        result = Source.sparql_query(
            vocab.sparql_endpoint, q, vocab.sparql_username, vocab.sparql_password
        )

        assert result, "Unable to query concepts for {}".format(
            self.request.values.get("uri")
        )

        prefLabel = None

        related_objects = {}

        for row in result:
            predicateUri = row["predicate"]["value"]

            # Special case for prefLabels
            if predicateUri == "http://www.w3.org/2004/02/skos/core#prefLabel":
                predicateLabel = "Multilingual Labels"
                preflabel_lang = row["object"].get("xml:lang")

                # Use default language or no language prefLabel as primary
                if (not prefLabel and not preflabel_lang) or (
                        preflabel_lang == self.language
                ):
                    prefLabel = row["object"]["value"]  # Set current language prefLabel

                # Omit current language string from list (remove this if we want to show all)
                if preflabel_lang in ["", self.language]:
                    continue

                # Apend language code to prefLabel literal
                related_object = "{} ({})".format(
                    row["object"]["value"], preflabel_lang
                )
                related_objectLabel = None
            else:
                predicateLabel = (
                    row["predicateLabel"]["value"]
                    if row.get("predicateLabel") and row["predicateLabel"].get("value")
                    else make_title(row["predicate"]["value"])
                )

                if row["object"]["type"] == "literal":
                    related_object = row["object"]["value"]
                    related_objectLabel = None
                elif row["object"]["type"] == "uri":
                    related_object = row["object"]["value"]
                    related_objectLabel = (
                        row["objectLabel"]["value"]
                        if row.get("objectLabel") and row["objectLabel"].get("value")
                        else make_title(row["object"]["value"])
                    )

            relationship_dict = related_objects.get(predicateUri)
            if relationship_dict is None:
                relationship_dict = {"label": predicateLabel, "objects": {}}
                related_objects[predicateUri] = relationship_dict

            relationship_dict["objects"][related_object] = related_objectLabel

        related_objects = OrderedDict(
            [
                (
                    predicate,
                    {
                        "label": related_objects[predicate]["label"],
                        "objects": OrderedDict(
                            [
                                (key, related_objects[predicate]["objects"][key])
                                for key in sorted(
                                related_objects[predicate]["objects"].keys()
                            )
                            ]
                        ),
                    },
                )
                for predicate in sorted(related_objects.keys())
            ]
        )

        return Concept(
            vocab_id=self.vocab_id,
            uri=concept_uri,
            prefLabel=prefLabel,
            related_objects=related_objects,
            semantic_properties=None,
            source=self,
        )

    def get_concepts(self):
        vocab = g.VOCABS[self.vocab_id]
        q = """PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
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
                    UNION
                    {{
                        ?tc skos:inScheme <{concept_scheme_uri}> .                
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
        """.format(
            concept_scheme_uri=vocab.concept_scheme_uri, language=self.language
        )
        top_concepts = Source.sparql_query(
            vocab.sparql_endpoint, q, vocab.sparql_username, vocab.sparql_password
        )
        if top_concepts is not None:
            # cache prefLabels and do not add duplicates. This prevents Concepts with sameAs properties appearing twice
            pl_cache = []
            tcs = []
            for tc in top_concepts:
                if (
                        tc.get("pl").get("value") not in pl_cache
                ):  # only add if not already in cache
                    tcs.append((tc.get("tc").get("value"), tc.get("pl").get("value")))
                    pl_cache.append(tc.get("pl").get("value"))

            return tcs
        else:
            return None

    def get_concept_hierarchy(self):
        """
        Function to draw concept hierarchy for vocabulary
        """

        def build_hierarchy(bindings_list, broader_concept=None, level=0):
            """
            Recursive helper function to build hierarchy list from a bindings list
            Returns list of tuples: (<level>, <concept>, <concept_preflabel>, <broader_concept>)
            """
            level += 1  # Start with level 1 for top concepts
            hierarchy = []

            narrower_list = sorted(
                [
                    binding_dict
                    for binding_dict in bindings_list
                    if (  # Top concept
                               (broader_concept is None)
                               and (binding_dict.get("broader_concept") is None)
                       )
                       or
                       # Narrower concept
                       (
                               (binding_dict.get("broader_concept") is not None)
                               and (
                                       binding_dict["broader_concept"]["value"] == broader_concept
                               )
                       )
                ],
                key=lambda binding_dict: binding_dict["concept_preflabel"]["value"],
            )
            for binding_dict in narrower_list:
                concept = binding_dict["concept"]["value"]
                hierarchy += [
                                 (
                                     level,
                                     concept,
                                     binding_dict["concept_preflabel"]["value"],
                                     binding_dict["broader_concept"]["value"]
                                     if binding_dict.get("broader_concept")
                                     else None,
                                 )
                             ] + build_hierarchy(bindings_list, concept, level)
            return hierarchy

        vocab = g.VOCABS[self.vocab_id]

        query = """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX dct: <http://purl.org/dc/terms/>
SELECT distinct ?concept ?concept_preflabel ?broader_concept
WHERE {{
    {{ GRAPH ?graph {{
        {{ ?concept skos:inScheme <{vocab_uri}> . }}
        UNION
        {{ ?concept skos:topConceptOf <{vocab_uri}> . }}
        UNION
        {{ <{vocab_uri}> skos:hasTopConcept ?concept . }}  
        ?concept skos:prefLabel ?concept_preflabel .
        OPTIONAL {{ ?concept skos:broader ?broader_concept .
            ?broader_concept skos:inScheme <{vocab_uri}> .
            }}
        FILTER(lang(?concept_preflabel) = "{language}" || lang(?concept_preflabel) = "")
    }} }}
    UNION
    {{
        {{ ?concept skos:inScheme <{vocab_uri}> . }}
        UNION
        {{ ?concept skos:topConceptOf <{vocab_uri}> . }}
        UNION
        {{ <{vocab_uri}> skos:hasTopConcept ?concept . }}  
        ?concept skos:prefLabel ?concept_preflabel .
        OPTIONAL {{ ?concept skos:broader ?broader_concept .
            ?broader_concept skos:inScheme <{vocab_uri}> .
            }}
        FILTER(lang(?concept_preflabel) = "{language}" || lang(?concept_preflabel) = "")
    }}
}}
ORDER BY ?concept_preflabel""".format(
            vocab_uri=vocab.concept_scheme_uri, language=self.language
        )

        bindings_list = Source.sparql_query(
            vocab.sparql_endpoint, query, vocab.sparql_username, vocab.sparql_password
        )

        assert bindings_list is not None, "SPARQL concept hierarchy query failed"

        hierarchy = build_hierarchy(bindings_list)

        return Source.draw_concept_hierarchy(hierarchy, self.request, self.vocab_id)

    def get_object_class(self):
        vocab = g.VOCABS[self.vocab_id]
        q = """SELECT DISTINCT * 
WHERE {{ 
    {{ GRAPH ?g {{
        <{uri}> a ?c .
    }} }}
    UNION
    {{
        <{uri}> a ?c .
    }}
}}""".format(
            uri=url_decode(self.request.values.get("uri"))
        )
        clses = Source.sparql_query(
            vocab.sparql_endpoint, q, vocab.sparql_username, vocab.sparql_password
        )
        assert clses is not None, "SPARQL class query failed"
        # look for classes we understand (SKOS)
        for cls in clses:
            if cls["c"]["value"] in Source.VOC_TYPES:
                return cls["c"]["value"]

        return None

    def get_top_concepts(self):
        vocab = g.VOCABS[self.vocab_id]
        q = """PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
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
""".format(
            concept_scheme_uri=vocab.concept_scheme_uri, language=self.language
        )
        top_concepts = Source.sparql_query(
            vocab.sparql_endpoint, q, vocab.sparql_username, vocab.sparql_password
        )

        if top_concepts is not None:
            # cache prefLabels and do not add duplicates. This prevents Concepts with sameAs properties appearing twice
            pl_cache = []
            tcs = []
            for tc in top_concepts:
                if (
                        tc.get("pl").get("value") not in pl_cache
                ):  # only add if not already in cache
                    tcs.append((tc.get("tc").get("value"), tc.get("pl").get("value")))
                    pl_cache.append(tc.get("pl").get("value"))

            if len(tcs) == 0:
                q = """PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
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
""".format(
                    concept_scheme_uri=vocab.concept_scheme_uri, language=self.language
                )
                top_concepts = Source.sparql_query(
                    vocab.sparql_endpoint,
                    q,
                    vocab.sparql_username,
                    vocab.sparql_password,
                )
                for tc in top_concepts:
                    if (
                            tc.get("pl").get("value") not in pl_cache
                    ):  # only add if not already in cache
                        tcs.append(
                            (tc.get("tc").get("value"), tc.get("pl").get("value"))
                        )
                        pl_cache.append(tc.get("pl").get("value"))

            return tcs
        else:
            return None