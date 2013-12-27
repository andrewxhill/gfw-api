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

"""This module contains request handlers for the Global Forest Watch API."""

import base64
import hashlib
import json
import logging
import random
import re
import webapp2

from gfw import countries
from gfw import forma
from gfw import hansen
from gfw import gcs
from gfw import imazon
from gfw import modis
from gfw import stories
from gfw import pubsub
from gfw import wdpa
from appengine_config import runtime_config
from gfw.common import CONTENT_TYPES, IS_DEV, APP_BASE_URL
from hashlib import md5
from google.appengine.api import mail
from google.appengine.api import taskqueue
from google.appengine.ext import blobstore
from google.appengine.ext import ndb
from google.appengine.ext.webapp import blobstore_handlers


class Entry(ndb.Model):
    value = ndb.TextProperty()


def analyze(dataset, params):
    if dataset == 'imazon':
        return imazon.analyze(params)
    elif dataset == 'forma':
        return forma.analyze(params)
    elif dataset == 'modis':
        return modis.analyze(params)
    elif dataset == 'hansen':
        return hansen.analyze(params)
    return None


def download(dataset, params):
    if dataset == 'imazon':
        return imazon.download(params)
    elif dataset == 'forma':
        return forma.download(params)
    elif dataset == 'modis':
        return modis.download(params)
    return None


ANALYSIS_ROUTE = r'/datasets/<dataset:(imazon|forma|modis|hansen)>'
DOWNLOAD_ROUTE = r'%s.<format:(shp|geojson|kml|svg|csv)>' % ANALYSIS_ROUTE
COUNTRY_ROUTE = r'/countries'
WDPA = r'/wdpa/sites'

# Stories API
LIST_STORIES = r'/stories'
CREATE_STORY = r'/stories/new'
CREATE_STORY_EMAILS = r'/stories/email'
GET_STORY = r'/stories/<id:\d+>'


class DownloadApi(blobstore_handlers.BlobstoreDownloadHandler):

    def _redirect(self, url):
        """Sends supplied result dictionnary as JSON response."""
        self.response.headers.add_header("Access-Control-Allow-Origin", "*")
        self.response.headers.add_header(
            'Access-Control-Allow-Headers',
            'Origin, X-Requested-With, Content-Type, Accept')
        self.response.headers.add_header('charset', 'utf-8')
        self.response.headers["Content-Type"] = "application/json"
        self.redirect(str(url))

    def _get_id(self, params):
        path, format = self.request.path.lower().split('.')
        logging.info('FORMAT %s' % format)
        format = format if format != 'shp' else 'zip'
        logging.info('FORMAT %s' % format)
        whitespace = re.compile(r'\s+')
        params = re.sub(whitespace, '', json.dumps(params, sort_keys=True))
        return '%s/%s.%s' % (path, md5(params).hexdigest(), format)

    def download(self, dataset, format):
        args = self.request.arguments()
        vals = map(self.request.get, args)
        params = dict(zip(args, vals))
        params['format'] = format
        rid = self._get_id(params)
        entry = Entry.get_by_id(rid)
        if not entry or params.get('bust') or runtime_config.get('IS_DEV'):
            data = download(dataset, params)
            logging.info("DOWNLOAD %s" % data)
            if data:
                if data.startswith('http://'):
                    entry = Entry(id=rid, value=data)
                    entry.put()
                else:
                    content_type = CONTENT_TYPES[format]
                    gcs_path = gcs.create_file(data, rid, content_type)
                    value = blobstore.create_gs_key(gcs_path)
                    entry = Entry(id=rid, value=value)
                    entry.put()
        if entry.value:
            if entry.value.startswith('http://'):
                self._redirect(entry.value)
            else:
                self.send_blob(entry.value)
        else:
            self.error(404)


class BaseApi(webapp2.RequestHandler):
    """Base request handler for API."""

    def _send_response(self, data):
        """Sends supplied result dictionnary as JSON response."""
        self.response.headers.add_header("Access-Control-Allow-Origin", "*")
        self.response.headers.add_header(
            'Access-Control-Allow-Headers',
            'Origin, X-Requested-With, Content-Type, Accept')
        self.response.headers.add_header('charset', 'utf-8')
        self.response.headers["Content-Type"] = "application/json"
        if not data:
            self.response.out.write('')
        else:
            self.response.out.write(data)

    def _get_id(self, params):
        whitespace = re.compile(r'\s+')
        params = re.sub(whitespace, '', json.dumps(params, sort_keys=True))
        return '/'.join([self.request.path.lower(), md5(params).hexdigest()])

    def _get_params(self, body=False):
        if body:
            params = json.loads(self.request.body)
        else:
            args = self.request.arguments()
            vals = map(self.request.get, args)
            logging.info('ARGS %s VALS %s' % (args, vals))
            params = dict(zip(args, vals))
        return params

    def options(self):
        """Options to support CORS requests."""
        self.response.headers['Access-Control-Allow-Origin'] = '*'
        self.response.headers['Access-Control-Allow-Headers'] = \
            'Origin, X-Requested-With, Content-Type, Accept'
        self.response.headers['Access-Control-Allow-Methods'] = 'POST, GET'


class StoriesApi(BaseApi):

    def _send_new_story_emails(self):
        story = self._get_params()

        # Email WRI:
        subject = 'A new story has been registered with Global Forest Watch'
        sender = \
            'Global Forest Watch Stories <noreply@gfw-apis.appspotmail.com>'
        to = runtime_config.get('wri_emails_stories')
        story_url = 'http://gfw-beta.org/stories/%s' % story['id']
        api_url = '%s/stories/%s' % (APP_BASE_URL, story['id'])
        token = story['token']
        body = 'Story URL: %s\nStory API: %s\nStory token: %s' % \
            (story_url, api_url, token)
        mail.send_mail(sender=sender, to=to, subject=subject, body=body)

        # Email user:
        subject = 'Your story has been registered with Global Forest Watch!'
        to = '%s <%s>' % (story['name'], story['email'])
        body = 'Here is your story: %s' % story_url
        mail.send_mail(sender=sender, to=to, subject=subject, body=body)

    def _gen_token(self):
        return base64.b64encode(
            hashlib.sha256(str(random.getrandbits(256))).digest(),
            random.choice(
                ['rA', 'aZ', 'gQ', 'hH', 'hG', 'aR', 'DD'])).rstrip('==')

    def list(self):
        params = self._get_params()
        result = stories.list(params)
        if not result:
            result = []
        self._send_response(json.dumps(result))

    def create(self):
        params = self._get_params(body=True)
        required = ['title', 'email', 'name', 'geom']
        if not all(x in params and params.get(x) for x in required):
            self.response.set_status(400)
            self._send_response(json.dumps(dict(required=required)))
        params['token'] = self._gen_token()
        result = stories.create(params)
        if result:
            story = json.loads(result)['rows'][0]
            story['media'] = json.loads(story['media'])
            self.response.set_status(201)
        else:
            story = None
            self.response.set_status(400)
        taskqueue.add(url='/stories/email', params=story,
                      queue_name="story-new-emails")
        self.response.out.write(story)

    def get(self, id):
        params = dict(id=id)
        result = stories.get(params)
        if not result:
            self.response.set_status(404)
        self._send_response(json.dumps(result))


class AnalyzeApi(BaseApi):
    """Handler for aggregated defor values for supplied dataset and polygon."""

    def analyze(self, dataset):
        params = self._get_params()
        rid = self._get_id(params)
        entry = Entry.get_by_id(rid)
        if not entry or params.get('bust') or runtime_config.get('IS_DEV'):
            value = analyze(dataset, params)
            entry = Entry(id=rid, value=json.dumps(value))
            entry.put()
        self._send_response(entry.value)


class WdpaApi(BaseApi):
    def site(self):
        params = self._get_params()
        rid = self._get_id(params)
        entry = Entry.get_by_id(rid)
        if not entry or params.get('bust') or runtime_config.get('IS_DEV'):
            site = wdpa.get_site(params)
            if site:
                entry = Entry(id=rid, value=json.dumps(site))
                entry.put()
        self._send_response(entry.value if entry else None)


class CountryApi(BaseApi):
    """Handler for countries."""

    def get(self):
        params = self._get_params()
        rid = self._get_id(params)
        if 'interval' not in params:
            params['interval'] = '12 MONTHS'
        entry = Entry.get_by_id(rid)
        if not entry or params.get('bust') or runtime_config.get('IS_DEV'):
            result = countries.get(params)
            if result:
                entry = Entry(id=rid, value=json.dumps(result))
                entry.put()
        self._send_response(entry.value if entry else None)



class PubSubApi(BaseApi):

    def subscribe(self):
        params = self._get_params(body=True)
        pubsub.subscribe(params)
        self.response.set_status(201)
        self._send_response(json.dumps(dict(subscribe=True)))

    def unsubscribe(self):
        params = self._get_params(body=True)
        pubsub.unsubscribe(params)
        self._send_response(json.dumps(dict(unsubscribe=True)))

    def publish(self):
        params = self._get_params(body=True)
        pubsub.publish(params)
        self._send_response(json.dumps(dict(publish=True)))

routes = [
    webapp2.Route(ANALYSIS_ROUTE, handler=AnalyzeApi,
                  handler_method='analyze'),
    webapp2.Route(DOWNLOAD_ROUTE, handler=DownloadApi,
                  handler_method='download'),
    webapp2.Route(COUNTRY_ROUTE, handler=CountryApi,
                  handler_method='get'),
    webapp2.Route(CREATE_STORY, handler=StoriesApi,
                  handler_method='create', methods=['POST']),
    webapp2.Route(LIST_STORIES, handler=StoriesApi,
                  handler_method='list'),
    webapp2.Route(GET_STORY, handler=StoriesApi,
                  handler_method='get'),
    webapp2.Route(WDPA, handler=WdpaApi,
                  handler_method='site'),
    webapp2.Route(CREATE_STORY_EMAILS, handler=StoriesApi,
                  handler_method='_send_new_story_emails',
                  methods=['POST']),
    webapp2.Route(r'/pubsub/publish', handler=pubsub.Publisher,
                  handler_method='post',
                  methods=['POST']),
    webapp2.Route(r'/pubsub/confirm', handler=pubsub.Confirmer,
                  handler_method='get',
                  methods=['GET']),
    webapp2.Route(r'/pubsub/notify', handler=pubsub.Notifier,
                  handler_method='post',
                  methods=['POST']),
    webapp2.Route(r'/subscribe', handler=PubSubApi,
                  handler_method='subscribe',
                  methods=['POST']),
    webapp2.Route(r'/unsubscribe', handler=PubSubApi,
                  handler_method='unsubscribe',
                  methods=['POST']),
    webapp2.Route(r'/publish', handler=PubSubApi,
                  handler_method='publish',
                  methods=['POST'])
]

handlers = webapp2.WSGIApplication(routes, debug=IS_DEV)
