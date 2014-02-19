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

import webapp2
import monitor
import common
import traceback

from appengine_config import runtime_config

from gfw import forma, imazon, modis, gcs

from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.api import urlfetch
from google.appengine.ext import ndb

# Support datasets for download.
_DATASETS = ['imazon', 'forma', 'modis']

# Supported dataset download formats.
_FORMATS = ['shp', 'geojson', 'kml', 'svg', 'csv']

# Download route.
_ROUTE = r'/datasets/<dataset:(%s)>.<fmt:(%s)>' % \
    ('|'.join(_DATASETS), '|'.join(_FORMATS))

# Download route via backend.
_BACKEND_ROUTE = r'/backend%s' % _ROUTE

# Maps CartoDB download format to GCS content type.
_CONTENT_TYPES = {
    'shp': 'application/octet-stream',
    'kml': 'application/vnd.google-earth.kmz',
    'svg': 'image/svg+xml',
    'csv': 'application/csv',
    'geojson': 'application/json',
}


class Cache():
    @classmethod
    def forma(cls, key, params, fmt):
        params['dataset'] = 'forma'
        params['fmt'] = fmt
        filename = '{dataset}_{begin}_{end}_{iso}.{fmt}' \
            .format(**params)
        gcs_path = gcs.exists(filename)
        if gcs_path:
            blobstore_filename = '/gs%s' % gcs_path
            blob_key = blobstore.create_gs_key(blobstore_filename)
            entry = DownloadEntry(id=key, blob_key=blob_key)
            entry.put()
            return entry

    @classmethod
    def get(cls, key, dataset, params, fmt, bust):
        if not bust:
            entry = DownloadEntry.get_by_id(key)
            if entry and entry.blob_key:
                return entry
        if dataset == 'forma':
            return cls.forma(key, params, fmt)


def _download(dataset, params):
    if dataset == 'imazon':
        return imazon.download(params)
    elif dataset == 'forma':
        return forma.download(params)
    elif dataset == 'modis':
        return modis.download(params)
    raise ValueError('Unsupported dataset for download: %s' % dataset)


class DownloadEntry(ndb.Model):
    """Download cache entry for datastore."""
    cdb_url = ndb.TextProperty()
    blob_key = ndb.TextProperty()


class Download(blobstore_handlers.BlobstoreDownloadHandler):
    def _redirect(self, url):
        self.response.headers.add_header("Access-Control-Allow-Origin", "*")
        self.response.headers.add_header(
            'Access-Control-Allow-Headers',
            'Origin, X-Requested-With, Content-Type, Accept')
        self.redirect(str(url))

    def _send_error(self):
        self.response.set_status(400)
        msg = "Something's not right. Sorry about that! We notified the team."
        self.response.out.write(msg)

    def options(self, dataset, fmt):
        """Options to support CORS requests."""
        self.response.headers['Access-Control-Allow-Origin'] = '*'
        self.response.headers['Access-Control-Allow-Headers'] = \
            'Origin, X-Requested-With, Content-Type, Accept'
        self.response.headers['Access-Control-Allow-Methods'] = 'POST, GET'

    def get(self, dataset, fmt):
        self.post(dataset, fmt)

    def post(self, dataset, fmt):
        params = common._get_request_params(self.request)
        params['format'] = fmt
        rid = common._get_request_id(self.request, params)
        bust = params.get('bust')

        entry = Cache.get(rid, dataset, params, fmt, bust)
        if entry and entry.blob_key:
            self.send_blob(entry.blob_key)
        elif entry and entry.cdb_url:
            self._redirect(entry.cdb_url)
        else:
            url = None
            try:
                url = _download(dataset, params)
                urlfetch.fetch(url, method='HEAD', deadline=60)
            except Exception, error:
                name = error.__class__.__name__
                trace = traceback.format_exc()
                msg = 'CartoDB %s download failure: %s: %s - URL: %s' % \
                    (dataset, name, error, url)
                monitor.log(self.request.url, msg, error=trace,
                            headers=self.request.headers)
                self._send_error()
                return
            DownloadEntry(id=rid, cdb_url=url).put()
            self._redirect(url)

routes = [webapp2.Route(_ROUTE, handler=Download)]

handlers = webapp2.WSGIApplication(routes, debug=runtime_config.get('IS_DEV'))
