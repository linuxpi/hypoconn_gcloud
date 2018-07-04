import os
import json
import time

import webapp2
import jinja2
import stripe
import datetime

from google.appengine.ext import ndb

import requests_toolbelt.adapters.appengine

# Use the App Engine Requests adapter. This makes sure that Requests uses
# URLFetch.
requests_toolbelt.adapters.appengine.monkeypatch()

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'stripe_demo')),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


# Configure stripe
stripe.api_key = 'sk_test_Yg0ufLCJzXD4F5utQxpixepk'


class Item(ndb.Model):
    """
    To Store scraped tokens for users
    """
    name = ndb.StringProperty()
    cost = ndb.IntegerProperty()


class Dispute(ndb.Model):

    dispute_id = ndb.StringProperty()
    status = ndb.StringProperty()
    amount = ndb.IntegerProperty()
    reason = ndb.StringProperty()


class Transaction(ndb.Model):
    charge_id = ndb.StringProperty()
    dispute = ndb.KeyProperty(kind=Dispute)


class ListPage(webapp2.RequestHandler):

    def get(self):
        items = Item.query().fetch()
        template = JINJA_ENVIRONMENT.get_template('list.html')
        self.response.write(template.render({
            'items': items
        }))


class ChargePage(webapp2.RequestHandler):

    def post(self):
        token = self.request.get('stripeToken')
        # item = ndb.Key(urlsafe=self.request.get('item')).get()
        charge = stripe.Charge.create(
            amount=50,
            description='test',
            source=token,
            currency='usd',
        )
        # transaction = Transaction(charge_id=charge.id)
        # transaction.put()
        self.redirect('/')


class DisputeHook(webapp2.RequestHandler):

    def post(self):
        print self.request.body
        event = json.loads(self.request.body)
        dispute_id = event['data']['object']['id']
        dispute = Dispute.query(Dispute.dispute_id == dispute_id).get()
        transaction = Transaction.query(Transaction.charge_id == event['data']['object']['charge']).get()

        if not dispute:
            dispute = Dispute(dispute_id=dispute_id)

        dispute.status = event['type']
        dispute.amount = event['data']['object']['amount']
        dispute.reason = event['data']['object']['reason']

        dispute.put()

        transaction.dispute = dispute.key
        transaction.put()


class AdminPage(webapp2.RequestHandler):

    def get(self):
        template = JINJA_ENVIRONMENT.get_template('admin.html')
        self.response.write(template.render({
            'transactions': Transaction.query().fetch(20)
        }))


application = webapp2.WSGIApplication([
    ('/', ListPage),
    ('/charge', ChargePage),
    ('/dispute', DisputeHook),
    ('/admin', AdminPage),
], debug=True)