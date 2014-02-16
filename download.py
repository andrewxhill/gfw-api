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

from appengine_config import runtime_config

from gfw import forma, imazon, modis

from google.appengine.api import urlfetch
from google.appengine.ext import ndb
from google.appengine.ext.webapp import blobstore_handlers

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
    value = ndb.TextProperty()


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

    def download(self, dataset, fmt):
        params = common._get_request_params(self.request)
        params['format'] = fmt
        rid = common._get_request_id(self.request, params)
        bust = params.get('bust')
        entry = DownloadEntry.get_by_id(rid)
        if entry and not bust:
            monitor.log(self.request.url, 'Download %s' % dataset,
                        headers=self.request.headers)
            self._redirect(entry.value)
        else:
            try:
                url = _download(dataset, params)
                response = urlfetch.fetch(url, method='HEAD', deadline=60)
                if response.status_code == 200:
                    DownloadEntry(id=rid, value=url).put()
                    monitor.log(self.request.url, 'Download %s' % dataset,
                                headers=self.request.headers)
                    self._redirect(url)
                else:
                    raise Exception('CartoDB status=%s, content=%s' %
                                    (response.status_code, response.content))
            except Exception, e:
                name = e.__class__.__name__
                msg = 'Error: Download %s (%s)' % (dataset, name)
                monitor.log(self.request.url, msg, error=e,
                            headers=self.request.headers)
                self._send_error()


routes = [webapp2.Route(_ROUTE, handler=Download, handler_method='download')]

handlers = webapp2.WSGIApplication(routes, debug=runtime_config.get('IS_DEV'))
