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
import logging
import os

from appengine_config import runtime_config

from gfw import forma, imazon, modis, gcs

from google.appengine.api import backends
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import blobstore
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
    def _backend_redirect(self):
        self.response.headers.add_header("Access-Control-Allow-Origin", "*")
        self.response.headers.add_header(
            'Access-Control-Allow-Headers',
            'Origin, X-Requested-With, Content-Type, Accept')
        host = backends.get_url(backend='download')
        path = '/backend%s' % os.environ.get('PATH_INFO')
        query = os.environ.get('QUERY_STRING')
        url = '%s%s?%s' % (host, path, query)
        logging.info('REDIRECT BACKEND: %s' % url)
        self.redirect(url)

    def _send_error(self):
        self.response.set_status(400)
        msg = "Something's not right. Sorry about that! We notified the team."
        self.response.out.write(msg)

    def start(self):
        logging.info('BACKEND STARTING')

    def stop(self):
        logging.info('BACKEND STOPPING')

    def download(self, dataset, fmt):
        params = common._get_request_params(self.request)
        params['format'] = fmt
        rid = common._get_request_id(self.request, params)
        bust = params.get('bust')
        entry = DownloadEntry.get_by_id(rid)
        if entry and not bust:
            self.send_blob(entry.value)
        else:
            try:
                response = _download(dataset, params)
                if response.status == 200:
                    content = response.read()
                    content_type = _CONTENT_TYPES[fmt]
                    gcs_path = gcs.create_file(content, rid, content_type)
                    blob_key = blobstore.create_gs_key(gcs_path)
                    entry = DownloadEntry(id=rid, value=blob_key)
                    entry.put()
                    self.send_blob(entry.value)
                elif response.status == 504:
                    if not 'backend' in self.request.url:
                        self._backend_redirect()
                    else:
                        msg = 'CartoDB error: %s, code:%s, content:%s' % \
                            (dataset, response.status, response.read())
                        monitor.error(self.request.url, msg)
                        self._send_error()
                else:
                    # Unrecoverable problem with the CartoDB request:
                    msg = 'CartoDB error: %s, status:%s, content:%s' % \
                        (dataset, response.status, response.read())
                    monitor.error(self.request.url, msg)
                    self._send_error()
            except Exception, e:
                # App Engine exception:
                name = e.__class__.__name__
                logging.info('DOWNLOAD ERROR %s' % name)
                if name in ['DeadlineExceededError']:
                    if not 'backend' in self.request.url:
                        self._backend_redirect()
                    else:
                        msg = 'Download error: %s' % dataset
                        monitor.error(self.request.url, msg, error=e)
                        self._send_error()
                else:
                    msg = 'Download error: %s' % dataset
                    monitor.error(self.request.url, msg, error=e)
                    self._send_error()


routes = [
    webapp2.Route(_ROUTE, handler=Download, handler_method='download'),
    webapp2.Route(r'/_ah/start', handler=Download, handler_method='start'),
    webapp2.Route(r'/_ah/stop', handler=Download, handler_method='stop'),
    webapp2.Route(_BACKEND_ROUTE, handler=Download, handler_method='download')]

handlers = webapp2.WSGIApplication(routes, debug=runtime_config.get('IS_DEV'))

application = webapp.WSGIApplication(routes)


def main():
    run_wsgi_app(application)

if __name__ == '__main__':
    main()
