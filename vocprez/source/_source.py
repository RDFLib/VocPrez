from flask import g
from ..utils import *
import vocprez._config as config


__all__ = [
    "Source"
]


class Source:
    VOC_TYPES = [
        "http://www.w3.org/2004/02/skos/core#ConceptScheme",
        "http://www.w3.org/2004/02/skos/core#Collection",
        "http://www.w3.org/2004/02/skos/core#Concept",
    ]

    def __init__(self, vocab_uri, request, language=None):
        self.vocab_uri = vocab_uri
        self.request = request
        self.language = language or config.DEFAULT_LANGUAGE

        self._graph = None  # Property for rdflib Graph object to be populated on demand

    @property
    def graph(self):
        # no graph cache file so extract graph from source and cache
        vocab = g.VOCABS[self.vocab_uri]

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
        cache_write(self._graph)
        return self._graph

    @staticmethod
    def collect(details):
        """
        Specialised Sources must implement a collect method to get all the vocabs of their sort, listed in
        _config/__init__.py, at startup
        """
        pass

    def list_collections(self):
        vocab = g.VOCABS[self.vocab_uri]
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
        vocab = g.VOCABS[self.vocab_uri]
        q = """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT DISTINCT ?c ?pl ?broader
            WHERE {{
                GRAPH <{vocab_uri}> {{
                    ?c a skos:Concept ;
                         skos:prefLabel ?pl .

                    OPTIONAL {{
                        {{?c skos:broader ?broader}}
                        UNION 
                        {{?broader skos:narrower ?c}}
                    }}

                    FILTER(lang(?pl) = "{language}" || lang(?pl) = "") 
                }}
            }}
            ORDER BY ?pl
            """.format(vocab_uri=vocab.uri, language=self.language)

        return [
            (
                concept["c"]["value"],
                concept["pl"]["value"],
                concept["broader"]["value"] if concept.get("broader") else None
            )
            for concept in sparql_query(q, vocab.sparql_endpoint, vocab.sparql_username, vocab.sparql_password)
        ]

    def get_vocabulary(self):
        """
        Get a vocab from the cache
        :return:
        :rtype:
        """
        vocab = g.VOCABS[self.vocab_uri]
        vocab.concept_hierarchy = self.get_concept_hierarchy()
        vocab.concepts = self.list_concepts()
        vocab.collections = self.list_collections()
        return vocab

    def get_collection(self, uri):
        vocab = g.VOCABS[self.vocab_uri]
        # get the collection's metadata and members
        q = """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            
            SELECT *
            WHERE {{
                <{collection_uri}> ?p ?o .            
                
                OPTIONAL {{
                    ?o skos:prefLabel ?mpl .
                }}
                
                FILTER(lang(?o) = "{language}" || lang(?o) = "" || ISURI(?o))
            }}
            """.format(collection_uri=uri, language=self.language)

        pl = None
        d = None
        s = {
            "provenance": None,
            "source": None,
            "wasDerivedFrom": None,
        }
        m = []
        found = False
        for r in sparql_query(q, vocab.sparql_endpoint, vocab.sparql_username, vocab.sparql_password):
            found = True
            if r["o"]["value"] == "http://www.w3.org/2004/02/skos/core#Concept":
                return None

            if r["p"]["value"] == "http://www.w3.org/2004/02/skos/core#prefLabel":
                pl = r["o"]["value"]
            elif r["p"]["value"] == "http://www.w3.org/2004/02/skos/core#definition":
                d = r["o"]["value"]
            elif r["p"]["value"] == "http://purl.org/dc/terms/provenance":
                s["provenance"] = r["o"]["value"]
            elif r["p"]["value"] == "http://purl.org/dc/terms/source":
                s["source"] = r["o"]["value"]
            elif r["p"]["value"] == "http://www.w3.org/ns/prov#wasDerivedFrom":
                s["wasDerivedFrom"] = r["o"]["value"]
            elif r["p"]["value"] == "http://www.w3.org/2004/02/skos/core#member":
                m.append((r["o"]["value"], r["mpl"]["value"]))

        if not found:
            return None

        from vocprez.model.collection import Collection

        return Collection(self.vocab_uri, uri, pl, d, s, m)

    def get_concept(self, uri):
        vocab = g.VOCABS[self.vocab_uri]
        # q = """
        #     PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        #     PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        #
        #     SELECT *
        #     WHERE {{
        #         <{concept_uri}> a skos:Concept ;
        #                         ?p ?o .
        #
        #         OPTIONAL {{
        #             GRAPH ?predicateGraph {{?p rdfs:label ?predicateLabel .}}
        #             FILTER(lang(?predicateLabel) = "{language}" || lang(?predicateLabel) = "")
        #         }}
        #         OPTIONAL {{
        #             ?o skos:prefLabel ?objectLabel .
        #             FILTER(?prefLabel = skos:prefLabel || lang(?objectLabel) = "{language}" || lang(?objectLabel) = "")
        #             # Don't filter prefLabel language
        #         }}
        #     }}
        #     """.format(
        #     concept_uri=uri, language=self.language
        # )
        q = """
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

            SELECT DISTINCT *            
            WHERE {{
                <{concept_uri}> a skos:Concept ;
                                ?p ?o .
                
                OPTIONAL {{
                    ?o skos:prefLabel ?ropl .
                }}                
            }}
            """.format(
            concept_uri=uri, language=self.language
        )

        pl = None
        d = None
        s = {
            "provenance": None,
            "source": None,
            "wasDerivedFrom": None,
        }
        annotation_types = {
            "http://www.opengis.net/def/metamodel/ogc-na/status": "Status"
        }
        annotations = {}
        agent_types = {
            'http://purl.org/dc/terms/contributor': "Contributor",
            'http://purl.org/dc/terms/creator': "Creator",
            'http://purl.org/dc/terms/publisher': "Publisher",
        }
        agent = {}
        related_instance_types = {
            'http://www.w3.org/2004/02/skos/core#exactMatch': "Exact Match",
            'http://www.w3.org/2004/02/skos/core#closeMatch': "Close Match",
            'http://www.w3.org/2004/02/skos/core#broadMatch': "Broad Match",
            'http://www.w3.org/2004/02/skos/core#narrowMatch': "Narrow Match",
            'http://www.w3.org/2004/02/skos/core#broader': "Broader",
            'http://www.w3.org/2004/02/skos/core#narrower': "Narrower"
        }
        related_instances = {}
        found = False
        for r in sparql_query(q, vocab.sparql_endpoint, vocab.sparql_username, vocab.sparql_password):
            found = True
            if r["p"]["value"] == "http://www.w3.org/2004/02/skos/core#prefLabel":
                pl = r["o"]["value"]
            elif r["p"]["value"] == "http://www.w3.org/2004/02/skos/core#definition":
                d = r["o"]["value"]
            elif r["p"]["value"] == "http://purl.org/dc/terms/provenance":
                s["provenance"] = r["o"]["value"]
            elif r["p"]["value"] == "http://purl.org/dc/terms/source":
                s["source"] = r["o"]["value"]
            elif r["p"]["value"] == "http://www.w3.org/ns/prov#wasDerivedFrom":
                s["wasDerivedFrom"] = r["o"]["value"]

            elif r["p"]["value"] in annotation_types.keys():
                if r.get("ropl") is not None:
                    # annotation value has a labe too
                    annotations[r["p"]["value"]] = (annotation_types[r["p"]["value"]], r["o"]["value"], r["ropl"]["value"])
                else:
                    # no label
                    annotations[r["p"]["value"]] = (annotation_types[r["p"]["value"]], r["o"]["value"])

            elif r["p"]["value"] in related_instance_types.keys():
                if related_instances.get(r["p"]["value"]) is None:
                    related_instances[r["p"]["value"]] = {}
                    related_instances[r["p"]["value"]] = {
                        "instances": [],
                        "label": related_instance_types[r["p"]["value"]]
                    }
                related_instances[r["p"]["value"]]["instances"].append(
                    (r["o"]["value"], r["ropl"]["value"] if r["ropl"] is not None else None)
                )

        if not found:
            return None

            # TODO: Agents

            # TODO: more Annotations

        from vocprez.model.concept import Concept

        return Concept(
            self.vocab_uri,
            uri,
            pl,
            d,
            related_instances,
            annotations
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

        vocab = g.VOCABS[self.vocab_uri]

        query = """
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            
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

        return draw_concept_hierarchy(hierarchy, self.request, self.vocab_uri)

    def get_object_class(self):
        vocab = g.VOCABS[self.vocab_uri]
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
