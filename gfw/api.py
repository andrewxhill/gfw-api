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

"""This module contains API request handlers for Global Forest Watch."""

from gfw import cache
from gfw import forma
from gfw import imazon
from gfw import modis
from gfw.common import CONTENT_TYPES
from gfw.common import APP_BASE_URL
from gfw.common import MEDIA_TYPES
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers

import json
import logging
import os
import urllib
import webapp2

# application/vnd.gfw+json

# True if executing on dev server:
IS_DEV = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')

# Matches a date in yyyy-mm-dd format from between 1900-01-01 and 2099-12-31.:
DATE_REGEX = r'(19|20)\d\d[- /.](0[1-9]|1[012])[- /.](0[1-9]|[12][0-9]|3[01])'

# Path to get aggregated FORMA alerts for supplied ISO.
# /{iso}/{startdate}/{enddate} where dates are in the form yyyy-mm-dd.
FORMA_ISO = r'/api/v1/defor/analyze/forma/iso/<:\w{3,3}>/<:%s>/<:%s>' \
    % (DATE_REGEX, DATE_REGEX)

# Path for aggregated defor values by dataset for dynamic polygon as GeoJSON:
FORMA_GEOJSON = r'/api/v1/defor/analyze/forma/<:%s>/<:%s>' \
    % (DATE_REGEX, DATE_REGEX)

MODIS_ISO = r'/api/v1/defor/analyze/modis/iso/<:\w{3,3}>/<:%s>' % DATE_REGEX
MODIS_GEOJSON = r'/api/v1/defor/analyze/modis/<:%s>' % DATE_REGEX

# Imazon defor value in BRA poly or GeoJSON for supplied date range.
# Note: Only data for 2008-2012
IMAZON = r'/api/dataset/imazon'
IMAZON_DOWNLOAD = r'/api/dataset/imazon<:\.(shp|geojson|kml|svg|csv)?.*>'

# API routes:
routes = [
    webapp2.Route(IMAZON, handler='gfw.api.Handler:imazon'),
    webapp2.Route(IMAZON_DOWNLOAD, handler='gfw.api.DownloadHandler:imazon'),

    webapp2.Route(FORMA_ISO, handler='gfw.api.AnalyzeApi:forma_iso'),
    webapp2.Route(FORMA_GEOJSON, handler='gfw.api.AnalyzeApi:forma_geojson'),
    webapp2.Route(MODIS_ISO, handler='gfw.api.AnalyzeApi:modis_iso'),
    webapp2.Route(MODIS_GEOJSON, handler='gfw.api.AnalyzeApi:modis_geojson'),
]


class DownloadHandler(blobstore_handlers.BlobstoreDownloadHandler):
    def imazon(self, foo):
        geom = self.request.get('geom')
        path = self.request.path
        format = path.split('.')[1]
        mt = MEDIA_TYPES[format]
        data = cache.hit(path, mt, geom=geom)
        if not data:
            value = imazon.analyze(mt, geom=geom)
            data = cache.update(path, mt, value, geom=geom)
        blob_info = blobstore.BlobInfo.get(data.gcskey)
        self.send_blob(blob_info)


class Handler(webapp2.RequestHandler):
    """Handler for aggregated defor values for supplied dataset and polygon."""

    def _send_response(self, data):
        """Sends supplied result dictionnary as JSON response."""
        self.response.headers.add_header("Access-Control-Allow-Origin", "*")
        self.response.headers.add_header(
            'Access-Control-Allow-Headers',
            'Origin, X-Requested-With, Content-Type, Accept')
        self.response.headers.add_header('charset', 'utf-8')
        if not data:
            self.response.set_status(204)
            return
        self.response.headers.add_header("X-GFW-Media-Type",
                                         str(data.media_type))
        self.response.headers.add_header("Content-Type",
                                         CONTENT_TYPES[data.media_type])
        if data.download:
            self.redirect(data.value)
        else:
            self.response.out.write(data.value)

    def _get_gfw_media_type(self):
        mt = self.request.headers['Accept']
        if not mt:
            mt = 'application/vnd.gfw+json'
        else:
            mt = filter(lambda x: x.startswith('application/vnd.gfw'),
                        mt.split(','))
            if not mt:
                mt = 'application/vnd.gfw+json'
            else:
                mt = mt[0]
        return mt

    def options(self):
        """Options to support CORS requests."""
        self.response.headers['Access-Control-Allow-Origin'] = '*'
        self.response.headers['Access-Control-Allow-Headers'] = \
            'Origin, X-Requested-With, Content-Type, Accept'
        self.response.headers['Access-Control-Allow-Methods'] = 'POST, GET'

    def imazon(self):
        geom = self.request.get('geom')
        path = self.request.path
        mt = self._get_gfw_media_type()
        data = cache.hit(path, mt, geom=geom)
        if not data:
            logging.info('MISS')
            if geom:
                geome = '?%s' % urllib.urlencode(dict(geom=geom))
            else:
                geome = ''
            value = imazon.analyze(mt, geom=geom)
            if value:
                value['shp_url'] = '%s%s.shp%s' % (APP_BASE_URL, IMAZON, geome)
                value['geojson_url'] = '%s%s.geojson%s' % \
                    (APP_BASE_URL, IMAZON, geome)
                value['kml_url'] = '%s%s.kml%s' % (APP_BASE_URL, IMAZON, geome)
                value['svg_url'] = '%s%s.svg%s' % (APP_BASE_URL, IMAZON, geome)
                value['csv_url'] = '%s%s.csv%s' % (APP_BASE_URL, IMAZON, geome)
                value = json.dumps(value)
                data = cache.update(path, mt, value, geom=geom)
            logging.info("VALUE %s" % type(value))
        else:
            logging.info('HIT %s' % path)
        self._send_response(data)

    def modis_iso(self, iso, date):
        """Return MODIS count for supplied ISO and date."""
        count = modis.get_count_by_iso(iso, date)
        result = {'units': 'count', 'value': count,
                  'value_display': format(count, ",d")}
        self._send_response(result)

    def modis_geojson(self, date):
        """Return MODIS count for supplied date and geojson polygon."""
        geojson = json.loads(self.request.get('q'))
        count = modis.get_count_by_geojson(geojson, date)
        result = {'units': 'alerts', 'value': count,
                  'value_display': format(count, ",d")}
        self._send_response(result)

    def forma_iso(self, iso, start_date, end_date):
        """Return FORMA alert count for supplied ISO and dates."""
        count = forma.get_alerts_by_iso(iso, start_date, end_date)
        result = {'units': 'alerts', 'value': count,
                  'value_display': format(count, ",d")}
        self._send_response(result)

    def forma_geojson(self, start_date, end_date):
        """Return FORMA alert count for supplied dates and geojson polygon."""
        geojson = json.loads(self.request.get('q'))
        count = forma.get_alerts_by_geojson(geojson, start_date, end_date)
        result = {'units': 'alerts', 'value': count,
                  'value_display': format(count, ",d")}
        self._send_response(result)


class DownloadApi(webapp2.RequestHandler):
    pass


class SubscribeApi(webapp2.RequestHandler):
    pass

handlers = webapp2.WSGIApplication(routes, debug=IS_DEV)
