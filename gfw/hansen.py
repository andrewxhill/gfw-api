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

"""This module supports accessing hansen data."""

import json
import ee
import os
import logging
import re
import webapp2
import config
import copy
from hashlib import md5


from appengine_config import runtime_config

from gfw import cdb

ALL = """SELECT iso, year, sum(loss) loss, sum(loss_perc) loss_perc
         FROM hansen 
         WHERE iso ilike '{iso}' 
         GROUP BY iso, year 
         ORDER BY iso, year ASC"""

SUM = """SELECT iso, avg(treecover_2000) treecover_2000,
                avg(treecover_2000_perc) treecover_2000_perc,
                avg(gain) gain, avg(gain_perc) gain_perc,
                sum(loss) loss,
                sum(loss_perc) loss_perc
         FROM hansen 
         WHERE iso ilike '{iso}'
         GROUP BY iso"""

def _get_coords(geojson):
    return geojson.get('coordinates')

def _sum_range(data, begin, end):
    logging.info('DATA %s begin %s end %s' % (data, begin, end))
    return sum(
        [value for key, value in data.iteritems() \
            if (int(key) >= int(begin)) and (int(key) <= int(end))])

def _get_range(result, begin, end):
    percent = _sum_range(result.get('percent'), begin, end)
    area = _sum_range(result.get('area'), begin, end)
    return dict(
        percent=dict(name='UMD Percentage Loss', units='Percentage', value=percent, begin=int(begin), end=int(end)),
        area=dict(name='UMD Hectares Loss', units='Hectares', value=area, begin=int(begin), end=int(end)))

def _ee(urlparams, asset_id):
    params = copy.copy(urlparams)
    loss_by_year = ee.Image(config.assets[asset_id])
    poly = _get_coords(json.loads(params.get('geom')))
    params.pop('geom')
    params.pop('layer')
    if 'begin' in params:
        params.pop('begin')
    if 'end' in params:
        params.pop('end')
    if params.get('maxPixels'):
        params['maxPixels'] = int(params['maxPixels'])
    if params.get('tileScale'):
        params['tileScale'] = int(params['tileScale'])
    if params.get('scale'):
        params['scale'] = int(params['scale'])
    else:
        params['scale'] = 90
    if params.get('bestEffort'):
        params['bestEffort'] = bool(params['bestEffort'])
    else:
        params['bestEffort'] = True
    region = ee.Geometry.Polygon(poly)
    reduce_args = {
        'reducer': ee.Reducer.sum(),
        'geometry': region
    }
    reduce_args.update(params)
    area_stats = loss_by_year.divide(1000 * 1000 * 255.0) \
        .multiply(ee.Image.pixelArea()) \
        .reduceRegion(**reduce_args)
    area_results = area_stats.getInfo()
    area = ee.Image.pixelArea().reduceRegion(**reduce_args).get('area')
    percent_stats = loss_by_year.multiply(100.0 / 255.0) \
        .divide(ee.Image.constant(area)) \
        .multiply(ee.Image.pixelArea()) \
        .reduceRegion(**reduce_args)
    percent_results = percent_stats.getInfo()
    if asset_id == 'hansen_all':
        loss = area_results['loss']
        area_results.pop('loss')
        area_results['loss_sum'] = loss
        loss = percent_results['loss']
        percent_results.pop('loss')
        percent_results['loss_sum'] = loss        
    return dict(area=area_results, percent=percent_results)

def _percent(row):
    return row['year'], row['loss_perc']

def _area(row):
    return row['year'], row['loss']

def _cdb(iso, layer):
    if layer == 'sum':
        query = SUM.format(iso=iso)
        result = cdb.execute(query, {})
        if result:
            result = json.loads(result)['rows'][0]
            percent = dict(
                loss_sum=result['loss_perc'],
                treecover_2000=result['treecover_2000_perc'],
                gain=result['gain_perc'])
            area = dict(
                loss_sum=result['loss'],
                treecover_2000=result['treecover_2000'],
                gain=result['gain'])
            return dict(iso=iso, area=area, percent=percent)
    elif layer == 'loss':
        query = ALL.format(iso=iso)
        result = cdb.execute(query, {})
        if result:
            rows = json.loads(result)['rows']
            percent = dict(map(_percent, rows))
            area = dict(map(_area, rows))
            return dict(iso=iso, area=area, percent=percent)


def download(params):
    pass


def analyze(params):
    layer = params.get('layer')
    geom = params.get('geom', None)
    if geom:
        ee.Initialize(config.EE_CREDENTIALS, config.EE_URL)
        geom = json.loads(geom)
        if layer == 'sum':
            result = _ee(params, 'hansen_all')
        else:
            result = _ee(params, 'hansen_loss')
        result['geom'] = geom
        if 'begin' in params and 'end' in params and layer == 'loss':
            sum_results = _ee(params, 'hansen_all')
            result['range'] = _get_range(result, params.get('begin'), params.get('end'))
            
            result['range']['percent']['treecover_2000'] = sum_results['percent']['treecover_2000']
            result['range']['percent']['gain'] = sum_results['percent']['gain']
            
            result['range']['area']['treecover_2000'] = sum_results['area']['treecover_2000']
            result['range']['area']['gain'] = sum_results['area']['gain']
    else:
        iso = params.get('iso', None)
        if iso:
            result = _cdb(iso, layer)
        if 'begin' in params and 'end' in params and layer == 'loss':
            sum_results = _cdb(iso, 'sum')
            result['range'] = _get_range(result, params.get('begin'), params.get('end'))
    
            result['range']['percent']['treecover_2000'] = sum_results['percent']['treecover_2000']
            result['range']['percent']['gain'] = sum_results['percent']['gain']
            
            result['range']['area']['treecover_2000'] = sum_results['area']['treecover_2000']
            result['range']['area']['gain'] = sum_results['area']['gain']
            
    return result

class BaseApi(webapp2.RequestHandler):
    """Base request handler for API."""

    def _send_response(self, data):
        """Sends supplied result dictionnary as JSON response."""
        self.response.headers.add_header("Access-Control-Allow-Origin", "*")
        self.response.headers.add_header(
            'Access-Control-Allow-Headers',
            'Origin, X-Requested-With, Content-Type, Accept')
        self.response.headers.add_header('charset', 'utf-8')
        self.response.headers["Content-Type"] = "application/json"
        if not data:
            self.response.out.write('')
        else:
            self.response.out.write(data)

    def _get_id(self, params):
        whitespace = re.compile(r'\s+')
        params = re.sub(whitespace, '', json.dumps(params, sort_keys=True))
        return '/'.join([self.request.path.lower(), md5(params).hexdigest()])

    def _get_params(self, body=False):
        if body:
            params = json.loads(self.request.body)
        else:
            args = self.request.arguments()
            vals = map(self.request.get, args)
            logging.info('ARGS %s VALS %s' % (args, vals))
            params = dict(zip(args, vals))
        return params

    def options(self):
        """Options to support CORS requests."""
        self.response.headers['Access-Control-Allow-Origin'] = '*'
        self.response.headers['Access-Control-Allow-Headers'] = \
            'Origin, X-Requested-With, Content-Type, Accept'
        self.response.headers['Access-Control-Allow-Methods'] = 'POST, GET'

class Backend(BaseApi):
    """Handler for backend requests."""

    def start(self):
        logging.info('BACKEND START')

    def api(self):
        import os
        logging.info('BACKEND API %s' % os.environ)
        from gfw.api import Entry
        params = self._get_params()
        rid = self._get_id(params)
        entry = Entry.get_by_id(rid)
        if not entry or params.get('bust') or runtime_config.get('IS_DEV'):
            if params.get('bust'):
                params.pop('bust')
            value = analyze(params)
            entry = Entry(id=rid, value=json.dumps(value))
            entry.put()
        self._send_response(entry.value)


routes = [
    webapp2.Route(r'/_ah/start', handler=Backend,
                  handler_method='start'),
    webapp2.Route(r'/backend/datasets/hansen', handler=Backend,
                  handler_method='api')]


handlers = webapp2.WSGIApplication(routes, debug=True)

