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

"""This module supports pubsub."""

import json
import logging
import webapp2
from gfw import forma
from google.appengine.ext import ndb
from google.appengine.api import mail
from google.appengine.api import taskqueue


class Subscription(ndb.Model):
    topic = ndb.StringProperty()
    email = ndb.StringProperty()
    params = ndb.JsonProperty()
    created = ndb.DateTimeProperty(auto_now_add=True)

    @classmethod
    def get_by_topic(cls, topic):
        """Return all Subscription entities for supplied topic."""
        return cls.query(cls.topic == topic).iter()

    @classmethod
    def unsubscribe(cls, topic, email):
        x = cls.query(cls.topic == topic, cls.email == email).get()
        if x:
            x.key.delete()


class Event(ndb.Model):
    topic = ndb.StringProperty()
    params = ndb.JsonProperty()
    multicasted = ndb.BooleanProperty(default=False)
    created = ndb.DateTimeProperty(auto_now_add=True)


class Notification(ndb.Model):
    """Key = subscription+event"""
    topic = ndb.StringProperty()
    params = ndb.JsonProperty()  # subscription+event JSON
    sent = ndb.BooleanProperty(default=False)
    created = ndb.DateTimeProperty(auto_now_add=True)

    @classmethod
    def get(cls, event, subscription):
        return cls.get_by_id('%s+%s' % (event.key.id(), subscription.key.id()))

    @classmethod
    def create(cls, event, subscription):
        id = '%s+%s' % (event.key.id(), subscription.key.id())
        return cls(
            id=id,
            topic=event.topic,
            params=dict(event=event.params, subscription=subscription.params))


def publish(params, dry_run=True):
    topic = params['topic']
    event_key = Event(topic=topic, params=params).put()
    taskqueue.add(
        url='/pubsub/publish',
        queue_name='pubsub-publish',
        params=dict(event=event_key.urlsafe(), dry_run=dry_run))


def subscribe(params):
    topic, email = map(params.get, ['topic', 'email'])
    Subscription(topic=topic, email=email, params=params).put()


def unsubscribe(params):
    topic, email = map(params.get, ['topic', 'email'])
    Subscription.unsubscribe(topic, email)


class Notifier(webapp2.RequestHandler):
    def post(self):
        """"""
        n = ndb.Key(urlsafe=self.request.get('notification')).get()
        e = n.params['event']
        s = n.params['subscription']
        # dry_run = self.request.get('dry_run')
        result = forma.subsription(s)
        body = json.dumps(dict(event=e, subscription=s, notification=result),
                          sort_keys=True, indent=4, separators=(',', ': '))
        logging.info("Notify %s to %s" % (n.topic, s['email']))
        mail.send_mail(
            sender='eightysteele@gmail.com', to=s['email'],
            subject='Global Forest Watch data notification',
            body=body)


class Publisher(webapp2.RequestHandler):
    def post(self):
        """Publish notifications to all event subscribers."""
        e = ndb.Key(urlsafe=self.request.get('event')).get()
        dry_run = self.request.get('dry_run', False)
        if not e.multicasted:
            for s in Subscription.get_by_topic(e.topic):
                n = Notification.get(e, s)
                if not n:
                    n = Notification.create(e, s)
                    n.put()
                logging.info("Publish %s to %s" % (s.topic, s.params['email']))
                taskqueue.add(
                    url='/pubsub/notify',
                    queue_name='pubsub-notify',
                    params=dict(notification=n.key.urlsafe(), dry_run=dry_run))
        e.multicasted = True
        e.put()
