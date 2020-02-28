from pyldapi import Renderer
from flask import Response, render_template, g
import _config as config
from rdflib import Graph, URIRef
from rdflib.namespace import SKOS, DCTERMS, NamespaceManager
from model.profiles import profile_skos


class Concept:
    def __init__(
        self, vocab_id, uri, prefLabel, related_objects, semantic_properties, source,
    ):
        self.vocab_id = vocab_id
        self.uri = uri
        self.prefLabel = prefLabel
        self.related_objects = related_objects
        self.semantic_properties = semantic_properties
        self.source = source


class ConceptRenderer(Renderer):
    def __init__(self, request, concept):
        self.request = request
        self.profiles = self._add_views()
        self.navs = []  # TODO: add in other nav items for Concept

        self.concept = concept

        super().__init__(self.request, self.concept.uri, self.profiles, "skos")

    def _add_views(self):
        return {"skos": profile_skos}

    def render(self):
        # try returning alt profile
        response = super().render()
        if response is not None:
            return response
        elif self.profile == "skos":
            if (
                self.mediatype in Renderer.RDF_MEDIA_TYPES
                or self.mediatype in Renderer.RDF_SERIALIZER_TYPES_MAP
            ):
                return self._render_skos_rdf()
            else:
                return self._render_skos_html()

    def _render_skos_rdf(self):
        namespace_manager = NamespaceManager(Graph())
        namespace_manager.bind("dct", DCTERMS)
        namespace_manager.bind("skos", SKOS)
        concept_g = Graph()
        concept_g.namespace_manager = namespace_manager

        for s, p, o in self.concept.source.graph.triples(
            (URIRef(self.concept.uri), None, None)
        ):
            concept_g.add((s, p, o))

        # serialise in the appropriate RDF format
        if self.mediatype in ["application/rdf+json", "application/json"]:
            return Response(
                concept_g.serialize(format="json-ld"), mimetype=self.mediatype
            )
        else:
            return Response(
                concept_g.serialize(format=self.mediatype), mimetype=self.mediatype
            )

        # # Create a graph from the self.concept object for a SKOS view
        # namespace_manager = NamespaceManager(Graph())
        # namespace_manager.bind('dct', DCTERMS)
        # namespace_manager.bind('skos', SKOS)
        #
        # s = URIRef(self.concept.uri)
        # g = Graph()
        # g.namespace_manager = namespace_manager
        # if self.concept.prefLabel:
        #     g.add((s, SKOS.prefLabel, Literal(self.concept.prefLabel)))
        # if self.concept.definition:
        #     g.add((s, SKOS.definition, Literal(self.concept.definition)))
        # if self.concept.altLabels:
        #     for label in self.concept.altLabels:
        #         g.add((s, SKOS.altLabel, Literal(label)))
        # if self.concept.hiddenLabels:
        #     for label in self.concept.hiddenLabels:
        #         g.add((s, SKOS.hiddenLabel, Literal(label)))
        # if self.concept.source:
        #     g.add((s, DCTERMS.source, Literal(self.concept.source)))
        # if self.concept.contributors:
        #     for cont in self.concept.contributors:
        #         g.add((s, DCTERMS.contributor, Literal(cont)))
        # if self.concept.broaders: #
        #     for n in self.concept.broaders:
        #         g.add((s, SKOS.broader, Literal(self.concept.broaders)))
        # if self.concept.narrowers:
        #     for n in self.concept.narrowers:
        #         g.add((s, SKOS.narrower, URIRef(n['uri'])))
        #         g.add((URIRef(n['uri']), SKOS.prefLabel, Literal(n['prefLabel'])))
        # # TODO: vocab_id, uri, semantic_properties
        #
        # # serialise in the appropriate RDF format
        # if self.mediatype in ['application/rdf+json', 'application/json']:
        #     return Response(g.serialize(format='json-ld'), mimetype=self.mediatype)
        # else:
        #     return Response(g.serialize(format=self.mediatype), mimetype=self.mediatype)

    def _render_skos_html(self):
        _template_context = {
            "vocab_id": self.request.values.get("vocab_id"),
            "vocab_title": g.VOCABS[self.request.values.get("vocab_id")].title,
            "uri": self.request.values.get("uri"),
            "concept": self.concept,
            "navs": self.navs,
            "title": "Concept: " + self.concept.prefLabel,
            "config": config,
        }

        return Response(
            render_template("concept.html", **_template_context), headers=self.headers
        )
