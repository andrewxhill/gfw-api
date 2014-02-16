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
