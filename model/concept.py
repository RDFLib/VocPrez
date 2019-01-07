from pyldapi import Renderer, View
from flask import Response, render_template, url_for
import _config as config
from rdflib import Graph
import data.source_selector as sel


class Concept:
    def __init__(
            self,
            vocab_id,
            uri,
            prefLabel,
            definition,
            altLabels,
            hiddenLabels,
            source,
            contributor,
            broaders,
            narrowers,
            semantic_properties
    ):
        self.vocab_id = vocab_id
        self.uri = uri
        self.prefLabel = prefLabel
        self.definition = definition
        self.altLabels = altLabels
        self.hiddenLabels = hiddenLabels
        self.source = source
        self.contributor = contributor
        self.broaders = broaders
        self.narrowers = narrowers
        self.semantic_properties = semantic_properties


class ConceptRenderer(Renderer):
    def __init__(self, request, concept):
        self.request = request
        self.views = self._add_views()
        self.navs = []  # TODO: add in other nav items for Concept

        self.concept = concept

        super().__init__(
            self.request,
            self.concept.uri,
            self.views,
            'skos'
        )

    def _add_views(self):
        return {
            'skos': View(
                'Simple Knowledge Organization System (SKOS)',
                'SKOS is a W3C recommendation designed for representation of thesauri, classification schemes, '
                'taxonomies, subject-heading systems, or any other type of structured controlled vocabulary.',
                ['text/html', 'application/json'] + self.RDF_MIMETYPES,
                'text/html',
                languages=['en'],  # default 'en' only for now
                namespace='http://www.w3.org/2004/02/skos/core#'
            ),
            'ckan': View(
                'Comprehensive Knowledge Archive Network',
                'The Comprehensive Knowledge Archive Network (CKAN) is a web-based open-source management system for '
                'the storage and distribution of open data.',
                ['text/html', 'application/json'] + self.RDF_MIMETYPES,
                'text/html',
                languages=['en'],
                namespace='https://ckan.org/'
            )
        }

    def render(self):
        if self.view == 'alternates':
            return self._render_alternates_view()
        elif self.view == 'skos':
            if self.format in Renderer.RDF_MIMETYPES:
                return self._render_skos_rdf()
            else:
                return self._render_skos_html()

    def _render_skos_rdf(self):
        # get Concept RDF
        import data.source_selector as sel
        rdf = sel.get_concept_rdf(self.request.values.get('vocab_id'), self.request.values.get('uri'))

        # serialise in the appropriate RDF format
        if self.format in ['application/rdf+json', 'application/json']:
            return g.serialize(format='json-ld')
        else:
            return g.serialize(format=self.format)

    def _render_skos_html(self):
        _template_context = {
            'vocab_id': self.request.values.get('vocab_id'),
            'vocab_title': config.VOCABS[self.request.values.get('vocab_id')].get('title'),
            'uri': self.request.values.get('uri'),
            'concept': self.concept,
            'navs': self.navs
        }

        return Response(
            render_template(
                'concept.html',
                **_template_context
            ),
            headers=self.headers
        )

    def _render_alternates_view(self):
        super().__init__(
            self.request,
            url_for('routes.object') + '?vocab_uri=' + self.concept.vocab.id,
            self.views,
            self.default_view_token
        )
