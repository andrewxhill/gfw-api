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

"""This module supports accessing WPDA data."""

import json
import logging
from google.appengine.api import urlfetch

SITE_URL = 'http://protectedplanet.net/api/sites_by_point/{lon}/{lat}'
GEOM_URL = 'http://protectedplanet.net/api2/sites/{site_id}/geom'


def get_site_geom(site_id):
    rpc = urlfetch.create_rpc(deadline=60)
    geom_url = GEOM_URL.format(site_id=site_id)
    urlfetch.make_fetch_call(rpc, geom_url)
    try:
        result = rpc.get_result()
        if result.status_code == 200:
            return json.loads(result.content)
    except urlfetch.DownloadError, e:
        logging.info("WDPA site geom failed: %s %s" % (e, geom_url))


def get_site(params):
    rpc = urlfetch.create_rpc(deadline=60)
    site_url = SITE_URL.format(**params)
    logging.info(site_url)
    urlfetch.make_fetch_call(rpc, site_url)
    try:
        result = rpc.get_result()
        if result.status_code == 200:
            sites = json.loads(result.content)
            logging.info('SITES %s' % sites)
            for site in sites:
                logging.info('SITE %s' % site)
                geom = get_site_geom(site['id'])
                site['geom'] = geom
            return sites
    except urlfetch.DownloadError, e:
        logging.info("WDPA site failed: %s %s" % (e, site_url))
