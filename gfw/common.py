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

"""This module supports common functions."""

import os

CONTENT_TYPES = {
    'application/vnd.gfw+json': 'application/json',
    'application/vnd.gfw.geojson+json': 'application/json',
    'application/vnd.gfw.csv+json': 'application/csv',
    'application/vnd.gfw.svg+json': 'image/svg+xml',
    'application/vnd.gfw.kml+json': 'application/vnd.google-earth.kmz',
    'application/vnd.gfw.shp+json': 'application/octet-stream'
}

MEDIA_TYPES = {
    'shp': 'application/vnd.gfw.shp+json',
    'kml': 'application/vnd.gfw.kml+json',
    'svg': 'application/vnd.gfw.svg+json',
    'csv': 'application/vnd.gfw.csv+json',
    'geojson': 'application/vnd.gfw.geojson+json'
}


GCS_URL_TMPL = 'http://storage.googleapis.com/gfw-apis-analysis%s.%s'

IS_DEV = 'Development' in os.environ['SERVER_SOFTWARE']

if IS_DEV:
    APP_BASE_URL = 'http://localhost:8080'
else:
    APP_BASE_URL = 'http://gfw-apis.appspot.com'


def get_cartodb_format(gfw_media_type):
    """Return CartoDB format for supplied GFW custom media type."""
    tokens = gfw_media_type.split('.')
    if len(tokens) == 2:
        return 'json'
    else:
        return tokens[2].split('+')[0]
