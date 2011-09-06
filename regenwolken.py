#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#
# Copyright 2011 posativ <info@posativ.org>. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of posativ <info@posativ.org>.
#
# Regenwolken is a CloudApp clone, with leave the cloud in mind.

__version__ = "0.2"

import sys; reload(sys)
sys.setdefaultencoding('utf-8')

from werkzeug.wrappers import Request
from werkzeug.routing import Map, Rule
from werkzeug.wsgi import responder
from werkzeug.http import parse_dict_header
from werkzeug.datastructures import Authorization
from werkzeug.utils import cached_property

from wolken import SETTINGS, REST, web

def parse_authorization_header(value):
    """make nc and cnonce optional, see https://github.com/mitsuhiko/werkzeug/pull/100"""
    if not value:
        return
    try:
        auth_type, auth_info = value.split(None, 1)
        auth_type = auth_type.lower()
    except ValueError:
        return
    if auth_type == 'basic':
        try:
            username, password = auth_info.decode('base64').split(':', 1)
        except Exception:
            return
        return Authorization('basic', {'username': username,
                                       'password': password})
    elif auth_type == 'digest':
        auth_map = parse_dict_header(auth_info)
        for key in 'username', 'realm', 'nonce', 'uri', 'response':
            if not key in auth_map:
                return
        if 'qop' in auth_map:
            if not auth_map.get('nc') or not auth_map.get('cnonce'):
                return
        return Authorization('digest', auth_map)


class Wolkenrequest(Request):
    """fixing HTTP Digest Auth fallback"""
    # FIXME: Cloud.app can not handle 413 Request Entity Too Large
    max_content_length = 1024 * 1024 * 64 # max. 64 mb request size
    
    @cached_property
    def authorization(self):
        """The `Authorization` object in parsed form."""
        header = self.environ.get('HTTP_AUTHORIZATION')
        return parse_authorization_header(header)


HTML_map = Map([
    Rule('/', endpoint=web.index),
    Rule('/-<short_id>', endpoint=web.redirect),
    Rule('/<short_id>', endpoint=web.show),
])

REST_map = Map([
    Rule('/', endpoint=REST.upload_file, methods=['POST', ]),
    Rule('/items', endpoint=REST.bookmark, methods=['POST', ]),
    Rule('/register', endpoint=REST.register, methods=['POST', ]),
    Rule('/<short_id>', endpoint=REST.view_item, methods=['GET', ]),
    Rule('/account', endpoint=REST.account),
    Rule('/account/stats', endpoint=REST.account_stats),
    Rule('/items', endpoint=REST.items),
    Rule('/items/new', endpoint=REST.items_new),
    Rule('/items/<objectid>', endpoint=REST.modify_item, methods=['HEAD', 'PUT', 'DELETE']),
])


@responder
def application(environ, start_response):
    
    environ['SERVER_SOFTWARE'] = "Regenwolken/%s" % __version__
    request = Wolkenrequest(environ)
    
    if request.headers.get('Accept', 'application/json') == 'application/json':
        urls = REST_map.bind_to_environ(environ)
    else:
        urls = HTML_map.bind_to_environ(environ)

    return urls.dispatch(lambda f, v: f(environ, request, **v),
                         catch_http_exceptions=True)


if __name__ == '__main__':
    from werkzeug.serving import run_simple    
    run_simple(SETTINGS.BIND_ADDRESS, SETTINGS.PORT,
               application, use_reloader=True)
