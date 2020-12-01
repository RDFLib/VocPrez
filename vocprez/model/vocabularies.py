from flask import Response
from pyldapi import Renderer, ContainerRenderer
from rdflib import URIRef, Literal
from rdflib.namespace import DCAT, DCTERMS, RDF, RDFS
from vocprez.model.profiles import profile_dcat


class VocabulariesRenderer(ContainerRenderer):
    def __init__(self, request, flask_vocs, system_uri_base, vocs_uri, vocs_title, vocs_desc):
        self.system_uri_base = system_uri_base
        # work out stuff from request
        self.page = int(request.values.get("page")) if request.values.get("page") is not None else 1
        self.per_page = int(request.values.get("per_page")) \
                   if request.values.get("per_page") is not None \
                   else 10

        # get this instance's list of vocabs
        vocabs = list(flask_vocs.keys())

        # respond to a filter
        if request.values.get("filter") is not None:
            vocabs = [
                v for v in vocabs
                if request.values.get("filter").lower() in flask_vocs[v].id.lower()
                   or request.values.get("filter").lower() in flask_vocs[v].title.lower()
                   or request.values.get("filter").lower() in flask_vocs[v].description.lower()
            ]

        # make local or absolute URIs

        vocabs = [(v, flask_vocs[v].title) for v in vocabs]
        vocabs.sort(key=lambda tup: tup[1])
        total = len(vocabs)
        start = (self.page - 1) * self.per_page
        end = start + self.per_page
        self.vocabs = vocabs[start:end]

        super().__init__(
            request,
            vocs_uri,
            vocs_title,
            vocs_desc,
            None,
            None,
            self.vocabs,
            total,
            profiles={"dcat": profile_dcat},
            default_profile_token="dcat",
            super_register=None,
            page_size_max=1000,
            register_template="vocabularies.html"
        )

    def _make_dcat_graph(self):
        g = super()._generate_mem_profile_rdf()
        g.bind("dcat", DCAT)
        g.bind("dcterms", DCTERMS)
        for s in g.subjects(predicate=RDF.type, object=RDF.Bag):
            g.remove((
                s,
                RDF.type,
                RDF.Bag
            ))
            g.add((
                s,
                RDF.type,
                DCAT.Catalogue
            ))

            for p, o in g.predicate_objects(subject=s):
                if p == RDFS.label:
                    g.remove((s, p, o))
                    g.add((s, DCTERMS.title, o))
                elif p == RDFS.comment:
                    g.remove((s, p, o))
                    g.add((s, DCTERMS.description, o))

            api = URIRef(self.system_uri_base)
            g.add((api, RDF.type, DCAT.DataService))
            g.add((api, DCTERMS.title, Literal("System ConnegP API")))
            g.add((api, DCTERMS.description, Literal("A Content Negotiation by Profile-compliant service that provides "
                                                     "access to all of this catalogue's information")))
            g.add((api, DCTERMS.type, URIRef("http://purl.org/dc/dcmitype/Service")))
            g.add((api, DCAT.endpointURL, api))

            sparql = URIRef(self.system_uri_base + "/sparql")
            g.add((sparql, RDF.type, DCAT.DataService))
            g.add((sparql, DCTERMS.title, Literal("System SPARQL Service")))
            g.add((sparql, DCTERMS.description, Literal("A SPARQL Protocol-compliant service that provides access "
                                                        "to all of this catalogue's information")))
            g.add((sparql, DCTERMS.type, URIRef("http://purl.org/dc/dcmitype/Service")))
            g.add((sparql, DCAT.endpointURL, sparql))

        for s, o in g.subject_objects(predicate=RDFS.member):
            g.remove((s, RDFS.member, o))
            g.add((
                o,
                RDF.type,
                DCAT.Dataset
            ))
            g.add((
                s,
                DCAT.dataset,
                o
            ))
            for p2, o2 in g.predicate_objects(subject=o):
                if p2 == RDFS.label:
                    g.remove((o, p2, o2))
                    g.add((o, DCTERMS.title, o2))
                elif p == RDFS.comment:
                    g.remove((o, p2, o2))
                    g.add((o, DCTERMS.description, o2))

        return g

    def render(self):
        """
        Renders the register profile.

        :return: A Flask Response object.
        :rtype: :py:class:`flask.Response`
        """
        response = super().render()
        if self.paging_error is None:
            if response is None and self.profile == "dcat":
                if self.mediatype in Renderer.RDF_MEDIA_TYPES:
                    g = self._make_dcat_graph()
                    return super()._make_rdf_response(g)
                else:
                    # TODO: make a better DCAT HTML view
                    return super()._render_mem_profile_html()
        else:  # there is a paging error (e.g. page > last_page)
            return Response(self.paging_error, status=400, mimetype="text/plain")
        return response
