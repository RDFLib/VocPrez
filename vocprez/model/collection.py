from vocprez import __version__
from pyldapi import Renderer
from flask import Response, render_template, g
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import DCTERMS, RDF, SKOS
from vocprez.model.profiles import profile_skos
import vocprez._config as config
from typing import List
from vocprez.model.property import Property


class Collection:
    def __init__(
        self,
        vocab_uri,
        uri,
        prefLabel,
        definition,
        source,
        members,
        other_properties: List[Property] = None
    ):
        self.vocab_uri = vocab_uri
        self.uri = uri
        self.prefLabel = prefLabel
        self.definition = definition
        self.source = source
        self.members = members

        self.other_properties = other_properties


class CollectionRenderer(Renderer):
    def __init__(self, request, collection):
        self.profiles = self._add_skos_profile()
        self.collection = collection

        super().__init__(request, self.collection.uri, self.profiles, "skos")

    def _add_skos_profile(self):
        return {"skos": profile_skos}

    def render(self):
        # try returning alt profile
        response = super().render()
        if response is not None:
            return response
        elif self.profile == "skos":
            if self.mediatype in Renderer.RDF_MEDIA_TYPES:
                return self._render_skos_rdf()
            else:
                return self._render_skos_html()

    def _render_skos_rdf(self):
        # make Collection RDF from Collection object in memory
        # (this is faster than re-querying for RDF from the main cache or a vocab's source)
        # this is the SKOS view - only SKOS stuff
        g = Graph()
        g.bind("dcterms", DCTERMS)
        g.bind("skos", SKOS)

        c = URIRef(self.collection.uri)

        # Collection metadata
        g.add((
            c,
            RDF.type,
            SKOS.Collection
        ))
        g.add((
            c,
            SKOS.prefLabel,
            Literal(self.collection.prefLabel, lang=config.DEFAULT_LANGUAGE)
        ))
        if self.collection.definition is not None:
            g.add((
                c,
                SKOS.definition,
                Literal(self.collection.definition, lang=config.DEFAULT_LANGUAGE)
            ))
        for k, v in self.collection.source.items():
            if k == "provenance" and v is not None:
                g.add((
                    c,
                    DCTERMS.provenance,
                    Literal(self.collection.source["provenance"], lang=config.DEFAULT_LANGUAGE)
                ))
            elif k == "source" and v is not None:
                g.add((
                    c,
                    DCTERMS.source,
                    URIRef(self.collection.source["source"])
                ))
            elif k == "wasDerivedFrom" and v is not None:
                g.add((
                    c,
                    DCTERMS.provenance,
                    URIRef(self.collection.source["wasDerivedFrom"])
                ))
        # vocab
        if self.collection.vocab_uri is not None:
            g.add((
                c,
                SKOS.inScheme,
                URIRef(self.collection.vocab_uri),
            ))

        # members
        for m in self.collection.members:
            g.add((
                c,
                SKOS.member,
                URIRef(m[0]),
            ))

        if self.collection.other_properties is not None:
            for prop in self.collection.other_properties:
                g.add((c, URIRef(prop.uri), prop.value))

        # serialise in the appropriate RDF format
        if self.mediatype in ["application/rdf+json", "application/json"]:
            graph_text = g.serialize(format="json-ld")
        else:
            graph_text = g.serialize(format=self.mediatype)

        return Response(
            graph_text,
            mimetype=self.mediatype,
            headers=self.headers,
        )

    def _render_skos_html(self):
        _template_context = {
            "version": __version__,
            "vocab_uri": self.collection.vocab_uri if self.collection.vocab_uri is not None else self.request.values.get("vocab_uri"),
            "vocab_title": g.VOCABS[self.collection.vocab_uri].title,
            "uri": self.instance_uri,
            "collection": self.collection,
        }

        return Response(
            render_template("collection.html", **_template_context),
            headers=self.headers,
        )
