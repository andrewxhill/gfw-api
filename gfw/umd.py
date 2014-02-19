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

# import os
# os.environ.pop('GAE_USE_SOCKETS_HTTPLIB')

import json
import ee
import logging
import config
import copy

from gfw import cdb

SUM = """SELECT iso, sum(loss_gt_0) loss, avg(gain) gain
         FROM umd
         WHERE year >= {begin} AND year <= {end} AND iso = upper('{iso}')
         GROUP BY iso"""


def _get_coords(geojson):
    return geojson.get('coordinates')


def _sum_range(data, begin, end):
    return sum(
        [value for key, value in data.iteritems()
            if (int(key) >= int(begin)) and (int(key) <= int(end))])


def _get_umd_range(result, begin, end):
    _sum_range(result.get('area'), begin, end)


def _get_range(result, begin, end):
    loss_area = _sum_range(result.get('loss_area'), begin, end)
    gain_area = _sum_range(result.get('gain_area'), begin, end)
    return dict(loss_area=loss_area, gain_area=gain_area, begin=begin, end=end)


def _ee(urlparams, asset_id):
    params = copy.copy(urlparams)
    loss_by_year = ee.Image(config.assets[asset_id])
    poly = _get_coords(json.loads(params.get('geom')))
    params.pop('geom')
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
    area_stats = loss_by_year.divide(100000 * 10 * 255.0) \
        .multiply(ee.Image.pixelArea()) \
        .reduceRegion(**reduce_args)
    area_results = area_stats.getInfo()
    logging.info(area_results)
    return area_results


def _loss_area(row):
    """Return hectares of loss."""
    return row['year'], row['loss']


def _gain_area(row):
    """Return hectares of gain."""
    return row['year'], row['gain']


def _cdb(params):
    query = SUM.format(**params)
    result = cdb.execute(query, {})
    if result:
        result = json.loads(result.content)['rows'][0]
        return dict(iso=params.get('iso'), loss=result['loss'],
                    gain=result['gain'])


def download(params):
    pass


def analyze(params):
    geom = params.get('geom', None)
    iso = params.get('iso', None)
    if geom:
        ee.Initialize(config.EE_CREDENTIALS, config.EE_URL)
        geom = json.loads(geom)
        gain = _ee(params, 'hansen_all')['gain']
        loss_results = _ee(params, 'hansen_loss')
        loss = _sum_range(loss_results, params.get('begin'), params.get('end'))
        result = {}
        result['gain'] = gain
        result['loss'] = loss
        result['geom'] = geom
        result['begin'] = params['begin']
        result['end'] = params['end']
        result['units'] = 'Ha'
        return result
    elif iso:
        iso = iso.upper()
        result = _cdb(params)
        result['begin'] = params['begin']
        result['end'] = params['end']
        result['units'] = 'Ha'
    else:
        raise AssertionError('geom or iso parameter required')
    result['dataset'] = 'UMD'
    return result
