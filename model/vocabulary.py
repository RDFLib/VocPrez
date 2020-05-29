from pyldapi import Renderer, Profile
from flask import Response, render_template, url_for
from rdflib import Graph, URIRef, Literal, XSD, RDF
from rdflib.namespace import DCTERMS, OWL, SKOS, Namespace, NamespaceManager
import _config as config
from model.profiles import profile_skos, profile_dcat


class Vocabulary:
    def __init__(
        self,
        id,
        uri,  # DCAT
        title,  # DCAT
        description,  # DCAT
        creator,  # DCAT
        created,  # DCAT
        modified,  # DCAT
        versionInfo,
        data_source,
        concept_scheme_uri,
        hasTopConcept=None,
        concepts=None,
        concept_hierarchy=None,
        collections=None,
        accessURL=None,
        downloadURL=None,
        sparql_endpoint=None,
        collection_uris=None,
        sparql_username=None,
        sparql_password=None,
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
        self.concepts = concepts
        self.conceptHierarchy = concept_hierarchy
        self.collection = collections
        self.accessURL = accessURL
        self.downloadURL = downloadURL
        self.sparql_endpoint = sparql_endpoint
        self.collection_uris = collection_uris
        self.sparql_username = sparql_username
        self.sparql_password = sparql_password


class VocabularyRenderer(Renderer):
    def __init__(self, request, vocab, language="en"):
        self.profiles = {"dcat": profile_dcat}
        self.profiles.update({"skos": profile_skos})
        self.vocab = vocab
        # self.navs = [
        #     # '<a href="' + url_for('routes.vocabulary', vocab_id=vocab.id) + '/collection/">Collections</a> |',
        #     '<a href="'
        #     + url_for("routes.conceptscheme", vocab_id=vocab.id)
        #     + '/concept/">Concepts</a> |'
        # ]
        self.uri = self.vocab.uri
        self.language = language

        super().__init__(request, self.vocab.uri, self.profiles, "dcat")

    def render(self):
        # try returning alt profile
        response = super().render()
        if response is not None:
            return response
        elif self.profile == "dcat":
            if self.mediatype in Renderer.RDF_SERIALIZER_TYPES_MAP:
                return self._render_dcat_rdf()
            else:
                return self._render_dcat_html()
        elif self.profile == "skos":
            if self.mediatype in Renderer.RDF_SERIALIZER_TYPES_MAP:
                return self._render_skos_rdf()
            # ===================================================================
            # else:
            #     return self._render_skos_html()
            # ===================================================================

    def _render_dcat_rdf(self):
        # get vocab RDF
        g = Graph()
        # map nice prefixes to namespaces
        NamespaceManager(g)
        DCAT = Namespace("https://www.w3.org/ns/dcat#")
        g.namespace_manager.bind("dcat", DCAT)
        g.namespace_manager.bind("dct", DCTERMS)
        g.namespace_manager.bind("owl", OWL)
        g.namespace_manager.bind("skos", SKOS)
        VOID = Namespace("http://rdfs.org/ns/void")
        g.namespace_manager.bind("void", VOID)
        s = URIRef(self.vocab.uri)

        g.add((s, RDF.type, DCAT.Dataset))
        if self.vocab.title:
            g.add((s, DCTERMS.title, Literal(self.vocab.title)))
        if self.vocab.description:
            g.add((s, DCTERMS.description, Literal(self.vocab.description)))
        if self.vocab.creator:
            if (
                self.vocab.creator[:7] == "http://"
                or self.vocab.creator[:7] == "https://"
            ):  # if url
                g.add((s, DCTERMS.creator, URIRef(self.vocab.creator)))
            else:  # else literal
                g.add((s, DCTERMS.creator, Literal(self.vocab.creator)))
        if self.vocab.created:
            g.add((s, DCTERMS.created, Literal(self.vocab.created, datatype=XSD.date)))
        if self.vocab.modified:
            g.add(
                (s, DCTERMS.modified, Literal(self.vocab.modified, datatype=XSD.date))
            )
        if self.vocab.versionInfo:
            g.add((s, OWL.versionInfo, Literal(self.vocab.versionInfo)))
        if self.vocab.hasTopConcept:
            for c in self.vocab.hasTopConcept:
                g.add((s, SKOS.hasTopConcept, URIRef(c[0])))
                g.add((URIRef(c[0]), SKOS.prefLabel, Literal(c[1])))
        if self.vocab.accessURL:
            g.add((s, DCAT.accessURL, URIRef(self.vocab.accessURL)))
        if self.vocab.downloadURL:
            g.add((s, DCAT.downloadURL, URIRef(self.vocab.downloadURL)))
        if self.vocab.sparql_endpoint:
            g.add((s, VOID.sparqlEndpoint, URIRef(self.vocab.sparql_endpoint)))

        # serialise in the appropriate RDF format
        if self.mediatype in ["application/rdf+json", "application/json"]:
            return Response(g.serialize(format="json-ld"), mimetype=self.mediatype)
        else:
            return Response(g.serialize(format=self.mediatype), mimetype=self.mediatype)

    def _render_skos_rdf(self):
        g = Graph()
        g.bind("skos", SKOS)
        s = URIRef(self.vocab.uri)
        g.add((s, RDF.type, SKOS.ConceptScheme))
        g.add((s, SKOS.prefLabel, Literal(self.vocab.title)))
        g.add((s, SKOS.definition, Literal(self.vocab.description)))
        if self.vocab.hasTopConcept:
            for c in self.vocab.hasTopConcept:
                g.add((s, SKOS.hasTopConcept, URIRef(c[0])))
                g.add((URIRef(c[0]), SKOS.prefLabel, Literal(c[1])))
        if self.vocab.concepts:
            for c in self.vocab.concepts:
                g.add((s, SKOS.inScheme, URIRef(c[0])))
                g.add((URIRef(c[0]), SKOS.prefLabel, Literal(c[1])))

        # serialise in the appropriate RDF format
        if self.mediatype in ["application/rdf+json", "application/json"]:
            return Response(g.serialize(format="json-ld"), mimetype=self.mediatype)
        else:
            return Response(g.serialize(format=self.mediatype), mimetype=self.mediatype)

    def _render_dcat_html(self):
        _template_context = {
            "uri": self.uri,
            "vocab": self.vocab,
            # "navs": self.navs,
            "title": "Voc: " + self.vocab.title,
            "config": config,
        }

        return Response(
            render_template("vocabulary.html", **_template_context),
            headers=self.headers,
        )
