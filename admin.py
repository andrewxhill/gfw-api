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

import os
import time
import webapp2

from gfw import common

import cloudstorage as gcs

DEV_BUCKET = '/gfw-apis-country'

my_default_retry_params = gcs.RetryParams(initial_delay=0.2,
                                          max_delay=5.0,
                                          backoff_factor=2,
                                          max_retry_period=15)

gcs.set_default_retry_params(my_default_retry_params)


class BootstrapGcs(webapp2.RequestHandler):
    def get(self):
        """Bootstraps local GCS with test data dwc files in dwc."""
        for filename in os.listdir('gcs'):
            content_type = common.CONTENT_TYPES[filename.split('.')[1]]

            path = os.path.abspath('gcs/%s' % filename)
            gcs_path = '%s/%s' % (DEV_BUCKET, filename)
            data = open(path, 'r').read()
            gcs_file = gcs.open(
                gcs_path,
                'w',
                content_type=content_type,
                options={})
            gcs_file.write(data)
            gcs_file.close()
        time.sleep(5)
        self.redirect('http://localhost:8000/blobstore')


routes = [
    webapp2.Route(r'/admin/bootstrap-gcs', handler='admin.BootstrapGcs:get'),
]

handlers = webapp2.WSGIApplication(routes, debug=True)
