import stripe
import webapp2
from time import mktime
import datetime
import logging
import json

from google.appengine.ext import db
from google.appengine.api import users


class Dispute(db.Model):
  """
  Model to keep dispute data.
  Using key_name to store stripe dispute id
  """

  PIKA = 'pika'
  RENEW = 'renew'
  FRESH = 'fresh'

  email = db.StringProperty()
  amount_cents = db.IntegerProperty()
  transaction_type = db.StringProperty()  # Subscription(Fresh, Renew) or Pika
  charge_id = db.StringProperty()  # Stripe charge id
  charge_created_at = db.DateTimeProperty()
  charge_description = db.TextProperty()
  currency = db.StringProperty()
  country = db.StringProperty()
  dispute_created_at = db.DateTimeProperty()
  dispute_status = db.StringProperty()
  dispute_reason = db.StringProperty()
  last_event = db.DateTimeProperty()  # Last dispute update(event) received through webhook
  created_at = db.DateTimeProperty(auto_now_add=True)


class UserCCTransactions(db.Model):

  email = db.StringProperty()
  ref = db.StringProperty()
  is_auto_renewed = db.BooleanProperty(default=False)


def fetch_all_disputes():
  stripe.api_key = 'sk_test_Yg0ufLCJzXD4F5utQxpixepk'

  try:
    disputes = stripe.Dispute.list(
      created={'gt': int(mktime((datetime.datetime.now() - datetime.timedelta(30)).timetuple()))}
    )
  except stripe.StripeError as se:
    logging.error('Failed to fetch disputes from stripe. Error - {}'.format(se.message))
  else:
    for dispute in disputes.data:
      dispute_id = dispute.id
      charge_id = dispute.charge

      try:
        charge = stripe.Charge.retrieve(charge_id)
      except stripe.StripeError as se:
        logging.error('Failed to fetch charge from stripe. Error - {}'.format(se.message))
      else:
        transaction = UserCCTransactions.all().filter('ref', str(charge_id)).get()
        transaction_type = Dispute.PIKA if transaction is None else (
          Dispute.RENEW if transaction.is_auto_renewed else Dispute.FRESH
        )
        dispute_obj = Dispute.all().filter('key_name', dispute_id).get()
        if not dispute_obj:
          dispute_obj = Dispute(
            key_name=dispute_id,
            email=charge.source.name,
            amount_cents=charge.amount,
            transaction_type=transaction_type,
            charge_id=charge_id,
            charge_created_at=datetime.datetime.utcfromtimestamp(charge.created),
            charge_description=charge.description,
            currency=charge.currency,
            country=charge.source.country,
            dispute_created_at=datetime.datetime.utcfromtimestamp(dispute.created),
            dispute_status=dispute.status,
            dispute_reason=dispute.reason,
            last_event=datetime.datetime.utcfromtimestamp(dispute.created),
          )
        else:
          dispute_obj.dispute_status = dispute.status
          dispute_obj.dispute_reason = dispute.reason
          dispute_obj.last_event = datetime.datetime.utcfromtimestamp(dispute.created)

        dispute_obj.put()


class DisputeHook(webapp2.RequestHandler):

  def get(self):
    fetch_all_disputes()
    return self.response.write("all ok! {}".format(users.get_current_user()))

  def post(self):
    json_data = json.loads(self.request.body)
    object_type = json_data['data']['object']['object']
    if object_type != 'dispute':
      return
    obj = json_data['data']['object']
    status = obj['status']
    reason = obj['reason'] if obj.has_key('reason') else 'No Reason given'
    stripe.api_key = 'sk_test_Yg0ufLCJzXD4F5utQxpixepk'
    charge_id = obj['charge']
    transaction = UserCCTransactions.all().filter('ref', str(charge_id)).get()

    try:
      charge_obj = stripe.Charge.retrieve('ch_1ChwmtDi3Tt2UqGPIZGICvhi')
    except stripe.StripeError as se:
      logging.error('[Service-API] Failed to fetch charge from stripe. Error - {}'.format(se.message))
    else:
      transaction_type = Dispute.PIKA if transaction is None else (
        Dispute.RENEW if transaction.is_auto_renewed else Dispute.FRESH
      )

      dispute = Dispute.get_by_key_name(obj['id'])
      if dispute:
        dispute.dispute_status = status
        dispute.dispute_reason = reason
        dispute.last_event = datetime.datetime.utcfromtimestamp(json_data['created'])
      else:
        dispute = Dispute(
          key_name=obj['id'],
          email=transaction.email if transaction else charge_obj.receipt_email,
          amount_cents=obj['amount'],
          transaction_type=transaction_type,
          charge_id=charge_id,
          charge_created_at=datetime.datetime.utcfromtimestamp(charge_obj.created),
          charge_description=charge_obj.description,
          currency=charge_obj.currency,
          country=charge_obj.source.country,
          dispute_created_at=datetime.datetime.utcfromtimestamp(obj['created']),
          dispute_status=status,
          dispute_reason=reason,
          last_event=datetime.datetime.utcfromtimestamp(json_data['created']),
        )
      dispute.put()


application = webapp2.WSGIApplication([
    ('/dispute', DisputeHook),
], debug=True)