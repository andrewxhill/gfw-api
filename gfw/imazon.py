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

# Query template for defor by years for all of BRA:
ALL_SQL = """SELECT SUM(total)
FROM
  (SELECT ano, count(*) as total
   FROM imazon_sad_desmatame
   WHERE date(ano || '-12-31') >= date('%s')
         AND date(ano || '-01-01') <= date('%s')
   GROUP BY ano) AS alias"""

# Query template for defor by years for a GeoJSON polygon:
GEOJSON_SQL = """SELECT SUM(total)
FROM
  (SELECT ano, count(*) as total
   FROM imazon_sad_desmatame
   WHERE date(ano || '-12-31') >= date('%s')
         AND date(ano || '-01-01') <= date('%s')
         AND ST_Intersects(the_geom,ST_SetSRID(ST_GeomFromGeoJSON('%s'), 4326))
   GROUP BY ano) AS alias"""


def get_defor(start, end, geojson=None):
    """ """
    if geojson:
        query = GEOJSON_SQL % (start, end, json.dumps(geojson))
    else:
        query = ALL_SQL % (start, end)
    return cdb.execute(query)['rows'][0]['sum']
