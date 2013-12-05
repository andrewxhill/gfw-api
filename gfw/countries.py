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

"""This module supports accessing countries data."""

import json
from gfw import cdb

GET = """SELECT countries.carbon_stocks,
  countries.co2_emissions, countries.convention_cbd,
  countries.convention_cites, countries.convention_ilo,
  countries.convention_itta, countries.convention_kyoto,
  countries.convention_nlbi, countries.convention_ramsar,
  countries.convention_unccd, countries.convention_unfccc,
  countries.convention_world_heritage, countries.dataset_link,
  countries.emissions_land, countries.emissions_noland,
  countries.employment, countries.enabled, countries.external_links,
  countries.forest_extent, countries.gdp_percent, countries.gdp_percent_fixed,
  countries.gross_value, countries.iso, countries.ministry_link,
  countries.name, countries.national_policy_link,
  countries.national_policy_title, countries.tenure_government,
  countries.tenure_owned, countries.tenure_owned_individuals,
  countries.tenure_reserved, countries.type_planted, countries.type_primary,
  countries.type_regenerated, alerts.count AS alerts_count
  FROM gfw2_countries AS countries
  {join} OUTER JOIN (
      SELECT COUNT(*) AS count, iso
      FROM cdm_latest
      WHERE date >= now() - INTERVAL '{interval}'
      {and}
      GROUP BY iso)
  AS alerts ON alerts.iso = countries.iso
  ORDER BY countries.name {order}"""


def get(params):
    if 'iso' in params:
        params['and'] = "AND iso ilike '%s'" % params['iso']
        params['join'] = 'RIGHT'
    else:
        params['and'] = ''
        params['join'] = 'LEFT'
    query = GET.format(**params)
    result = cdb.execute(query, params)
    if result:
        result = json.loads(result)['rows']
    if 'iso' in params:
        result = result[0]
    return result
