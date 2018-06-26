import os

import webapp2
import jinja2
import requests
import requests_toolbelt.adapters.appengine

# Use the App Engine Requests adapter. This makes sure that Requests uses
# URLFetch.
requests_toolbelt.adapters.appengine.monkeypatch()

import mechanicalsoup
from utilities.token_scraper import TokenScraper


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


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

        tempate = JINJA_ENVIRONMENT.get_template('login.html')
        self.response.write(tempate.render(template_context))

application = webapp2.WSGIApplication([
    ('/hypoconn/login', LoginPage)
], debug=True)