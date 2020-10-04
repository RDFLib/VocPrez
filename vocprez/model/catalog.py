from vocprez import __version__
from pyldapi import Renderer
import vocprez._config as config
from flask import Response, render_template
from typing import List
from vocprez.model.property import Property
from vocprez.model.profiles import profile_dcat, profile_void  # , profile_ckan
from rdflib import Graph, URIRef, Literal, XSD, RDF
from rdflib.namespace import DCAT, DCTERMS, OWL, SKOS, VOID


class DataService:
    def __init__(
        self,
        title,
        description,
        access_uri
    ):
        self.title = title
        self.description = description
        self.access_uri = access_uri


class Catalog:
    def __init__(
        self,
        uri,
        title,
        description,
        creator,
        publisher,
        contributors,
        created,
        modified,
        versionInfo,
        source,
        sparql_endpoint,
        datasets,
        other_properties: List[Property] = None
    ):
        self.uri = uri
        self.title = title
        self.description = description
        self.creator = creator
        self.publisher = publisher
        self.contributors = contributors
        self.created = created
        self.modified = modified
        self.versionInfo = versionInfo
        self.source = source
        self.sparql_endpoint = sparql_endpoint
        self.datasets = datasets

        self.other_properties = other_properties

        # make know Distributions here
        self.distributions = DataService(
            "VocPrez Linked Data API",
            "These vocabularies available via a Linked Data API",
            "http://localhost:5000/vocab/"
        )


class CatalogRenderer(Renderer):
    def __init__(self, request, datasets):
        self.profiles = {"dcat": profile_dcat}
        self.profiles.update({"void": profile_void})
        self.catalog = Catalog(
            config.VOCS_URI,
            config.VOCS_TITLE,
            config.VOCS_DESC,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            config.SPARQL_ENDPOINT,
            datasets
        )

        super().__init__(request, self.catalog.uri, self.profiles, "dcat")

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
        elif self.profile == "void":
            return self._render_void_rdf()

    def _render_dcat_rdf(self):
        g = Graph()
        g.bind("dcat", DCAT)
        g.bind("dct", DCTERMS)
        g.bind("owl", OWL)
        g.bind("skos", SKOS)
        g.bind("skos", SKOS)
        g.bind("void", VOID)
        s = URIRef(self.dataset.uri)

        g.add((s, RDF.type, DCAT.Catalog))
        if self.dataset.title:
            g.add((s, DCTERMS.title, Literal(self.dataset.title)))
        if self.dataset.description:
            g.add((s, DCTERMS.description, Literal(self.dataset.description)))
        if self.dataset.creator:
            if (
                self.dataset.creator[:7] == "http://"
                or self.dataset.creator[:7] == "https://"
            ):  # if url
                g.add((s, DCTERMS.creator, URIRef(self.dataset.creator)))
            else:  # else literal
                g.add((s, DCTERMS.creator, Literal(self.dataset.creator)))
        if self.dataset.created:
            g.add((s, DCTERMS.created, Literal(self.dataset.created, datatype=XSD.date)))
        if self.dataset.modified:
            g.add(
                (s, DCTERMS.modified, Literal(self.dataset.modified, datatype=XSD.date))
            )
        if self.dataset.versionInfo:
            g.add((s, OWL.versionInfo, Literal(self.dataset.versionInfo)))
        # if self.dataset.accessURL:
        #     g.add((s, DCAT.accessURL, URIRef(self.dataset.accessURL)))
        # if self.dataset.downloadURL:
        #     g.add((s, DCAT.downloadURL, URIRef(self.dataset.downloadURL)))
            
        # TODO: make this into a DataService Distribution
        if self.dataset.sparql_endpoint:
            g.add((s, VOID.sparqlEndpoint, URIRef(self.dataset.sparql_endpoint)))

        for part in self.parts:
            g.add((s, DCAT.dataset, URIRef(part[0])))

        if self.dataset.other_properties is not None:
            for prop in self.dataset.other_properties:
                g.add((s, URIRef(prop.uri), prop.value))

        # serialise in the appropriate RDF format
        if self.mediatype in ["application/rdf+json", "application/json"]:
            return Response(g.serialize(format="json-ld"), mimetype=self.mediatype)
        else:
            return Response(g.serialize(format=self.mediatype), mimetype=self.mediatype)
        
    def _render_dcat_html(self):
        _template_context = {
            "version": __version__,
            "catalog": self.catalog
        }

        return Response(
            render_template("catalog.html", **_template_context),
            headers=self.headers,
        )

    def _render_void_rdf(self):
        g = Graph()
        g.bind("dcat", DCAT)
        g.bind("dct", DCTERMS)
        g.bind("owl", OWL)
        g.bind("skos", SKOS)
        g.bind("void", VOID)
        s = URIRef(self.dataset.uri)
        
        if self.dataset.sparql_endpoint:
            g.add((s, VOID.sparqlEndpoint, URIRef(self.dataset.sparql_endpoint)))

        # serialise in the appropriate RDF format
        if self.mediatype in ["application/rdf+json", "application/json"]:
            return Response(g.serialize(format="json-ld"), mimetype=self.mediatype)
        else:
            return Response(g.serialize(format=self.mediatype), mimetype=self.mediatype)
