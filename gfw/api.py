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

"""This module contains request handlers for the Global Forest Watch API."""

import json
import logging
import re
import webapp2

from gfw import cdb
from gfw import forma
from gfw import imazon
from gfw import gcs
from gfw.common import CONTENT_TYPES, IS_DEV
from hashlib import md5
from google.appengine.ext import blobstore
from google.appengine.ext import ndb
from google.appengine.ext.webapp import blobstore_handlers


class Entry(ndb.Model):
    value = ndb.TextProperty()


def analyze(dataset, params):
    if dataset == 'imazon':
        return imazon.analyze(params)
    elif dataset == 'forma':
        return forma.analyze(params)
    return None


def download(dataset, params):
    if dataset == 'imazon':
        return imazon.download(params)
    elif dataset == 'forma':
        return forma.download(params)
    return None


ANALYSIS_ROUTE = r'/datasets/<dataset:(imazon|forma|modis|hansen)>'
DOWNLOAD_ROUTE = r'%s.<format:(shp|geojson|kml|svg|csv)>' % ANALYSIS_ROUTE
COUNTRY_ALERTS_ROUTE = r'/countries/alerts'


class DownloadApi(blobstore_handlers.BlobstoreDownloadHandler):
    def _get_id(self, params):
        path, format = self.request.path.lower().split('.')
        logging.info('FORMAT %s' % format)
        format = format if format != 'shp' else 'zip'
        logging.info('FORMAT %s' % format)
        whitespace = re.compile(r'\s+')
        params = re.sub(whitespace, '', json.dumps(params, sort_keys=True))
        return '%s/%s.%s' % (path, md5(params).hexdigest(), format)

    def download(self, dataset, format):
        args = self.request.arguments()
        vals = map(self.request.get, args)
        params = dict(zip(args, vals))
        params['format'] = format
        rid = self._get_id(params)
        entry = Entry.get_by_id(rid)
        if not entry or params.get('bust'):
            data = download(dataset, params)
            if data:
                content_type = CONTENT_TYPES[format]
                gcs_path = gcs.create_file(data, rid, content_type)
                value = blobstore.create_gs_key(gcs_path)
                entry = Entry(id=rid, value=value)
                entry.put()
        if entry.value:
            self.send_blob(entry.value)
        else:
            self.error(404)


class BaseApi(webapp2.RequestHandler):
    """Base request handler for API."""

    def _send_response(self, data):
        """Sends supplied result dictionnary as JSON response."""
        self.response.headers.add_header("Access-Control-Allow-Origin", "*")
        self.response.headers.add_header(
            'Access-Control-Allow-Headers',
            'Origin, X-Requested-With, Content-Type, Accept')
        self.response.headers.add_header('charset', 'utf-8')
        if not data:
            self.response.out.write('{}')
            return
        self.response.headers.add_header("Content-Type", "application/json")
        self.response.out.write(data)

    def _get_id(self, params):
        whitespace = re.compile(r'\s+')
        params = re.sub(whitespace, '', json.dumps(params, sort_keys=True))
        return '/'.join([self.request.path.lower(), md5(params).hexdigest()])

    def options(self):
        """Options to support CORS requests."""
        self.response.headers['Access-Control-Allow-Origin'] = '*'
        self.response.headers['Access-Control-Allow-Headers'] = \
            'Origin, X-Requested-With, Content-Type, Accept'
        self.response.headers['Access-Control-Allow-Methods'] = 'POST, GET'


class AnalyzeApi(BaseApi):
    """Handler for aggregated defor values for supplied dataset and polygon."""

    def analyze(self, dataset):
        args = self.request.arguments()
        vals = map(self.request.get, args)
        params = dict(zip(args, vals))
        rid = self._get_id(params)
        entry = Entry.get_by_id(rid)
        if not entry or params.get('bust'):
            value = analyze(dataset, params)
            entry = Entry(id=rid, value=json.dumps(value))
            entry.put()
        self._send_response(entry.value)


class CountryApi(BaseApi):
    """Handler for countries."""

    def alerts(self):
        args = self.request.arguments()
        vals = map(self.request.get, args)
        params = dict(zip(args, vals))
        rid = self._get_id(params)
        if 'interval' not in params:
            params['interval'] = '12 MONTHS'
        sql = """SELECT countries.name,
             countries.iso,
             countries.enabled,
             alerts.count as alerts_count
      FROM gfw2_countries as countries
      LEFT OUTER JOIN (SELECT COUNT(*) as count,
                              iso
                       FROM cdm_latest
                       WHERE date >= now() - INTERVAL '{interval}'
                       GROUP BY iso) as alerts ON alerts.iso = countries.iso"""
        entry = Entry.get_by_id(rid)
        if not entry or self.request.get('bust'):
            result = cdb.execute(sql.format(**params))
            if result:
                value = json.loads(result)['rows']
            entry = Entry(id=rid, value=json.dumps(value))
            entry.put()
        self._send_response(entry.value)

routes = [
    webapp2.Route(ANALYSIS_ROUTE, handler=AnalyzeApi,
                  handler_method='analyze'),
    webapp2.Route(DOWNLOAD_ROUTE, handler=DownloadApi,
                  handler_method='download'),
    webapp2.Route(COUNTRY_ALERTS_ROUTE, handler=CountryApi,
                  handler_method='alerts')
]

handlers = webapp2.WSGIApplication(routes, debug=IS_DEV)
