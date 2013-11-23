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
FROM sad_polygons_fixed_2
WHERE ST_ISvalid(the_geom)
  AND added_on >= '{begin}'::date
  AND added_on <= '{end}'::date"""

# Download within supplied GeoJSON:
DOWNLOAD_GEOM = """SELECT the_geom,
SUM(ST_Area(ST_Intersection(the_geom::geography,
  ST_SetSRID(ST_GeomFromGeoJSON('{geom}'),4326)::geography)))
AS value, 'Imazon' as name, 'meters' as units
FROM sad_polygons_fixed_2
WHERE ST_SetSRID(ST_GeomFromGeoJSON('{geom}'),4326) && the_geom
  AND ST_ISvalid(the_geom)
  AND added_on >= '{begin}'::date
  AND added_on <= '{end}'::date
GROUP BY the_geom"""

# Analyze entire layer:
ANALYSIS = """SELECT SUM(sum) AS value, 'Imazon' as name, 'meters' as units
FROM
  (SELECT SUM(ST_Area(the_geom::geography)) AS sum
   FROM sad_polygons_fixed_2
   WHERE ST_ISvalid(the_geom)
     AND added_on >= '{begin}'::date
     AND added_on <= '{end}'::date
   GROUP BY added_on
   ORDER BY added_on) AS alias"""

# Analyze within supplied GeoJSON:
ANALYSIS_GEOM = """SELECT SUM(ST_Area(ST_Intersection(the_geom::geography,
  ST_SetSRID(ST_GeomFromGeoJSON('{geom}'),4326)::geography))) AS value,
  'Imazon' AS name, 'meters' AS units
FROM sad_polygons_fixed_2
WHERE ST_SetSRID(ST_GeomFromGeoJSON('{geom}'),4326) && the_geom
  AND ST_ISvalid(the_geom)
  AND added_on >= '{begin}'::date
  AND added_on <= '{end}'::date"""


def download(params):
    geom = params.get('geom')
    if geom:
        query = DOWNLOAD_GEOM.format(**params)
    else:
        query = DOWNLOAD.format(**params)
    return cdb.execute(query, params)


def analyze(params):
    geom = params.get('geom')
    if geom:
        query = ANALYSIS_GEOM.format(**params)
    else:
        query = ANALYSIS.format(**params)
    result = cdb.execute(query)
    if result:
        result = json.loads(result)['rows'][0]
    return result
