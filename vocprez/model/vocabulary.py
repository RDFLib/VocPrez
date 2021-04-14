from vocprez import __version__
from pyldapi import Renderer
from flask import Response, render_template
from rdflib import Graph, URIRef, Literal, XSD, RDF
from rdflib.namespace import DCTERMS, OWL, SKOS, Namespace, NamespaceManager
from vocprez.model.profiles import profile_skos, profile_dcat, profile_dd
from typing import List
from vocprez.model.property import Property
import json as j
from vocprez._config import *


class Vocabulary:
    def __init__(
        self,
        id,
        uri,
        title,
        description,
        creator,
        created,
        modified,
        versionInfo,
        source,
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
        other_properties: List[Property] = None
    ):
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
        self.source = source
        if hasTopConcept:
            hasTopConcept.sort()
        self.hasTopConcepts = hasTopConcept
        self.concepts = concepts
        self.conceptHierarchy = concept_hierarchy
        self.collections = collections
        self.accessURL = accessURL
        self.downloadURL = downloadURL
        self.sparql_endpoint = sparql_endpoint
        self.collection_uris = collection_uris
        self.sparql_username = sparql_username
        self.sparql_password = sparql_password

        self.other_properties = other_properties


class VocabularyRenderer(Renderer):
    def __init__(self, request, vocab, language="en"):
        self.profiles = {"dcat": profile_dcat}
        self.profiles.update({"skos": profile_skos})
        self.profiles.update({"dd": profile_dd})
        self.vocab = vocab
        self.uri = self.vocab.uri
        self.language = language

        super().__init__(request, self.vocab.uri, self.profiles, "skos")

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
            else:
                return self._render_dcat_html()  # same as DCAT, for now
        elif self.profile == "dd":
            return self._render_dd_json()

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
        if self.vocab.accessURL:
            g.add((s, DCAT.accessURL, URIRef(self.vocab.accessURL)))
        if self.vocab.downloadURL:
            g.add((s, DCAT.downloadURL, URIRef(self.vocab.downloadURL)))

        sp = URIRef(SYSTEM_URI_BASE + "/sparql")
        g.add((sp, DCAT.servesDataset, s))
        g.add((sp, DCTERMS.title, Literal("VocPrez SPARQL Service")))
        api = URIRef(SYSTEM_URI_BASE)
        g.add((api, DCAT.servesDataset, s))
        g.add((api, DCTERMS.title, Literal("VocPrez Linked Data API")))

        if self.vocab.other_properties is not None:
            for prop in self.vocab.other_properties:
                # other properties from DCAT, DCTERMS only
                if str(prop.uri).startswith(("https://www.w3.org/ns/dcat#", "http://purl.org/dc/terms/")):
                    g.add((s, URIRef(prop.uri), prop.value))

        # serialise in the appropriate RDF format
        if self.mediatype in ["application/rdf+json", "application/json"]:
            return Response(g.serialize(format="json-ld"), mimetype=self.mediatype, headers=self.headers)
        else:
            return Response(g.serialize(format=self.mediatype), mimetype=self.mediatype, headers=self.headers)

    def _render_skos_rdf(self):
        g = Graph()
        g.bind("skos", SKOS)
        s = URIRef(self.vocab.uri)
        g.add((s, RDF.type, SKOS.ConceptScheme))
        g.add((s, SKOS.prefLabel, Literal(self.vocab.title)))
        g.add((s, SKOS.definition, Literal(self.vocab.description)))
        # if self.vocab.hasTopConcept:
        #     for c in self.vocab.hasTopConcept:
        #         g.add((s, SKOS.hasTopConcept, URIRef(c[0])))
        #         g.add((URIRef(c[0]), SKOS.prefLabel, Literal(c[1])))
        if self.vocab.concepts:
            for c in self.vocab.concepts:
                g.add((s, SKOS.inScheme, URIRef(c[0])))
                g.add((URIRef(c[0]), SKOS.prefLabel, Literal(c[1])))

        # serialise in the appropriate RDF format
        if self.mediatype in ["application/rdf+json", "application/json"]:
            return Response(g.serialize(format="json-ld"), mimetype=self.mediatype, headers=self.headers)
        else:
            return Response(g.serialize(format=self.mediatype), mimetype=self.mediatype, headers=self.headers)

    def _render_dcat_html(self):
        _template_context = {
            "version": __version__,
            "uri": self.uri,
            "vocab": self.vocab,
            "title": self.vocab.title,
        }

        return Response(
            render_template("vocabulary.html", **_template_context),
            headers=self.headers,
        )

    def _render_dd_json(self):
        concepts = []
        if self.vocab.concepts:
            for c in self.vocab.concepts:
                concepts.append({
                    "uri": c[0],
                    "prefLabel": c[1],
                    "broader": c[2],
                })
        return Response(j.dumps(concepts), mimetype="application/json", headers=self.headers)
