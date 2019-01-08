from pyldapi import Renderer, View
from flask import Response, render_template, url_for
from rdflib import Graph


class Vocabulary:
    def __init__(
            self,
            id,
            uri,            # DCAT
            title,          # DCAT
            description,    # DCAT
            creator,        # DCAT
            created,        # DCAT
            modified,       # DCAT
            versionInfo,
            hasTopConcepts=None,
            conceptHierarchy=None,
            accessURL=None,
            downloadURL=None
    ):
        self.id = id
        self.uri = uri
        self.title = title
        self.description = description
        self.creator = creator
        self.created = created
        self.modified = modified
        self.versionInfo = versionInfo
        self.hasTopConcepts = hasTopConcepts
        self.conceptHierarchy = conceptHierarchy
        self.accessURL = accessURL
        self.downloadURL = downloadURL


class VocabularyRenderer(Renderer):
    def __init__(self, request, vocab):
        self.views = self._add_dcat_view()
        self.navs = [
            # '<a href="' + url_for('routes.vocabulary', vocab_id=vocab.id) + '/collection/">Collections</a> |',
            # '<a href="' + url_for('routes.vocabulary', vocab_id=vocab.id) + '/concept/">Concepts</a> |'
        ]

        self.vocab = vocab

        super().__init__(
            request,
            self.vocab.uri,
            self.views,
            'dcat'
        )

    def _add_dcat_view(self):
        return {
            'dcat': View(
                'Dataset Catalogue Vocabulary (DCAT)',
                'DCAT is an RDF vocabulary designed to facilitate interoperability between data catalogs published on '
                'the Web.',
                ['text/html', 'application/json'] + self.RDF_MIMETYPES,
                'text/html',
                languages=['en'],  # default 'en' only for now
                namespace='http://www.w3.org/ns/dcat#'
            )
        }

    def render(self):
        if self.view == 'alternates':
            return self._render_alternates_view()
        elif self.view == 'dcat':
            if self.format in Renderer.RDF_MIMETYPES:
                return self._render_dcat_rdf()
            else:
                return self._render_dcat_html()

    def _render_dcat_rdf(self):
        # get vocab RDF
        import data.source_rva as rva
        v = rva.RVA()._get_resource_rdf(self.vocab_id, self.uri)
        g = Graph().load(v, format='turtle')

        # serialise in the appropriate RDF format
        if self.format in ['application/rdf+json', 'application/json']:
            return g.serialize(format='json-ld')
        else:
            return g.serialize(format=self.format)

    def _render_dcat_html(self):
        _template_context = {
            'uri': self.uri,
            'vocab': self.vocab,
            'navs': self.navs
        }

        return Response(
            render_template(
                'vocabulary.html',
                **_template_context
            ),
            headers=self.headers
        )
