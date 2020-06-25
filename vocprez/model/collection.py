from vocprez import __version__
from pyldapi import Renderer
from flask import Response, render_template, g
from rdflib import Graph
from vocprez.model.profiles import profile_skos


class Collection:
    def __init__(
        self, vocab, uri, prefLabel, definition, members,
    ):
        self.vocab = vocab
        self.uri = uri
        self.prefLabel = prefLabel
        self.definition = definition
        self.members = members


class CollectionRenderer(Renderer):
    def __init__(self, request, collection, vocab_uri=None):
        self.profiles = self._add_skos_profile()
        self.vocab_uri = vocab_uri
        self.collection = collection

        super().__init__(request, self.collection.uri, self.profiles, "skos")

    def _add_skos_profile(self):
        return {"skos": profile_skos}

    def render(self):
        # try returning alt profile
        response = super().render()
        if response is not None:
            return response
        elif self.profile == "skos":
            if self.mediatype in Renderer.RDF_MEDIA_TYPES:
                return self._render_skos_rdf()
            else:
                return self._render_skos_html()

    def _render_skos_rdf(self):
        # get Collection RDF
        # TODO: re-assemble RDF from Concept object
        g = Graph()

        # serialise in the appropriate RDF format
        if self.mediatype in ["application/rdf+json", "application/json"]:
            return g.serialize(format="json-ld")
        else:
            return g.serialize(format=self.mediatype)

    def _render_skos_html(self):
        _template_context = {
            "version": __version__,
            "vocab_id": self.vocab_uri if self.vocab_uri is not None else self.request.values.get("vocab_uri"),
            "vocab_title": g.VOCABS[self.vocab_uri].title,
            "uri": self.instance_uri,
            "collection": self.collection,
        }

        return Response(
            render_template("collection.html", **_template_context),
            headers=self.headers,
        )
