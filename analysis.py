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
import json

from appengine_config import runtime_config

from gfw import forma, imazon, modis, hansen

from google.appengine.ext import ndb

# Support datasets for analysis.
_DATASETS = ['imazon', 'forma', 'modis', 'hansen']

# Analysis route.
_ROUTE = r'/datasets/<dataset:(%s)>' % '|'.join(_DATASETS)


def _analyze(dataset, params):
    if dataset == 'imazon':
        return imazon.analyze(params)
    elif dataset == 'forma':
        return forma.analyze(params)
    elif dataset == 'modis':
        return modis.analyze(params)
    elif dataset == 'hansen':
        return hansen.analyze(params)
    raise ValueError('Unsupported dataset for analysis: %s' % dataset)


def _parse_analysis(dataset, content):
    if dataset == 'forma':
        return forma.parse_analysis(content)
    elif dataset == 'imazon':
        return imazon.parse_analysis(content)
    elif dataset == 'modis':
        return modis.parse_analysis(content)
    elif dataset == 'hansen':
        return hansen.parse_analysis(content)
    raise ValueError('Unsupported dataset for parse analysis %s' % dataset)


class AnalysisEntry(ndb.Model):
    """Analysis cache entry for datastore."""
    value = ndb.TextProperty()


class Analysis(common.BaseApi):

    def _send_error(self):
        self.response.set_status(400)
        msg = "Something's not right. Sorry about that! We notified the team."
        self.response.out.write(msg)

    def options(self, dataset):
        """Options to support CORS requests."""
        self.response.headers['Access-Control-Allow-Origin'] = '*'
        self.response.headers['Access-Control-Allow-Headers'] = \
            'Origin, X-Requested-With, Content-Type, Accept'
        self.response.headers['Access-Control-Allow-Methods'] = 'POST, GET'

    def get(self, dataset):
        self.post(dataset)

    def post(self, dataset):
        params = self._get_params()
        rid = self._get_id(params)
        bust = params.get('bust')
        entry = AnalysisEntry.get_by_id(rid)
        if entry and not bust:
            monitor.log(self.request.url, 'Analyze %s' % dataset,
                        headers=self.request.headers)
            self._send_response(entry.value)
        else:
            try:
                response = _analyze(dataset, params)
                if dataset == 'hansen':
                    value = json.dumps(response)
                    AnalysisEntry(id=rid, value=value).put()
                    monitor.log(self.request.url, 'Analyze %s' % dataset,
                                headers=self.request.headers)
                    self._send_response(value)
                elif response.status_code == 200:
                    result = _parse_analysis(dataset, response.content)
                    value = json.dumps(result)
                    AnalysisEntry(id=rid, value=value).put()
                    monitor.log(self.request.url, 'Analyze %s' % dataset,
                                headers=self.request.headers)
                    self._send_response(value)
                else:
                    raise Exception('CartoDB Failed (status=%s, content=%s)' %
                                   (response.status_code, response.content))
            except Exception, e:
                name = e.__class__.__name__
                msg = 'Error: Analyze %s (%s)' % (dataset, name)
                monitor.log(self.request.url, msg, error=e,
                            headers=self.request.headers)
                self._send_error()


routes = [webapp2.Route(_ROUTE, handler=Analysis)]

handlers = webapp2.WSGIApplication(routes, debug=runtime_config.get('IS_DEV'))
