from pyldapi import Renderer, View
from flask import Response, render_template
from rdflib import Graph


class VocabularyRenderer(Renderer):
    def __init__(self, request, navs, vocab_id):
        self.navs = navs

        self.views = self._add_dcat_view()

        import model.sources_rva as rva
        self.vocab_metadata = rva.RVA().get_vocabulary(vocab_id)

        super().__init__(
            request,
            vocab_id,
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
        """
        Renders the register view.

        :return: A Flask Response object.
        :rtype: :py:class:`flask.Response`
        """
        #response = super(Renderer, self).render()  # render Alternates view, if selected
        #if not response:
        if self.view == 'alternates':
            return self._render_alternates_view()
        if self.view == 'dcat':
            if self.format in Renderer.RDF_MIMETYPES:
                return self._render_dcat_rdf()
            else:
                return self._render_dcat_html()

        #return response  # returning from parent (Alternates View only)

    def _render_dcat_rdf(self):
        # read vocab RDF from SPARQL endpoint
        v = '''
        @prefix dcat: <http://www.w3.org/ns/dcat#> .
        @prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix owl:  <http://www.w3.org/2002/07/owl#> .
        @prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
        @prefix skos: <http://www.w3.org/2004/02/skos/core#> .
        @prefix dct:  <http://purl.org/dc/terms/> .
        @prefix dc:   <http://purl.org/dc/elements/1.1/> .
        @prefix : <http://linked.data.gov.au/def/reg-status/> .
        
        
        <http://linked.data.gov.au/def/reg-status> a dcat:Dataset ;
            dct:title "Test Vocabulary"@en ;
            dct:description """This vocabulary is a test vocabulary used just to show off vocabulary managment tools.
        
            This vocabulary is a a SKOS vocabulary implemented as a single skos:ConceptScheme, also an OWL Ontology and also a DCAT Dataset."""@en ;
            dct:publisher <http://linked.data.qld.gov.au/org/gsq> ;
            dc:publisher "Geological Survey of Queensland"@en ;
            dct:creator <https://orcid.org/0000-0002-8742-7730> ;
            dc:creator "Nicholas Car"@en ;                        
            dct:created "2018-11-20"^^xsd:date ;
            dct:modified "2018-11-20"@en ;
            dct:rights "(c) Commonwealth of Australia (State of Queensland) 2018"@en ;            
        .
        '''
        g = Graph().load(v, format='turtle')

        # serialise in the appropriate RDF format
        if self.format in ['application/rdf+json', 'application/json']:
            return g.serialize(format='json-ld')
        else:
            return g.serialize(format=self.format)

    def _render_dcat_html(self):
        _template_context = {
            'uri': self.uri,
            'title': 'Test Vocabulary',
            'description': """This vocabulary is a test vocabulary used just to show off vocabulary managment tools.
        
            This vocabulary is a a SKOS vocabulary implemented as a single skos:ConceptScheme, also an OWL Ontology and also a DCAT Dataset.""",
            'publisher_uri': 'http://linked.data.qld.gov.au/org/gsq',
            'publisher_label': 'Geological Survey of Queensland',
            'creator_uri': 'https://orcid.org/0000-0002-8742-7730',
            'creator_label': 'Nicholas Car',
            'created': '2018-11-20',
            'modified': '2018-11-20',
            'rights': '(c) Commonwealth of Australia (State of Queensland) 2018',
            'navs': self.navs
        }

        return Response(
            render_template(
                'vocabulary.html',
                **_template_context
            ),
            headers=self.headers
        )