from collections import OrderedDict
import dateutil
from flask import g
from vocprez.model.concept import Concept
from .utils import cache_read, cache_write, url_decode, sparql_query, draw_concept_hierarchy, make_title, get_graph
import vocprez._config as config


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
        self.language = language or config.DEFAULT_LANGUAGE

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

                self._graph = get_graph(
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
        q = """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT DISTINCT ?c ?pl
            WHERE {{
                GRAPH <{vocab_uri}> {{
                    ?c  a skos:Collection ;
                        skos:prefLabel ?pl .
                        
                    FILTER(lang(?pl) = "{language}" || lang(?pl) = "") 
                }}
            }}
            """.format(vocab_uri=vocab.uri, language=self.language)
        collections = sparql_query(q, vocab.sparql_endpoint, vocab.sparql_username, vocab.sparql_password)

        return [(x.get("c").get("value"), x.get("pl").get("value")) for x in collections]

    def list_concepts(self):
        vocab = g.VOCABS[self.vocab_id]
        q = """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX dct: <http://purl.org/dc/terms/>
            SELECT DISTINCT ?c ?pl
            WHERE {{
                    {{ ?c skos:inScheme <{uri}> . }}
                    UNION
                    {{ ?c skos:topConceptOf <{uri}> . }}
                    UNION
                    {{ <{uri}> skos:hasTopConcept ?c . }}
            
                    ?c skos:prefLabel ?pl .
                    FILTER(lang(?pl) = "{language}" || lang(?pl) = "") 
            }}
            ORDER BY ?pl
            """.format(uri=vocab.uri, language=self.language)
        concepts = sparql_query(
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
        vocab.concept_hierarchy = self.get_concept_hierarchy()
        vocab.collections = self.list_collections()
        return vocab

    def get_collection(self, uri):
        vocab = g.VOCABS[self.vocab_id]
        q = """
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT DISTINCT ?pl ?d
            WHERE {{ 
                <{collection_uri}> skos:prefLabel ?pl .
                    FILTER(lang(?pl) = "{language}" || lang(?pl) = "") }}
                    OPTIONAL {{<{collection_uri}> skos:definition ?d .
                    FILTER(lang(?d) = "{language}" || lang(?d) = "") }}
            }}
            """.format(collection_uri=uri, language=self.language)
        metadata = sparql_query(vocab.sparql_endpoint, q, vocab.sparql_username, vocab.sparql_password)

        # get the collection's members
        q = """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT DISTINCT ?m ?pl
            WHERE {{
                <{collection_uri}> skos:member ?m .
                ?m skos:prefLabel ?pl .
                FILTER(lang(?pl) = "{language}" || lang(?pl) = "")
            }}
            ORDER BY ?pl
            """.format(
            collection_uri=uri, language=self.language
        )

        members = sparql_query(
            vocab.sparql_endpoint, q, vocab.sparql_username, vocab.sparql_password
        )

        from vocprez.model.collection import Collection

        return Collection(
            self.vocab_id,
            uri,
            metadata[0]["l"]["value"],
            metadata[0].get("c").get("value") if metadata[0].get("c") is not None else None,
            [(x.get("m").get("value"), x.get("pl").get("value")) for x in members],
        )

    def get_concept(self):
        concept_uri = self.request.values.get("uri")
        vocab = g.VOCABS[self.vocab_id]
        q = """
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX dct: <http://purl.org/dc/terms/>
            
            SELECT *            
            WHERE {{
                <{concept_uri}> ?p ?o .
                OPTIONAL {{
                    GRAPH ?predicateGraph {{?p rdfs:label ?predicateLabel .}} 
                    FILTER(lang(?predicateLabel) = "{language}" || lang(?predicateLabel) = "")
                }}
                OPTIONAL {{
                    ?o skos:prefLabel ?objectLabel .
                    FILTER(?prefLabel = skos:prefLabel || lang(?objectLabel) = "{language}" || lang(?objectLabel) = "") 
                    # Don't filter prefLabel language
                }}
            }}
            """.format(
            concept_uri=concept_uri, language=self.language
        )
        result = sparql_query(q, vocab.sparql_endpoint, vocab.sparql_username, vocab.sparql_password)

        assert result, "Unable to query concepts for {}".format(
            self.request.values.get("uri")
        )

        prefLabel = None

        related_objects = {}

        for row in result:
            predicateUri = row["p"]["value"]

            # Special case for prefLabels
            if predicateUri == "http://www.w3.org/2004/02/skos/core#prefLabel":
                predicateLabel = "Multilingual Labels"
                preflabel_lang = row["o"].get("xml:lang")

                # Use default language or no language prefLabel as primary
                if (not prefLabel and not preflabel_lang) or (
                        preflabel_lang == self.language
                ):
                    prefLabel = row["o"]["value"]  # Set current language prefLabel

                # Omit current language string from list (remove this if we want to show all)
                if preflabel_lang in ["", self.language]:
                    continue

                # Append language code to prefLabel literal
                related_object = "{} ({})".format(
                    row["object"]["value"], preflabel_lang
                )
                related_objectLabel = None
            else:
                predicateLabel = (
                    row["predicateLabel"]["value"]
                    if row.get("predicateLabel") and row["predicateLabel"].get("value")
                    else make_title(row["p"]["value"])
                )

                if row["o"]["type"] == "literal":
                    related_object = row["o"]["value"]
                    related_objectLabel = None
                elif row["o"]["type"] == "uri":
                    related_object = row["o"]["value"]
                    related_objectLabel = (
                        row["objectLabel"]["value"]
                        if row.get("objectLabel") and row["objectLabel"].get("value")
                        else make_title(row["o"]["value"])
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
            hier = []

            narrower_list = sorted(
                [
                    binding_dict
                    for binding_dict in bindings_list
                    if (  # Top concept
                               (broader_concept is None)
                               and (binding_dict.get("broader_concept") is None)
                       )
                       or  # Narrower concept
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
                hier += [
                                 (
                                     level,
                                     concept,
                                     binding_dict["concept_preflabel"]["value"],
                                     binding_dict["broader_concept"]["value"]
                                     if binding_dict.get("broader_concept")
                                     else None,
                                 )
                             ] + build_hierarchy(bindings_list, concept, level)
            return hier

        vocab = g.VOCABS[self.vocab_id]

        query = """
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX dct: <http://purl.org/dc/terms/>
            SELECT distinct ?concept ?concept_preflabel ?broader_concept
            WHERE {{
                {{ ?concept skos:inScheme <{vocab_uri}> . }}
                UNION
                {{ ?concept skos:topConceptOf <{vocab_uri}> . }}
                UNION
                {{ <{vocab_uri}> skos:hasTopConcept ?concept . }}  
                ?concept skos:prefLabel ?concept_preflabel .
                OPTIONAL {{ 
                    ?concept skos:broader ?broader_concept .
                    ?broader_concept skos:inScheme <{vocab_uri}> .
                }}
                FILTER(lang(?concept_preflabel) = "{language}" || lang(?concept_preflabel) = "")
            }}
            ORDER BY ?concept_preflabel
            """.format(
                vocab_uri=vocab.uri,
                language=self.language
            )

        bindings_list = sparql_query(query, vocab.sparql_endpoint, vocab.sparql_username, vocab.sparql_password)

        assert bindings_list is not None, "SPARQL concept hierarchy query failed"

        hierarchy = build_hierarchy(bindings_list)

        return draw_concept_hierarchy(hierarchy, self.request, self.vocab_id)

    def get_object_class(self):
        vocab = g.VOCABS[self.vocab_id]
        q = """
            SELECT DISTINCT * 
            WHERE {{ 
                <{uri}> a ?c .
            }}
            """.format(
            uri=url_decode(self.request.values.get("uri"))
        )
        clses = sparql_query(q, vocab.sparql_endpoint, vocab.sparql_username, vocab.sparql_password)
        assert clses is not None, "SPARQL class query failed"
        # look for classes we understand (SKOS)
        for cls in clses:
            if cls["c"]["value"] in Source.VOC_TYPES:
                return cls["c"]["value"]

        return None
