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

import json
import webapp2
import logging
import urllib

from gfw import cdb
from appengine_config import runtime_config

from google.appengine.api import mail
from google.appengine.api import taskqueue


def log(url, msg, error=None, headers={}):
    headers = dict([(k, v) for k, v in headers.iteritems()])
    params = dict(url=url, msg=msg, headers=json.dumps(headers))
    if error:
        error = '%s: %s' % (error.__class__.__name__, str(error))
        params['error'] = error
    taskqueue.add(url='/monitor', params=params, queue_name="log")


class Monitor(webapp2.RequestHandler):
    def post(self):
        params = ['url', 'msg', 'error', 'headers']
        url, msg, error, headers = map(self.request.get, params)
        dev = runtime_config.get('IS_DEV')
        headers = json.loads(headers)
        lat, lon = headers.get('X-Appengine-Citylatlong', '0,0').split(',')
        point = '{"type": "Point", "coordinates": [%s, %s]}' % (lon, lat)
        the_geom = "ST_SetSRID(ST_GeomFromGeoJSON('%s'), 4326)" % point
        vals = dict(
            dev=dev,
            error=error.replace("'", ''),
            url=urllib.quote_plus(url),
            msg=msg.replace("'", ''),
            country=headers.get('X-Appengine-Country'),
            region=headers.get('X-Appengine-Region'),
            city=headers.get('X-Appengine-City'),
            the_geom=the_geom)
        if error:
            logging.error('MONITOR: %s' % vals)
            mail.send_mail(
                sender='noreply@gfw-apis.appspotmail.com',
                to='eightysteele+gfw-api-errors@gmail.com',
                subject='[GFW API ERROR] %s' % msg,
                body=json.dumps(vals, sort_keys=True, indent=4,
                                separators=(',', ': ')))
        else:
            logging.info('MONITOR: %s' % vals)
        sql = """INSERT INTO gfw_api_monitor
                 (dev, error, url, msg, country, region, city, the_geom)
                 VALUES
                 ({dev},'{error}','{url}','{msg}','{country}','{region}',
                 '{city}', {the_geom});"""
        query = sql.format(**vals)
        if not dev:
            cdb.execute(query, auth=True)


routes = [webapp2.Route(r'/monitor', handler=Monitor, methods=['POST'])]
handlers = webapp2.WSGIApplication(routes, debug=runtime_config.get('IS_DEV'))
