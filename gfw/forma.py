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

FORMA_TABLE = 'forma_api'

ISO_SUB_SQL = """SELECT SUM(count) as value, 'FORMA' as name, 'alerts' as unit,
  '500 meters' as resolution
FROM
  (SELECT COUNT(*), iso, date
   FROM %s
   WHERE iso = upper('{iso}')
         AND date <= now() - INTERVAL '1 Months'
   GROUP BY date, iso
   ORDER BY iso, date) AS alias""" % FORMA_TABLE

GEOJSON_SUB_SQL = """SELECT SUM(count) as value, 'FORMA' as name,
  'alerts' as unit, '500 meters' as resolution
FROM
  (SELECT COUNT(*) AS count
   FROM %s
   WHERE date <= now() - INTERVAL '1 Months'
     AND ST_INTERSECTS(ST_SetSRID(ST_GeomFromGeoJSON('{geom!s}'), 4326),
        the_geom)
   GROUP BY date, iso
   ORDER BY iso, date) AS alias""" % FORMA_TABLE

ISO_SQL = """SELECT SUM(count) as value, 'FORMA' as name, 'alerts' as unit,
  '500 meters' as resolution
FROM
  (SELECT COUNT(*), iso, date
   FROM %s
   WHERE iso = upper('{iso}')
         AND date >= '{begin}'
         AND date <= '{end}'
   GROUP BY date, iso
   ORDER BY iso, date) AS alias""" % FORMA_TABLE

ISO_GEOM_SQL = """SELECT *
   FROM %s
   WHERE iso = upper('{iso}')
         AND date >= '{begin}'
         AND date <= '{end}'""" % FORMA_TABLE

GEOJSON_SQL = """SELECT SUM(count) as value, 'FORMA' as name, 'alerts' as unit,
  '500 meters' as resolution
FROM
  (SELECT COUNT(*) AS count
   FROM %s
   WHERE date >= '{begin}'
     AND date <= '{end}'
     AND ST_INTERSECTS(ST_SetSRID(ST_GeomFromGeoJSON('{geom}'), 4326),
        the_geom)
   GROUP BY date, iso
   ORDER BY iso, date) AS alias""" % FORMA_TABLE

GEOJSON_GEOM_SQL = """SELECT *
   FROM %s
   WHERE date >= '{begin}'
     AND date <= '{end}'
     AND ST_INTERSECTS(ST_SetSRID(ST_GeomFromGeoJSON('{geom}'), 4326),
        the_geom)""" % FORMA_TABLE

ALERTS_ALL_COUNTRIES = """SELECT countries.iso, countries.name,
  countries.enabled, countries.lat, countries.lng, countries.extent,
  countries.gva, countries.gva_percent, countries.employment, countries.indepth,
  countries.national_policy_link, countries.national_policy_title,
  countries.convention_cbd, countries.convention_unfccc,
  countries.convention_kyoto, countries.convention_unccd,
  countries.convention_itta, countries.convention_cites,
  countries.convention_ramsar, countries.convention_world_heritage,
  countries.convention_nlbi, countries.convention_ilo, countries.ministry_link,
  countries.external_links, countries.dataset_link, countries.emissions,
  countries.carbon_stocks, alerts.count AS alerts_count
  FROM gfw2_countries AS countries
  LEFT OUTER JOIN (
      SELECT COUNT(*) AS count, iso
      FROM %s
      WHERE date >= now() - INTERVAL '{interval}'
      GROUP BY iso)
  AS alerts ON alerts.iso = countries.iso""" % FORMA_TABLE

ALERTS_ALL_COUNT = """SELECT sum(alerts.count) AS alerts_count
  FROM gfw2_countries AS countries
  LEFT OUTER JOIN (
    SELECT COUNT(*) AS count, iso
      FROM %s
      WHERE date >= now() - INTERVAL '12 Months'
      GROUP BY iso)
  AS alerts ON alerts.iso = countries.iso""" % FORMA_TABLE

ALERTS_COUNTRY = """SELECT countries.iso, countries.name,
  countries.enabled, countries.lat, countries.lng, countries.extent,
  countries.gva, countries.gva_percent, countries.employment, countries.indepth,
  countries.national_policy_link, countries.national_policy_title,
  countries.convention_cbd, countries.convention_unfccc,
  countries.convention_kyoto, countries.convention_unccd,
  countries.convention_itta, countries.convention_cites,
  countries.convention_ramsar, countries.convention_world_heritage,
  countries.convention_nlbi, countries.convention_ilo, countries.ministry_link,
  countries.external_links, countries.dataset_link, countries.emissions,
  countries.carbon_stocks, alerts.count AS alerts_count, alerts.iso
  FROM gfw2_countries AS countries
  RIGHT OUTER JOIN (
      SELECT COUNT(*) AS count, iso
      FROM %s
      WHERE date >= now() - INTERVAL '12 MONTHS'
      AND iso = upper('{iso}')
      GROUP BY iso)
  AS alerts ON alerts.iso = countries.iso""" % FORMA_TABLE


def alerts(params):
    query = ALERTS_ALL_COUNT.format(**params)
    alerts_count = json.loads(
        cdb.execute(query, params))['rows'][0]['alerts_count']
    if 'iso' in params:
        query = ALERTS_COUNTRY.format(**params)
        result = cdb.execute(query, params)
        if result:
            result = json.loads(result)['rows']
    elif 'geom' in params:
        query = ALERTS_ALL_COUNTRIES.format(**params)
        result = cdb.execute(query, params)
        if result:
            result = json.loads(result)['rows']
    else:
        raise AssertionError('geom or iso parameter required')
    return dict(total_count=alerts_count, countries=result)


def download(params):
    """Return CartoDB download URL for supplied parameters."""
    if 'geom' in params:
        query = GEOJSON_GEOM_SQL.format(**params)
    elif 'iso' in params:
        query = ISO_GEOM_SQL.format(**params)
    else:
        raise ValueError('FORMA download expects geom or iso parameter')
    return cdb.get_url(query, params=dict(format=params['format']))


def analyze(params):
    if 'geom' in params:
        query = GEOJSON_SQL.format(**params)
    elif 'iso' in params:
        query = ISO_SQL.format(**params)
    else:
        raise ValueError('FORMA analysis expects geom or iso parameter')
    return cdb.execute(query)


def parse_analysis(content):
    return json.loads(content)['rows'][0]


def subsription(params):
    if 'geom' in params:
        params['geom'] = json.dumps(params.get('geom'))
        query = GEOJSON_SUB_SQL.format(**params)
    elif 'iso' in params:
        query = ISO_SUB_SQL.format(**params)
    else:
        raise ValueError('FORMA subscription expects geom or iso param')
    return cdb.execute(query)
