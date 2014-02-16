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


def error(url, msg, error=None):
    if error:
        error = '%s: %s' % (error.__class__.__name__, str(error))
    params = dict(url=url, msg=msg, error=error)
    taskqueue.add(url='/monitor', params=params, queue_name="log")


class Monitor(webapp2.RequestHandler):
    def post(self):
        url, msg, error = map(self.request.get, ['url', 'msg', 'error'])
        dev = runtime_config.get('IS_DEV')
        vals = dict(dev=dev, error=error, url=urllib.quote_plus(url), msg=msg)
        logging.error('MONITOR ERROR: %s' % vals)
        sql = """INSERT INTO gfw_api_monitor
                 (dev, error, url, msg)
                 VALUES
                 ({dev},'{error}','{url}','{msg}');"""
        query = sql.format(**vals)
        logging.info(query)
        mail.send_mail(
            sender='noreply@gfw-apis.appspotmail.com',
            to='eightysteele+gfw-api-errors@gmail.com',
            subject='[GFW API ERROR] %s' % msg,
            body=json.dumps(vals))
        cdb.execute(query, auth=True)


routes = [webapp2.Route(r'/monitor', handler=Monitor, methods=['POST'])]
handlers = webapp2.WSGIApplication(routes, debug=runtime_config.get('IS_DEV'))
