import os
import json
import webapp2
import jinja2
import requests
import requests_toolbelt.adapters.appengine

# Use the App Engine Requests adapter. This makes sure that Requests uses
# URLFetch.
requests_toolbelt.adapters.appengine.monkeypatch()

import mechanicalsoup
from utilities.token_scraper import TokenScraper

from google.appengine.ext import ndb
from google.appengine.api import urlfetch
from google.appengine.api import memcache


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

ANNOTATIONS_SEARCH_URL = 'https://hypothes.is/api/search'


class UserToken(ndb.Model):
    """
    To Store scraped tokens for users
    """

    username = ndb.StringProperty()
    api_token = ndb.StringProperty()


class LoginPage(webapp2.RequestHandler):

    def get(self):
        tempate = JINJA_ENVIRONMENT.get_template('login.html')
        self.response.write(tempate.render({}))

    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')
        token_scraper = TokenScraper(username, password)
        template_context = {}

        try:
            token = token_scraper.login_and_get_token()
        except Exception as e:
            template_context['error'] = e.message
        else:
            template_context['token'] = True
            usertoken = UserToken(
                username=username, 
                api_token=token,
            )
            usertoken.put()
            self.response.set_cookie('token', usertoken.key.urlsafe())
            self.redirect('/hypoconn')
        tempate = JINJA_ENVIRONMENT.get_template('login.html')
        self.response.write(tempate.render(template_context))


class ListPage(webapp2.RequestHandler):

    def get(self):
        headers = get_auth_headers(self.request.cookies.get('token'))
        if not headers:
            self.request.cookies.delete('token')
            self.redirect('/hypoconn/login')
        is_valid, annotations = check_or_fetch_data(
            'annotations', 
            {
                'url': ANNOTATIONS_SEARCH_URL,
                'headers': headers,
            })
        if is_valid:
            self.response.write(
                JINJA_ENVIRONMENT.get_template('index.html').render({
                    'annotations': annotations
                })
            )
        else:
            self.response.write(annotations)


def check_or_fetch_data(key, request_data):
    data = memcache.get(key)
    if data is None:
        try:
            response = urlfetch.fetch(**request_data)
        except urlfetch.Error:
            return False, 'Error while fetching data from the api. Please refresh to retry!'
        finally:
            data = json.loads(response.content).get('rows')
            memcache.add(key=key, value=data, time=900)
    return True, data


def get_auth_headers(urlsafe_key):
    user = ndb.Key(urlsafe=urlsafe_key).get()
    return {'Authorization': user.api_token} if user else None

application = webapp2.WSGIApplication([
    ('/hypoconn/login', LoginPage),
    ('/hypoconn', ListPage)
], debug=True)