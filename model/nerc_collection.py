from pyldapi import Renderer
from flask import Response, render_template, request
from model.profiles import profile_skos
from SPARQLWrapper import SPARQLWrapper, JSON, XML


def curie(uri):
    prefixes = {
        "grg": "http://www.isotc211.org/schemas/grg/",
        "dcterms": "http://purl.org/dc/terms/",
        "owl": "http://www.w3.org/2002/07/owl#",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "skos": "http://www.w3.org/2004/02/skos/core#"
    }
    for prefix, namespace in prefixes.items():
        if namespace in uri:
            return prefix + ":" + uri.replace(namespace, "")
    # can't match a know prefixe, return the last URI segment only
    return uri.split("#")[-1].split("/")[-1]


class Collection:
    def __init__(
        self, vocab, uri, label, comment, members,
    ):
        self.vocab = vocab
        self.uri = uri
        self.label = label
        self.comment = comment
        self.members = members


class NercCollectionRenderer(Renderer):
    def __init__(self, request):
        self.profiles = self._add_skos_profile()
        self.navs = []  # TODO: add in other nav items for Collection

        super().__init__(request, request.values.get("uri"), self.profiles, "skos")

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
        collection_uri = request.values.get("uri")
        sparql = SPARQLWrapper("http://vocab.nerc.ac.uk/sparql/sparql")
        # get the collection members
        sparql.setQuery("""
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            
            CONSTRUCT {{
                <{col_uri}> skos:member ?m .
                ?m skos:prefLabel ?pl.
            }}
            WHERE {{
                <{col_uri}> skos:member ?m .
                ?m skos:prefLabel ?pl.
            }}
            ORDER BY ?pl
            """.format(**{"col_uri": collection_uri}))
        sparql.setReturnFormat(XML)
        new_g = sparql.query().convert()
        # get the collection metadata
        sparql.setQuery("""
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            
            CONSTRUCT {{
              <{col_uri}> ?p ?o .
            }}
            WHERE {{
              <{col_uri}> ?p ?o .
            
              FILTER (?p != skos:member)
            }}""".format(**{"col_uri": collection_uri}))
        sparql.setReturnFormat(XML)
        new_g = new_g + sparql.query().convert()

        # serialise in the appropriate RDF format
        if self.mediatype in ["application/ld+json", "application/rdf+json", "application/json"]:
            self.mediatype = "application/ld+json"

        return Response(new_g.serialize(format=self.mediatype), headers={"Content-Type": self.mediatype})

    def _render_skos_html(self):
        collection_uri = request.values.get("uri")
        sparql = SPARQLWrapper("http://vocab.nerc.ac.uk/sparql/sparql")
        # get the collection members
        sparql.setQuery("""
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

            SELECT DISTINCT *
            WHERE {{
                <{}> skos:member ?m .
                ?m skos:prefLabel ?pl.
            }}
            ORDER BY ?pl
            """.format(collection_uri))
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()

        members = []
        for result in results["results"]["bindings"]:
            members.append((result["m"]["value"], result["pl"]["value"]))

        # get the collection metadata
        sparql.setQuery("""
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

            SELECT *
            WHERE {{
              <{}> ?p ?o .

              FILTER (?p != skos:member)
            }}
            """.format(collection_uri))
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()

        properties = {}
        for result in results["results"]["bindings"]:
            properties[curie(result["p"]["value"])] = (result["p"]["value"], result["o"]["value"])

        return render_template(
            "nerc_collection.html",
            collection_uri=collection_uri,
            properties=properties,
            members=members
        )
