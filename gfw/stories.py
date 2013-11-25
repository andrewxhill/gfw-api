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

"""This module supports stories."""

import json
import logging
from gfw import cdb

INSERT = """INSERT INTO community_stories
  (details, email, featured, name, title, token, visible, date, location,
   the_geom, media)
  VALUES
  ('{details!s}', '{email!s}', {featured}::boolean, '{name!s}', '{title!s}',
   '{token!s}', {visible}::boolean, '{date}'::date, '{location!s}',
   ST_SetSRID(ST_GeomFromGeoJSON('{geom}'), 4326), '{media}')"""

LIST = """SELECT details, email, featured, name, title, visible, date,
    location, cartodb_id as id, ST_AsGeoJSON(the_geom) as geom, media
FROM community_stories
WHERE visible = True {and_where}"""


GET = """SELECT details, email, featured, name, title, visible, date,
    location, cartodb_id as id, ST_AsGeoJSON(the_geom) as geom, media
FROM community_stories
WHERE cartodb_id = {id}"""


def _prep_story(story):
    logging.info("STORY %s" % story)
    if 'geom' in story:
        story['geom'] = json.loads(story['geom'])
    if 'media' in story:
        story['media'] = json.loads(story['media'])
    return story


def create(params):
    """Create new story with params."""
    props = dict(details='', email='', featured='False', name='',
                 title='', token='', visible='True', date='null',
                 location='', geom='', media='[]')
    props.update(params)
    props['geom'] = json.dumps(props['geom'])
    if 'media' in props:
        props['media'] = json.dumps(props['media'])
    return cdb.execute(INSERT.format(**props), api_key=True)


def list(params):
    and_where = ''
    if 'geom' in params:
        and_where = """AND ST_Intersects(the_geom::geography,
            ST_SetSRID(ST_GeomFromGeoJSON('{geom}'),4326)::geography)"""
    if 'since' in params:
        and_where += """ AND date >= '{since}'::date"""
    if and_where:
        and_where = and_where.format(**params)
    result = cdb.execute(LIST.format(and_where=and_where), api_key=True)
    if result:
        data = json.loads(result)
        if 'total_rows' in data and data['total_rows'] > 0:
            return map(_prep_story, data['rows'])


def get(params):
    result = cdb.execute(GET.format(**params), api_key=True)
    if result:
        data = json.loads(result)
        if 'total_rows' in data and data['total_rows'] == 1:
            story = data['rows'][0]
            return _prep_story(story)
            # if 'geom' in story:
            #     story['geom'] = json.loads(story['geom'])
            # if 'media' in story:
            #     story['media'] = json.loads(story['media'])
            # return story
