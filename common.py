# Global Forest Watch API
# Copyright (C) 2013 World Resource Institute
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import json
import re
import webapp2

from hashlib import md5


def _get_request_params(request, body=False):
    """Return params as a dictionary for supplied HTTP request."""
    if body:
        params = json.loads(request.body)
    else:
        args = request.arguments()
        vals = map(request.get, args)
        params = dict(zip(args, vals))
    return params


def _get_request_id(request, params):
    """Return id for supplied HTTP request and parameters."""
    path, fmt = request.path.lower().split('.')
    fmt = fmt if fmt != 'shp' else 'zip'
    whitespace = re.compile(r'\s+')
    params = re.sub(whitespace, '', json.dumps(params, sort_keys=True))
    return '%s/%s.%s' % (path, md5(params).hexdigest(), fmt)


class BaseApi(webapp2.RequestHandler):
    """Base request handler for API."""

    def _get_id(self, params):
        whitespace = re.compile(r'\s+')
        params = re.sub(whitespace, '', json.dumps(params, sort_keys=True))
        return '/'.join([self.request.path.lower(), md5(params).hexdigest()])

    def _get_params(self, body=False):
        if body:
            params = json.loads(self.request.body)
        else:
            args = self.request.arguments()
            vals = map(self.request.get, args)
            params = dict(zip(args, vals))
        return params

    def _redirect(self, url):
        self.response.headers.add_header("Access-Control-Allow-Origin", "*")
        self.response.headers.add_header(
            'Access-Control-Allow-Headers',
            'Origin, X-Requested-With, Content-Type, Accept')
        self.redirect(str(url))

    def _send_response(self, data):
        """Sends supplied result dictionnary as JSON response."""
        self.response.headers.add_header("Access-Control-Allow-Origin", "*")
        self.response.headers.add_header(
            'Access-Control-Allow-Headers',
            'Origin, X-Requested-With, Content-Type, Accept')
        self.response.headers.add_header('charset', 'utf-8')
        self.response.headers["Content-Type"] = "application/json"
        self.response.out.write(str(data))

    def options(self):
        """Options to support CORS requests."""
        self.response.headers['Access-Control-Allow-Origin'] = '*'
        self.response.headers['Access-Control-Allow-Headers'] = \
            'Origin, X-Requested-With, Content-Type, Accept'
        self.response.headers['Access-Control-Allow-Methods'] = 'POST, GET'
