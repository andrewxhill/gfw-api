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

ISO_SUB_SQL = """SELECT SUM(count) as value, 'FORMA' as name, 'alerts' as unit,
  '500 meters' as resolution
FROM
  (SELECT COUNT(*), iso, date
   FROM cdm_latest
   WHERE iso ilike '{iso}'
         AND date <= now() - INTERVAL '1 Months'
   GROUP BY date, iso
   ORDER BY iso, date) AS alias"""

GEOJSON_SUB_SQL = """SELECT SUM(count) as value, 'FORMA' as name,
  'alerts' as unit, '500 meters' as resolution
FROM
  (SELECT COUNT(*) AS count
   FROM cdm_latest
   WHERE date <= now() - INTERVAL '1 Months'
     AND ST_INTERSECTS(ST_SetSRID(ST_GeomFromGeoJSON('{geom!s}'), 4326),
        the_geom)
   GROUP BY date, iso
   ORDER BY iso, date) AS alias"""

ISO_SQL = """SELECT SUM(count) as value, 'FORMA' as name, 'alerts' as unit,
  '500 meters' as resolution
FROM
  (SELECT COUNT(*), iso, date
   FROM cdm_latest
   WHERE iso ilike'{iso}'
         AND date >= '{begin}'
         AND date <= '{end}'
   GROUP BY date, iso
   ORDER BY iso, date) AS alias"""

ISO_GEOM_SQL = """SELECT *
   FROM cdm_latest
   WHERE iso ilike'{iso}'
         AND date >= '{begin}'
         AND date <= '{end}'"""

GEOJSON_SQL = """SELECT SUM(count) as value, 'FORMA' as name, 'alerts' as unit,
  '500 meters' as resolution
FROM
  (SELECT COUNT(*) AS count
   FROM cdm_latest
   WHERE date >= '{begin}'
     AND date <= '{end}'
     AND ST_INTERSECTS(ST_SetSRID(ST_GeomFromGeoJSON('{geom}'), 4326),
        the_geom)
   GROUP BY date, iso
   ORDER BY iso, date) AS alias"""

GEOJSON_GEOM_SQL = """SELECT *
   FROM cdm_latest
   WHERE date >= '{begin}'
     AND date <= '{end}'
     AND ST_INTERSECTS(ST_SetSRID(ST_GeomFromGeoJSON('{geom}'), 4326),
        the_geom)"""

ALERTS_ALL_COUNTRIES = """SELECT countries.name, countries.iso,
  countries.enabled, alerts.count AS alerts_count
  FROM gfw2_countries AS countries
  LEFT OUTER JOIN (
      SELECT COUNT(*) AS count, iso
      FROM cdm_latest
      WHERE date >= now() - INTERVAL '{interval}'
      GROUP BY iso)
  AS alerts ON alerts.iso = countries.iso"""

ALERTS_ALL_COUNT = """SELECT sum(alerts.count) AS alerts_count
  FROM gfw2_countries AS countries
  LEFT OUTER JOIN (
    SELECT COUNT(*) AS count, iso
      FROM cdm_latest
      WHERE date >= now() - INTERVAL '12 Months'
      GROUP BY iso)
  AS alerts ON alerts.iso = countries.iso"""

ALERTS_COUNTRY = """SELECT countries.name, countries.iso, countries.enabled,
  alerts.count AS alerts_count, alerts.iso
  FROM gfw2_countries AS countries
  RIGHT OUTER JOIN (
      SELECT COUNT(*) AS count, iso
      FROM cdm_latest
      WHERE date >= now() - INTERVAL '12 MONTHS'
      AND iso = '{iso}'
      GROUP BY iso)
  AS alerts ON alerts.iso = countries.iso"""


def alerts(params):
    query = ALERTS_ALL_COUNT.format(**params)
    alerts_count = json.loads(
        cdb.execute(query, params))['rows'][0]['alerts_count']
    if 'iso' in params:
        query = ALERTS_COUNTRY.format(**params)
        result = cdb.execute(query, params)
        if result:
            result = json.loads(result)['rows']
    else:
        query = ALERTS_ALL_COUNTRIES.format(**params)
        result = cdb.execute(query, params)
        if result:
            result = json.loads(result)['rows']
    return dict(total_count=alerts_count, countries=result)


def download(params):
    geom = params.get('geom')
    if geom:
        query = GEOJSON_GEOM_SQL.format(**params)
    else:
        query = ISO_GEOM_SQL.format(**params)
    return cdb.execute(query, params)


def analyze(params):
    geom = params.get('geom')
    if geom:
        query = GEOJSON_SQL.format(**params)
    else:
        query = ISO_SQL.format(**params)
    result = cdb.execute(query)
    if result:
        result = json.loads(result)['rows'][0]
    return result


def subsription(params):
    geom = params.get('geom')
    if geom:
        params['geom'] = json.dumps(geom)
        query = GEOJSON_SUB_SQL.format(**params)
    else:
        query = ISO_SUB_SQL.format(**params)
    result = cdb.execute(query)
    if result:
        result = json.loads(result)['rows'][0]
    return result
