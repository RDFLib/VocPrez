from pyldapi import Renderer, View
from flask import Response, render_template, url_for
from rdflib import Graph, URIRef, Literal, XSD, RDF
from rdflib.namespace import DCTERMS, OWL, SKOS, Namespace, NamespaceManager


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
        if hasTopConcepts:
            hasTopConcepts.sort()
        self.hasTopConcepts = hasTopConcepts
        self.conceptHierarchy = conceptHierarchy
        self.accessURL = accessURL
        self.downloadURL = downloadURL


class VocabularyRenderer(Renderer):
    def __init__(self, request, vocab):
        self.views = self._add_dcat_view()
        self.navs = [
            # '<a href="' + url_for('routes.vocabulary', vocab_id=vocab.id) + '/collection/">Collections</a> |',
            '<a href="' + url_for('routes.vocabulary', vocab_id=vocab.id) + '/concept/">Concepts</a> |'
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
            if self.format == 'text/html':
                return self._render_alternates_view_html({'title': 'Alternates View of ' + self.vocab.title, 'name': self.vocab.title})
            return self._render_alternates_view()
        elif self.view == 'dcat':
            if self.format in Renderer.RDF_SERIALIZER_MAP:
                return self._render_dcat_rdf()
            else:
                return self._render_dcat_html()

    def _render_dcat_rdf(self):
        # get vocab RDF
        g = Graph()
        # map nice prefixes to namespaces
        NamespaceManager(g)
        DCAT = Namespace('https://www.w3.org/ns/dcat#')
        g.namespace_manager.bind('dcat', DCAT)
        g.namespace_manager.bind('dct', DCTERMS)
        g.namespace_manager.bind('owl', OWL)
        g.namespace_manager.bind('skos', SKOS)
        s = URIRef(self.vocab.uri)

        g.add((s, RDF.type, DCAT.Dataset))
        if self.vocab.title:
            g.add((s, DCTERMS.title, Literal(self.vocab.title, datatype=XSD.string)))
        if self.vocab.description:
            g.add((s, DCTERMS.description, Literal(self.vocab.description, datatype=XSD.string)))
        if self.vocab.creator:
            if self.vocab.creator[:7] == 'http://' or self.vocab.creator[:7] == 'https://': # if url
                g.add((s, DCTERMS.creator, URIRef(self.vocab.creator)))
            else: # else literal
                g.add((s, DCTERMS.creator, Literal(self.vocab.creator, datatype=XSD.string)))
        if self.vocab.created:
            g.add((s, DCTERMS.created, Literal(self.vocab.created, datatype=XSD.date)))
        if self.vocab.modified:
            g.add((s, DCTERMS.modified, Literal(self.vocab.modified, datatype=XSD.date)))
        if self.vocab.versionInfo:
            g.add((s, OWL.versionInfo, Literal(self.vocab.versionInfo, datatype=XSD.string)))
        if self.vocab.hasTopConcepts:
            for c in self.vocab.hasTopConcepts:
                g.add((s, SKOS.hasTopConcept, URIRef(c[0])))
                g.add((URIRef(c[0]), SKOS.prefLabel, Literal(c[1], datatype=XSD.string)))
        if self.vocab.accessURL:
            g.add((s, DCAT.accessURL, URIRef(self.vocab.accessURL)))
        if self.vocab.downloadURL:
            g.add((s, DCAT.downloadURL, URIRef(self.vocab.downloadURL)))

        # serialise in the appropriate RDF format
        if self.format in ['application/rdf+json', 'application/json']:
            return Response(g.serialize(format='json-ld'), mimetype=self.format)
        else:
            return Response(g.serialize(format=self.format), mimetype=self.format)

    def _render_dcat_html(self):
        _template_context = {
            'uri': self.uri,
            'vocab': self.vocab,
            'navs': self.navs,
            'title': 'Voc: ' + self.vocab.title
        }

        return Response(
            render_template(
                'vocabulary.html',
                **_template_context
            ),
            headers=self.headers
        )
