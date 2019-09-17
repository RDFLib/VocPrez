from pyldapi import Renderer, View
from flask import Response, render_template, url_for
from rdflib import Graph, URIRef, Literal, XSD, RDF
from rdflib.namespace import DCTERMS, OWL, SKOS, Namespace, NamespaceManager
import _config as config

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
            data_source,
            concept_scheme_uri,
            hasTopConcept=None,
            concept_hierarchy=None,
            accessURL=None,
            downloadURL=None,
            sparql_endpoint=None,
            collection_uris=None,
            sparql_username=None,
            sparql_password=None
    ):
        self.source = None
        self.id = id
        self.uri = uri
        self.title = title
        self.description = description
        self.creator = creator
        try:
            self.created = created
        except:
            self.created = created
        try:
            self.modified = modified
        except:
            self.modified = modified
        self.versionInfo = versionInfo
        self.data_source = data_source
        self.concept_scheme_uri = concept_scheme_uri
        if hasTopConcept:
            hasTopConcept.sort()
        self.hasTopConcepts = hasTopConcept
        self.conceptHierarchy = concept_hierarchy
        self.accessURL = accessURL
        self.downloadURL = downloadURL
        self.sparql_endpoint = sparql_endpoint
        self.collection_uris = collection_uris
        self.sparql_username = sparql_username
        self.sparql_password = sparql_password


class VocabularyRenderer(Renderer):
    def __init__(self, request, vocab, language='en'):
        self.views = self._add_dcat_view()
        self.views.update(self._add_skos_view())
        self.navs = [
            # '<a href="' + url_for('routes.vocabulary', vocab_id=vocab.id) + '/collection/">Collections</a> |',
            '<a href="' + url_for('routes.vocabulary', vocab_id=vocab.id) + '/concept/">Concepts</a> |'
        ]

        self.vocab = vocab
        self.language = language

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

    def _add_skos_view(self):
        return {
            'skos': View(
                'Simple Knowledge Organization System (SKOS)',
                'SKOS provides a standard way to represent knowledge organization systems using the Resource Description Framework (RDF). '
                'Encoding this information in RDF allows it to be passed between computer applications in an interoperable way.',
                ['text/html', 'application/json'] + self.RDF_MIMETYPES,
                'text/html',
                languages=['en'],  # default 'en' only for now
                namespace='http://www.w3.org/2004/02/skos/core#'
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
        elif self.view == 'skos':
            if self.format in Renderer.RDF_SERIALIZER_MAP:
                return self._render_skos_rdf()
            #===================================================================
            # else:
            #     return self._render_skos_html()
            #===================================================================

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
        VOID = Namespace('http://rdfs.org/ns/void')
        g.namespace_manager.bind('void', VOID)
        s = URIRef(self.vocab.uri)
 
        g.add((s, RDF.type, DCAT.Dataset))
        if self.vocab.title:
            g.add((s, DCTERMS.title, Literal(self.vocab.title)))
        if self.vocab.description:
            g.add((s, DCTERMS.description, Literal(self.vocab.description)))
        if self.vocab.creator:
            if self.vocab.creator[:7] == 'http://' or self.vocab.creator[:7] == 'https://': # if url
                g.add((s, DCTERMS.creator, URIRef(self.vocab.creator)))
            else:  # else literal
                g.add((s, DCTERMS.creator, Literal(self.vocab.creator)))
        if self.vocab.created:
            g.add((s, DCTERMS.created, Literal(self.vocab.created, datatype=XSD.date)))
        if self.vocab.modified:
            g.add((s, DCTERMS.modified, Literal(self.vocab.modified, datatype=XSD.date)))
        if self.vocab.versionInfo:
            g.add((s, OWL.versionInfo, Literal(self.vocab.versionInfo)))
        if self.vocab.hasTopConcepts:
            for c in self.vocab.hasTopConcepts:
                g.add((s, SKOS.hasTopConcept, URIRef(c[0])))
                g.add((URIRef(c[0]), SKOS.prefLabel, Literal(c[1])))
        if self.vocab.accessURL:
            g.add((s, DCAT.accessURL, URIRef(self.vocab.accessURL)))
        if self.vocab.downloadURL:
            g.add((s, DCAT.downloadURL, URIRef(self.vocab.downloadURL)))
        if self.vocab.sparql_endpoint:
            g.add((s, VOID.sparqlEndpoint, URIRef(self.vocab.sparql_endpoint)))

        # serialise in the appropriate RDF format
        if self.format in ['application/rdf+json', 'application/json']:
            return Response(g.serialize(format='json-ld'), mimetype=self.format)
        else:
            return Response(g.serialize(format=self.format), mimetype=self.format)

    def _render_skos_rdf(self):
        # get vocab RDF
        g = self.vocab.source.graph

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
            'title': 'Voc: ' + self.vocab.title,
            'config': config
        }

        return Response(
            render_template(
                'vocabulary.html',
                **_template_context
            ),
            headers=self.headers
        )
