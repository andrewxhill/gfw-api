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

ISO_SQL = """SELECT count(*) AS total
FROM modis_forest_change_copy m, world_countries c
WHERE m.date = '%s'
      AND m.country = c.name
      AND c.iso3 = '%s'
LIMIT 1"""

GEOJSON_SQL = """SELECT count(*) AS total
FROM modis_forest_change_copy m, world_countries c
WHERE ST_Intersects(m.the_geom,ST_SetSRID(ST_GeomFromGeoJSON('%s'),4326))
      AND m.date = '%s'
LIMIT 1"""


def get_count_by_iso(iso, date):
    """Return MODIS count for supplied iso and date."""
    query = ISO_SQL % (date, iso.upper())
    return cdb.execute(query)['rows'][0]['total']


def get_count_by_geojson(geojson, date):
    """Return MODIS count for supplied geojson and date."""
    query = GEOJSON_SQL % (json.dumps(geojson), date)
    return cdb.execute(query)['rows'][0]['total']
