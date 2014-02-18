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
import random
import re
import webapp2
import monitor

from gfw import common
from gfw import countries
from gfw import stories
from gfw import pubsub
from gfw import wdpa
from appengine_config import runtime_config
from hashlib import md5
from google.appengine.api import mail
from google.appengine.api import taskqueue
from google.appengine.ext import ndb


class Entry(ndb.Model):
    value = ndb.TextProperty()


# Countries API route
COUNTRY_ROUTE = r'/countries'

# WPDA site API route
WDPA = r'/wdpa/sites'

# Stories API routes
LIST_STORIES = r'/stories'
CREATE_STORY = r'/stories/new'
CREATE_STORY_EMAILS = r'/stories/email'
GET_STORY = r'/stories/<id:\d+>'


class BaseApi(webapp2.RequestHandler):
    """Base request handler for API."""

    def _send_response(self, data, error=None):
        """Sends supplied result dictionnary as JSON response."""
        self.response.headers.add_header("Access-Control-Allow-Origin", "*")
        self.response.headers.add_header(
            'Access-Control-Allow-Headers',
            'Origin, X-Requested-With, Content-Type, Accept')
        self.response.headers.add_header('charset', 'utf-8')
        self.response.headers["Content-Type"] = "application/json"
        if error:
            self.response.set_status(400)
        if not data:
            self.response.out.write('')
        else:
            self.response.out.write(data)
        if error:
            taskqueue.add(url='/log/error', params=error, queue_name="log")

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
        return
        story = self._get_params()

        # Email WRI:
        subject = 'A new story has been registered with Global Forest Watch'
        sender = \
            'Global Forest Watch Stories <noreply@gfw-apis.appspotmail.com>'
        to = runtime_config.get('wri_emails_stories')
        story_url = 'http://globalforestwatch.org/stories/%s' % story['id']
        api_url = '%s/stories/%s' % (common.APP_BASE_URL, story['id'])
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
        try:
            params = self._get_params()
            result = stories.list(params)
            if not result:
                result = []
            self._send_response(json.dumps(result))
        except Exception, e:
            name = e.__class__.__name__
            msg = 'Error: Story API (%s)' % name
            monitor.log(self.request.url, msg, error=e,
                        headers=self.request.headers)

    def create(self):
        params = self._get_params(body=True)
        required = ['title', 'email', 'name', 'geom']
        if not all(x in params and params.get(x) for x in required):
            self.response.set_status(400)
            self._send_response(json.dumps(dict(required=required)))
        params['token'] = self._gen_token()
        result = stories.create(params)
        if result:
            story = json.loads(result.content)['rows'][0]
            story['media'] = json.loads(story['media'])
            self.response.set_status(201)
        else:
            story = None
            self.response.set_status(400)
        taskqueue.add(url='/stories/email', params=story,
                      queue_name="story-new-emails")
        self._send_response(json.dumps(story))

    def get(self, id):
        try:
            params = dict(id=id)
            result = stories.get(params)
            if not result:
                self.response.set_status(404)
            self._send_response(json.dumps(result))
        except Exception, e:
            name = e.__class__.__name__
            msg = 'Error: Story API (%s)' % name
            monitor.log(self.request.url, msg, error=e,
                        headers=self.request.headers)


class WdpaApi(BaseApi):
    def site(self):
        try:
            params = self._get_params()
            rid = self._get_id(params)
            entry = Entry.get_by_id(rid)
            if not entry or params.get('bust') or runtime_config.get('IS_DEV'):
                site = wdpa.get_site(params)
                if site:
                    entry = Entry(id=rid, value=json.dumps(site))
                    entry.put()
            self._send_response(entry.value if entry else None)
        except Exception, e:
            name = e.__class__.__name__
            msg = 'Error: WPDA API (%s)' % name
            monitor.log(self.request.url, msg, error=e,
                        headers=self.request.headers)


class CountryApi(BaseApi):
    """Handler for countries."""

    def get(self):
        try:
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
        except Exception, e:
            name = e.__class__.__name__
            msg = 'Error: Countries API (%s)' % name
            monitor.log(self.request.url, msg, error=e,
                        headers=self.request.headers)


class PubSubApi(BaseApi):

    def subscribe(self):
        try:
            params = self._get_params(body=True)
            pubsub.subscribe(params)
            self.response.set_status(201)
            self._send_response(json.dumps(dict(subscribe=True)))
        except Exception, e:
            name = e.__class__.__name__
            msg = 'Error: PubSub API (%s)' % name
            monitor.log(self.request.url, msg, error=e,
                        headers=self.request.headers)

    def unsubscribe(self):
        try:
            params = self._get_params(body=True)
            pubsub.unsubscribe(params)
            self._send_response(json.dumps(dict(unsubscribe=True)))
        except Exception, e:
            name = e.__class__.__name__
            msg = 'Error: PubSub API (%s)' % name
            monitor.log(self.request.url, msg, error=e,
                        headers=self.request.headers)

    def publish(self):
        try:
            params = self._get_params(body=True)
            pubsub.publish(params)
            self._send_response(json.dumps(dict(publish=True)))
        except Exception, e:
            name = e.__class__.__name__
            msg = 'Error: PubSub API (%s)' % name
            monitor.log(self.request.url, msg, error=e,
                        headers=self.request.headers)


routes = [
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

handlers = webapp2.WSGIApplication(routes, debug=common.IS_DEV)
