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

"""This module supports caching API results."""

import json

from gfw.common import CONTENT_TYPES
from gfw.common import get_cartodb_format
from gfw.common import GCS_URL_TMPL
from gfw import gcs
from hashlib import md5
from google.appengine.ext import ndb


class Cache(ndb.Model):
    """A simple Cache moodel."""

    request = ndb.StringProperty()
    value = ndb.BlobProperty()
    media_type = ndb.StringProperty()
    download = ndb.ComputedProperty(lambda self: self.value.startswith('http'))

    @classmethod
    def get_id(cls, path, mt, params):
        phash = md5(json.dumps(params, sort_keys=True)).hexdigest()
        return '/'.join([path.lower(), get_cartodb_format(mt), phash])

    @classmethod
    def get_or_insert(cls, path, mt, params={}, value=None):
        """Get or create Cache entity and return it."""
        id = cls.get_id(path, mt, params)
        return super(Cache, cls).get_or_insert(id, request=id, value=value,
                                               media_type=mt)


def hit(path, mt, **params):
    """Return cached result for path, media type, and params or None."""
    return Cache.get_by_id(Cache.get_id(path, mt, params))


def update(path, mt, value, **params):
    """Update cache with value for supplied params."""
    id = Cache.get_id(path, mt, params)
    is_geo = mt not in ['application/vnd.gfw+json',
                        'application/vnd.gfw.csv+json']
    if is_geo:
        content_type = CONTENT_TYPES[mt]
        gcs.create_file(value, id, content_type, mt)
        url = GCS_URL_TMPL % (id, get_cartodb_format(mt))
        entry = Cache(id=id, request=id, value=url, media_type=mt)
    else:
        entry = Cache(id=id, request=id, value=value, media_type=mt)
    entry.put()
    return entry
