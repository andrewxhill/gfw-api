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

ALL_SQL = """SELECT SUM(ST_Area(the_geom::geography))
AS total_area
FROM sad_polygons_fixed_2
WHERE ST_ISvalid(the_geom)"""

GEOJSON_SQL = """SELECT SUM(ST_Area(ST_Intersection(the_geom::geography,
  ST_SetSRID(ST_GeomFromGeoJSON('%s'),4326)::geography)))
AS total_area
FROM sad_polygons_fixed_2
WHERE ST_SetSRID(ST_GeomFromGeoJSON('%s'),4326) && the_geom
  AND ST_ISvalid(the_geom)"""


def get_defor(geojson=None):
    """ """
    if geojson:
        poly = json.dumps(geojson)
        query = GEOJSON_SQL % (poly, poly)
    else:
        query = ALL_SQL
    return cdb.execute(query)['rows'][0]['total_area']
