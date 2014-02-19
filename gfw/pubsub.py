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
import webapp2
import monitor
from gfw import polyline
from gfw import forma
from gfw import cdb
from appengine_config import runtime_config
from google.appengine.ext import ndb
from google.appengine.api import mail
from google.appengine.api import taskqueue
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler


class Subscription(ndb.Model):
    topic = ndb.StringProperty()
    email = ndb.StringProperty()
    params = ndb.JsonProperty()
    confirmed = ndb.BooleanProperty(default=False)
    created = ndb.DateTimeProperty(auto_now_add=True)

    @classmethod
    def get_by_topic(cls, topic):
        """Return all confirmed Subscription entities for supplied topic."""
        return cls.query(cls.topic == topic, cls.confirmed == True).iter()

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
    s = Subscription(topic=topic, email=email, params=params).put()
    reply_to = 'sub+%s@gfw-apis.appspotmail.com' % s.urlsafe()
    conf_url = '%s/pubsub/confirm?token=%s' % \
        (runtime_config['APP_BASE_URL'], s.urlsafe())
    mail.send_mail(
        sender=reply_to,
        to=email,
        reply_to=reply_to,
        subject='You subscribed to Global Forest Watch',
        body="""To receive updates for %s just reply to this email or click
here:\n%s""" % (topic, conf_url))


def unsubscribe(params):
    topic, email = map(params.get, ['topic', 'email'])
    Subscription.unsubscribe(topic, email)


class Subscriber(InboundMailHandler):
    def receive(self, message):
        if message.to.find('<') > -1:
            urlsafe = message.to.split('<')[1].split('+')[1].split('@')[0]
        else:
            urlsafe = message.to.split('+')[1].split('@')[0]
        s = ndb.Key(urlsafe=urlsafe).get()
        s.confirmed = True
        s.put()


class Notifier(webapp2.RequestHandler):

    def _body(self, alert, n, e, s):
        body = """You have subscribed to forest change alerts through Global Forest Watch. This message reports new forest change alerts for one of your areas of interest (a country or self-drawn polygon).

A total of {value} {name} {unit} were detected within your area of interest in the past {interval}. Explore the details of this dataset on Global Forest Watch <a href="http://globalforestwatch.com/sources#forest_change">here</a>. 

Your area of interest is {aoi}, as shown in the map below:

{aoi-vis}

You can unsubscribe or manage your subscriptions by emailing: gfw@wri.org 

You will receive a separate e-mail for each distinct polygon, country, or shape on the GFW map. You will also receive a separate e-mail for each dataset for which you have requested alerts (FORMA alerts, Imazon SAD Alerts, and NASA QUICC alerts.)

Please note that this information is subject to the Global Forest Watch <a href='http://globalforestwatch.com/terms'>Terms of Service</a>.
"""

        html = """You have subscribed to forest change alerts through Global Forest Watch. This message reports new forest change alerts for one of your areas of interest (a country or self-drawn polygon).
<p>
A total of {value} {name} {unit} were detected within your area of interest in the past {interval}. Explore the details of this dataset on Global Forest Watch <a href="http://globalforestwatch.com/sources#forest_change">here</a>. 
<p>
Your area of interest is {aoi}, as shown in the map below:
<p>
{aoi-vis}
<p>
You can unsubscribe or manage your subscriptions by emailing: gfw@wri.org 
<p>
You will receive a separate e-mail for each distinct polygon, country, or shape on the GFW map. You will also receive a separate e-mail for each dataset for which you have requested alerts (FORMA alerts, Imazon SAD Alerts, and NASA QUICC alerts.)
<p>
Please note that this information is subject to the Global Forest Watch <a href='http://globalforestwatch.com/terms'>Terms of Service</a>.
"""

        alert['interval'] = 'month'
        if not alert['value']:
            alert['value'] = 0
        if 'geom' in s:
            alert['aoi'] = 'a user drawn polygon'
            coords = json.loads(s['geom'])['coordinates'][0][0]
            coords = [[float(j) for j in i] for i in coords]
            poly = polyline.encode_coords(coords)
            url = u"http://maps.googleapis.com/maps/api/staticmap?sensor=false&size=600x400&path=fillcolor:0xAA000033|color:0xFFFFFF00|enc:%s" % poly
            alert['aoi-vis'] = '<img src="%s">' % url
        else:
            alert['aoi'] = 'a country (%s)' % s['iso']
            sql = "SELECT ST_AsGeoJSON(ST_ConvexHull(the_geom)) FROM world_countries where iso3 = upper('%s')" % s['iso']
            response = cdb.execute(sql)
            if response.status_code == 200:
                result = json.loads(response.content)
                coords = json.loads(result['rows'][0]['st_asgeojson'])['coordinates']
                poly = polyline.encode_coords(coords[0])
                url = "http://maps.googleapis.com/maps/api/staticmap?sensor=false&size=600x400&path=fillcolor:0xAA000033|color:0xFFFFFF00|enc:%s" % poly
                alert['aoi-vis'] = '<img src="%s">' % url
            else:
                raise Exception('CartoDB Failed (status=%s, content=%s, \
                                q=%s)' % (response.status_code,
                                          response.content,
                                          sql))
        return body.format(**alert), html.format(**alert)

    def post(self):
        """"""
        try:
            n = ndb.Key(urlsafe=self.request.get('notification')).get()
            e = n.params['event']
            s = n.params['subscription']
            response = forma.subsription(s)
            if response.status_code == 200:
                result = json.loads(response.content)['rows'][0]
                body, html = self._body(result, n, e, s)
                mail.send_mail(
                    sender='noreply@gfw-apis.appspotmail.com',
                    to=s['email'],
                    subject='New Forest Change Alerts from Global Forest Watch',
                    body=body,
                    html=html)
            else:
                raise Exception('CartoDB Failed (status=%s, content=%s)' %
                               (response.status_code, response.content))
        except Exception, e:
            name = e.__class__.__name__
            msg = 'Error: Publish %s (%s)' % (json.dumps(s), name)
            monitor.log(self.request.url, msg, error=e,
                        headers=self.request.headers)


class Confirmer(webapp2.RequestHandler):
    def get(self):
        urlsafe = self.request.get('token')
        if not urlsafe:
            self.error(404)
            return
        try:
            s = ndb.Key(urlsafe=urlsafe).get()
        except:
            self.error(404)
            return
        if not s:
            self.error(404)
            return
        if s.confirmed:
            self.error(404)
            return
        else:
            s.confirmed = True
            s.put()
        self.response.write('Subscription confirmed!')


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
                taskqueue.add(
                    url='/pubsub/notify',
                    queue_name='pubsub-notify',
                    params=dict(notification=n.key.urlsafe(), dry_run=dry_run))
        e.multicasted = True
        e.put()

handlers = webapp2.WSGIApplication([Subscriber.mapping()], debug=True)
