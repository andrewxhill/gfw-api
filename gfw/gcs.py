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

"""This module supports reading and writing to Google Cloud Storage."""

import cloudstorage as gcs

ANALYSIS_BUCKET = '/gfw-apis-analysis'
COUNTRY_BUCKET = '/gfw-apis-country'

RETRY_PARAMS = gcs.RetryParams(initial_delay=0.2,
                               max_delay=5.0,
                               backoff_factor=2,
                               max_retry_period=15)

gcs.set_default_retry_params(RETRY_PARAMS)

def exists(filename):
	try:
		path = ''.join([COUNTRY_BUCKET, filename])
		gcs.stat(filename)
		return True
	except:
		return False

def create_file(value, filename, content_type):
    """Create a file.

    The retry_params specified in the open call will override the default
    retry params for this particular file handle.

    Args:
      filename: filename.
    """
    path = ''.join([ANALYSIS_BUCKET, filename])
    gcs_file = gcs.open(path,
                        'w',
                        content_type=content_type,
                        options={})
    gcs_file.write(value)
    gcs_file.close()
    return '/gs%s' % path
