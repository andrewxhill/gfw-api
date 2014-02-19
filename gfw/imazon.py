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

"""This module supports accessing imazon data."""

import json
from gfw import cdb

# Download entire layer:
DOWNLOAD = """SELECT *
FROM imazon_clean2
WHERE ST_ISvalid(the_geom)
  AND date >= '{begin}'::date
  AND date <= '{end}'::date"""

# Download within supplied GeoJSON:
DOWNLOAD_GEOM = """SELECT ST_Intersection(imazon.the_geom,
  ST_SetSRID(ST_GeomFromGeoJSON('{geom}'),4326)) the_geom,
  data_type disturbance, to_char(date, 'YYYY-MM-DD') date
  FROM imazon_clean2 imazon
  WHERE ST_SetSRID(ST_GeomFromGeoJSON('{geom}'),4326) && imazon.the_geom
  AND ST_ISvalid(imazon.the_geom)
  AND date >= '{begin}'::date
  AND date <= '{end}'::date"""

ANALYSIS = """SELECT data_type, sum(ST_Area(the_geom_webmercator)) AS value,
'Imazon' AS name, 'hectares' AS units
FROM imazon_clean2
WHERE date > '{begin}'::date
AND date <= '{end}'::date
GROUP BY data_type"""


ANALYSIS_GEOM = """SELECT data_type disturbance, SUM(ST_Area(ST_Intersection(the_geom::geography,
  ST_SetSRID(ST_GeomFromGeoJSON('{geom}'),4326)::geography))) AS value,
  'Imazon' AS name, 'hectares' AS units
  FROM imazon_clean2
  WHERE ST_SetSRID(ST_GeomFromGeoJSON('{geom}'),4326) && the_geom
  AND ST_ISvalid(the_geom)
  AND date >= '{begin}'::date
  AND date <= '{end}'::date
  GROUP BY data_type"""


def download(params):
    if 'geom' in params:
        query = DOWNLOAD_GEOM.format(**params)
    else:
        query = DOWNLOAD.format(**params)
    return cdb.get_url(query, params)


def analyze(params):
    if 'geom' in params:
        query = ANALYSIS_GEOM.format(**params)
    elif 'iso' in params:
        iso = params.get('iso').upper()
        if iso == 'BRA':
            query = ANALYSIS.format(**params)
        else:
            query = "select * from imazon_clean2 where orig_oid = '-999'"
    return cdb.execute(query)


def parse_analysis(content):
    try:
        result = json.loads(content)['rows']
        if result:
            result[0]['value'] = result[0]['value'] / 10000.0
            result[1]['value'] = result[1]['value'] / 10000.0
        else:
            result = [
                {
                    "units": "hectares",
                    "value": 0,
                    "data_type": "degrad",
                    "name": "Imazon"
                },
                {
                    "units": "hectares",
                    "value": 0,
                    "data_type": "defor",
                    "name": "Imazon"
                }
            ]
        return result
    except:
        return [
            {
                "units": "hectares",
                "value": 0,
                "data_type": "degrad",
                "name": "Imazon"
            },
            {
                "units": "hectares",
                "value": 0,
                "data_type": "defor",
                "name": "Imazon"
            }
        ]
