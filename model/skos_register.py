from pyldapi import RegisterRenderer, View
from flask import Response, render_template, jsonify
from flask_paginate import Pagination


class SkosRegisterRenderer(RegisterRenderer):
    def __init__(self, request, navs, items, register_item_type_string, total, search_enabled=None, search_query=None, vocabulary_url=None, **kwargs):
        self.navs = navs
        self.register_item_type_string = register_item_type_string
        self.search_query = search_query
        self.search_enabled = search_enabled
        self.vocabulary_url = vocabulary_url
        self.template_extras = kwargs
        views = {
            'ckan': View(
                'Comprehensive Knowledge Archive Network',
                'The Comprehensive Knowledge Archive Network (CKAN) is a web-based open-source management system for '
                'the storage and distribution of open data.',
                ['application/json'],
                'application/json',
                languages=['en'],
                namespace='https://ckan.org/'
            )
        }
        super().__init__(
            request,
            request.base_url,
            "Test Label",
            "Test Comment",
            items,
            register_item_type_string,
            total,
            views=views
        )

    def render(self):
        """
        Renders the register view.

        :return: A Flask Response object.
        :rtype: :py:class:`flask.Response`
        """
        response = super(RegisterRenderer, self).render()
        if not response and self.view == 'reg':
            if self.paging_error is None:
                self.headers['Profile'] = str(self.views['reg'].namespace)
                response = self._render_reg_view()
            else:  # there is a paging error (e.g. page > last_page)
                response = Response(self.paging_error, status=400, mimetype='text/plain')
        elif not response and self.view == 'ckan':
            if self.paging_error is None:
                response = self._render_ckan_view()
        return response

    def _render_ckan_view(self):
        """
        Render a CKAN view, which is formatted as an application/sparql-results+json response.

        :return: A list of register items rendered as application/sparql-results+json.
        :rtype: JSON
        """
        response = {
            "head": {
                "vars": [
                    "s",
                    "pl"
                ]
            },
            "results": {
                "bindings": []
            }
        }
        for item in self.register_items:
            response['results']['bindings'].append(
                {
                    "pl": {
                        "xml:lang": "en",
                        "type": "literal",
                        "value": item[1]
                    },
                    "s": {
                        "type": "uri",
                        "value": item[0]
                    }
                }
            )

        response = jsonify(response)
        response.headers.add('Access-Control-Allow-origin', '*')
        return response

    def _render_reg_view_html(self, template_context=None):
        pagination = Pagination(page=self.page, per_page=self.per_page,
                                total=self.register_total_count,
                                page_parameter='page', per_page_parameter='per_page')
        _template_context = {
            'label': self.label,
            'comment': self.comment,
            'register_item_type_string': self.register_item_type_string,
            'register_items': self.register_items,
            'page': self.page,
            'per_page': self.per_page,
            'first_page': self.first_page,
            'prev_page': self.prev_page,
            'next_page': self.next_page,
            'last_page': self.last_page,
            'super_register': self.super_register,
            'pagination': pagination,
            'navs': self.navs,
            'query': self.search_query,
            'search_enabled': self.search_enabled,
            'vocabulary_url': self.vocabulary_url
        }
        if self.template_extras is not None:
            _template_context.update(self.template_extras)
        if template_context is not None and isinstance(template_context, dict):
            _template_context.update(template_context)

        return Response(
            render_template(
                self.register_template or 'register.html',
                **_template_context
            ),
            headers=self.headers
        )