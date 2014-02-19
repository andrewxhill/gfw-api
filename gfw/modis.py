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

"""This module supports accessing MODIS data."""

import json
from gfw import cdb

ANALYSIS = """SELECT count(*) AS total {select_geom}
FROM modis_forest_change_copy m, world_countries c
WHERE m.date = '{date}'::date
      AND m.country = c.name
      AND c.iso3 = upper('{iso}')
GROUP BY c.the_geom"""

ANALYSIS_GEOM = """SELECT count(*) AS total {select_geom}
FROM modis_forest_change_copy m, world_countries c
WHERE ST_Intersects(m.the_geom,ST_SetSRID(ST_GeomFromGeoJSON('{geom}'),4326))
      AND m.date = '{date}'::date
GROUP BY c.the_geom"""


def download(params):
    params['select_geom'] = ', c.the_geom'
    geom = params.get('geom')
    if geom:
        query = ANALYSIS_GEOM.format(**params)
    else:
        query = ANALYSIS.format(**params)
    return cdb.get_url(query, params=dict(format=params['format']))


def analyze(params):
    params['select_geom'] = ''
    if 'iso' in params:
        params['iso'] = params['iso'].upper()
    geom = params.get('geom')
    if geom:
        query = ANALYSIS_GEOM.format(**params)
    else:
        query = ANALYSIS.format(**params)
    return cdb.execute(query)


def parse_analysis(content):
    rows = json.loads(content)['rows']
    if rows:
        result = rows[0]
    else:
        result = dict(total=0)
    return result
