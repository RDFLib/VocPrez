from vocprez import __version__
from pyldapi import Renderer
from flask import Response, render_template, g
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import DCTERMS, RDF, RDFS, SKOS
from vocprez.model.profiles import profile_skos
import vocprez._config as config
from typing import List
from vocprez.model.property import Property


class Concept:
    def __init__(
        self,
        vocab_uri,
        uri,
        prefLabel,
        definition,
        related_instances,
        annotations=None,
        other_properties: List[Property] = None
    ):
        self.vocab_uri = vocab_uri
        self.uri = uri
        self.prefLabel = prefLabel
        self.definition = definition
        self.related_instances = related_instances
        self.annotations = annotations
        self.agents = None

        self.other_properties = other_properties


class ConceptRenderer(Renderer):
    def __init__(self, request, concept):
        self.request = request
        self.profiles = self._add_views()
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
        g = Graph()
        g.bind("dct", DCTERMS)
        g.bind("skos", SKOS)

        c = URIRef(self.concept.uri)

        # Concept SKOS metadata
        g.add((
            c,
            RDF.type,
            SKOS.Concept
        ))
        g.add((
            c,
            SKOS.prefLabel,
            Literal(self.concept.prefLabel, lang=config.DEFAULT_LANGUAGE)
        ))
        g.add((
            c,
            SKOS.definition,
            Literal(self.concept.definition, lang=config.DEFAULT_LANGUAGE)
        ))

        for k, v in self.concept.related_instances.items():
            for k2, v2 in v.items():
                if k2 == "instances":
                    for inst in v2:
                        g.add((
                            c,
                            URIRef(k),
                            URIRef(inst[0])  # only URIs for RDF, not prefLabels too
                        ))

        if self.concept.other_properties is not None:
            for prop in self.concept.other_properties:
                if str(prop.value).startswith("http"):
                    g.add((c, URIRef(prop.uri), URIRef(prop.value)))
                else:
                    g.add((c, URIRef(prop.uri), Literal(prop.value)))

        # serialise in the appropriate RDF format
        if self.mediatype in ["application/rdf+json", "application/json"]:
            graph_text = g.serialize(format="json-ld")
        else:
            graph_text = g.serialize(format=self.mediatype)

        return Response(
            graph_text,
            mimetype=self.mediatype,
            headers=self.headers,
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
        # # TODO: vocab_uri, uri, semantic_properties
        #
        # # serialise in the appropriate RDF format
        # if self.mediatype in ['application/rdf+json', 'application/json']:
        #     return Response(g.serialize(format='json-ld'), mimetype=self.mediatype)
        # else:
        #     return Response(g.serialize(format=self.mediatype), mimetype=self.mediatype)

    def _render_skos_html(self):
        _template_context = {
            "version": __version__,
            "vocab_uri": self.concept.vocab_uri if self.concept.vocab_uri is not None else self.request.values.get("vocab_uri"),
            "vocab_title": g.VOCABS[self.concept.vocab_uri].title,
            "uri": self.request.values.get("uri"),
            "concept": self.concept,
        }

        return Response(
            render_template("concept.html", **_template_context), headers=self.headers
        )
