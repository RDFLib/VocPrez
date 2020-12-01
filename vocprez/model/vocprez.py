from pyldapi import Renderer
from vocprez.model.profiles import profile_dcat, profile_sdo
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import DCAT, DCTERMS, SDO, RDF
from flask import Response, render_template


class VocPrez:
    def __init__(self, system_uri, vocs_uri, vocs_title, vocs_desc, g_vocabs):
        self.uri = system_uri
        self.vocs_uri = vocs_uri
        self.vocs_title = vocs_title
        self.vocs_desc = vocs_desc
        self.vocabs = g_vocabs

    def to_sdo_rdf(self):
        # gets only schema.org RDF from the cache
        g = Graph()
        g.bind("sdo", SDO)
        vs = URIRef(self.vocs_uri)
        g.add((vs, RDF.type, SDO.Dataset))
        g.add((vs, SDO.name, Literal(self.vocs_title)))
        g.add((vs, SDO.description, Literal(self.vocs_desc)))
        # for v in self.vocabs.values():
        #     g.add((vs, SDO.item, URIRef(v.uri)))
        #     g.add((URIRef(v.uri), RDF.type, SDO.Dataset))
        #     g.add((URIRef(v.uri), SDO.name, Literal(v.title)))

        return g

    def to_dcat_rdf(self):
        g = Graph()
        g.bind("dcat", DCAT)
        g.bind("dcterms", DCTERMS)
        vs = URIRef(self.vocs_uri)
        g.add((vs, RDF.type, DCAT.Dataset))
        g.add((vs, DCTERMS.title, Literal(self.vocs_title)))
        g.add((vs, DCTERMS.description, Literal(self.vocs_desc)))

        api = URIRef(self.uri)
        g.add((api, DCAT.servesDataset, vs))
        g.add((api, RDF.type, DCAT.DataService))
        g.add((api, DCTERMS.title, Literal("System ConnegP API")))
        g.add((api, DCTERMS.description, Literal("A Content Negotiation by Profile-compliant service that provides "
                                                 "access to all of this catalogue's information")))
        g.add((api, DCTERMS.type, URIRef("http://purl.org/dc/dcmitype/Service")))
        g.add((api, DCAT.endpointURL, api))

        sparql = URIRef(self.uri + "/sparql")
        g.add((sparql, DCAT.servesDataset, vs))
        g.add((sparql, RDF.type, DCAT.DataService))
        g.add((sparql, DCTERMS.title, Literal("System SPARQL Service")))
        g.add((sparql, DCTERMS.description, Literal("A SPARQL Protocol-compliant service that provides access to all "
                                                    "of this catalogue's information")))
        g.add((sparql, DCTERMS.type, URIRef("http://purl.org/dc/dcmitype/Service")))
        g.add((sparql, DCAT.endpointURL, sparql))

        return g


class VocPrezRenderer(Renderer):
    def __init__(self, request, system_uri, vocs_uri, vocs_title, vocs_desc, g_vocabs):
        self.profiles = {
            "dcat": profile_dcat,
            "sdo": profile_sdo
        }
        self.vocprez = VocPrez(system_uri, vocs_uri, vocs_title, vocs_desc, g_vocabs)

        super().__init__(request, self.vocprez.uri, self.profiles, "sdo")

    def render(self):
        # try returning alt profile
        response = super().render()
        if response is not None:
            return response
        elif self.profile == "dcat":
            if self.mediatype in Renderer.RDF_SERIALIZER_TYPES_MAP:
                g = self.vocprez.to_dcat_rdf()
                return super()._make_rdf_response(g)
            else:
                return self._render_dcat_html()
        elif self.profile == "sdo":
            if self.mediatype in Renderer.RDF_SERIALIZER_TYPES_MAP:
                g = self.vocprez.to_sdo_rdf()
                return super()._make_rdf_response(g)
            else:
                return self._render_sdo_html()

    def _render_dcat_html(self):

        # _template_context = {
        #     "uri": self.vocprez.uri,
        #     "title": title,
        #     "description": "This dataset represents the total content of this catalogue.",
        #     "created": created,
        #     "modified": modified,
        #     "creator": creator,
        #     "publisher": publisher,
        #     "distributions": distributions
        # }

        return Response(
            render_template("index.html"),  # **_template_context),
            headers=self.headers,
        )

    def _render_sdo_html(self):

        # _template_context = {
        #     "uri": self.vocprez.uri,
        #     "title": title,
        #     "description": description,
        #     "publisher": publisher,
        # }

        return Response(
            render_template("index.html"),  # **_template_context),
            headers=self.headers,
        )
