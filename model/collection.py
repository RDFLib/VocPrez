from pyldapi import Renderer, Profile
from flask import Response, render_template
from rdflib import Graph


class Collection:
    def __init__(
            self,
            vocab,
            uri,
            label,
            comment,
            members,
    ):
        self.vocab = vocab
        self.uri = uri
        self.label = label
        self.comment = comment
        self.members = members


class CollectionRenderer(Renderer):
    def __init__(self, request, collection):
        self.profiles = self._add_skos_view()
        self.navs = []  # TODO: add in other nav items for Collection

        self.collection = collection

        super().__init__(
            request,
            self.collection.uri,
            self.profiles,
            'skos'
        )

    def _add_skos_view(self):
        return {
            'skos': View(
                'Simple Knowledge Organization System (SKOS)',
                'SKOS is a W3C recommendation designed for representation of thesauri, classification schemes, '
                'taxonomies, subject-heading systems, or any other type of structured controlled vocabulary.',
                ['text/html', 'application/json'] + self.RDF_MEDIA_TYPES,
                'text/html',
                languages=['en'],  # default 'en' only for now
                namespace='http://www.w3.org/2004/02/skos/core#'
            )
        }

    def render(self):
        # try returning alt profile
        response = super().render()
        if response is not None:
            return response
        elif self.profile == 'skos':
            if self.mediatype in Renderer.RDF_MEDIA_TYPES:
                return self._render_skos_rdf()
            else:
                return self._render_skos_html()

    def _render_skos_rdf(self):
        # get Collection RDF
        # TODO: re-assemble RDF from Concept object
        g = Graph()

        # serialise in the appropriate RDF format
        if self.mediatype in ['application/rdf+json', 'application/json']:
            return g.serialize(format='json-ld')
        else:
            return g.serialize(format=self.mediatype)

    def _render_skos_html(self):
        _template_context = {
            'uri': self.instance_uri,
            'collection': self.collection,
            'navs': self.navs
        }

        return Response(
            render_template(
                'collection.html',
                **_template_context
            ),
            headers=self.headers
        )
