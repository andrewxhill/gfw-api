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

"""This module supports accessing FORMA data."""

import json
from gfw import cdb

# FORMA table in CDM:
FORMA_TABLE = 'cdm_latest'

# Query template for number of FORMA alerts by ISO and start/end dates.
# (table, iso, start, end)
ISO_SQL = """SELECT SUM(count)
FROM
  (SELECT COUNT(*) AS count, iso, date
   FROM %s
   WHERE iso = '%s'
         AND date >= '%s'
         AND date <= '%s'
   GROUP BY date, iso
   ORDER BY iso, date) AS alias"""

# Query template for FORMA alert count by GeoJSON polygon and start/end dates.
# (table, start, end, geojson)
GEOJSON_SQL = """SELECT SUM(count)
FROM
  (SELECT COUNT(*) AS count, iso, date
   FROM %s
   WHERE date >= '%s'
     AND date <= '%s'
     AND ST_INTERSECTS(ST_SetSRID(ST_GeomFromGeoJSON('%s'), 4326), the_geom)
   GROUP BY date, iso
   ORDER BY iso, date) AS alias"""


def get_alerts_by_iso(iso, start, end):
    """Return aggregated alert count for supplied iso and start/end dates."""
    query = ISO_SQL % (FORMA_TABLE, iso.upper(), start, end)
    return cdb.execute(query)['rows'][0]['sum']


def get_alerts_by_geojson(geojson, start, end):
    """Return FORMA alert count for supplied geojson and start/end dates."""
    query = GEOJSON_SQL % (FORMA_TABLE, start, end, json.dumps(geojson))
    return cdb.execute(query)['rows'][0]['sum']
