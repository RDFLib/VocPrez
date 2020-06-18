from pyldapi import ContainerRenderer
from flask import Response, jsonify, g
from flask_paginate import Pagination
from vocprez.model.profiles import *


class SkosRegisterRenderer(ContainerRenderer):
    def __init__(
        self,
        request,
        navs,
        members,
        register_item_type_string,
        total,
        search_enabled=None,
        search_query=None,
        contained_item_classes=[],
        **kwargs
    ):

        self.vocab_id = kwargs.get('vocab_id')
        self.navs = navs
        # TODO: Deal with this more elegantly
        try:
            self.members = [(x.uri, x.title) for x in members]  # Vocabulary members
        except:
            self.members = [(x["uri"], x["title"]) for x in members]  # dict members

        self.register_item_type_string = register_item_type_string
        self.search_query = search_query
        self.search_enabled = search_enabled
        self.vocabulary_url = contained_item_classes
        self.template_extras = kwargs
        profiles = {
            "ckan": profile_ckan
        }

        if "/concept/" in request.base_url:
            label = "Concepts within " + g.VOCABS[self.vocab_id].title
            description = "All of the Concepts for the Vocabulary <a href=\"" + request.base_url.replace('/concept/', '') + "\">" + g.VOCABS[self.vocab_id].title + '</a>'
        else:
            label = "Vocabularies"
            description = "All of the Vocabularies published by this instance of VocPrez"

        super().__init__(
            request,
            request.base_url,
            label,
            description,
            None,
            None,
            self.members,
            members_total_count=len(members),
            profiles=profiles,
        )

    def render(self):
        """
        Renders the register view.

        :return: A Flask Response object.
        :rtype: :py:class:`flask.Response`
        """
        # try returning alt profile
        response = Renderer.render(self)
        if response is not None:
            return response
        elif self.profile == "mem":
            if self.paging_error is None:
                self.headers["Profile"] = str(self.profiles["mem"].uri)
                if self.mediatype == "text/html":
                    response = self._render_mem_profile_html()
                # elif self.mediatype in ContainerRenderer.RDF_MEDIA_TYPES:
                #     response = self._render_mem_profile_rdf()
                else:
                    response = self._render_mem_profile_rdf()
            else:  # there is a paging error (e.g. page > last_page)
                response = Response(
                    self.paging_error, status=400, mimetype="text/plain"
                )
        elif self.profile == "ckan":
            if self.paging_error is None:
                response = self._render_ckan_profile()
        return response

    def _render_ckan_profile(self):
        """
        Render a CKAN view, which is formatted as an application/sparql-results+json response.

        :return: A list of register items rendered as application/sparql-results+json.
        :rtype: JSON
        """
        response = {"head": {"vars": ["s", "pl"]}, "results": {"bindings": []}}
        for member in self.members:
            response["results"]["bindings"].append(
                {
                    "pl": {"xml:lang": "en", "type": "literal", "value": member[1]},
                    "s": {"type": "uri", "value": member[0]},
                }
            )

        response = jsonify(response)
        response.headers.add("Access-Control-Allow-origin", "*")
        return response
