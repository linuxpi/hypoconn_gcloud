import os
import json
import webapp2
import jinja2

from google.appengine.ext import ndb
from google.appengine.api import urlfetch
from google.appengine.api import memcache

import requests_toolbelt.adapters.appengine

# Use the App Engine Requests adapter. This makes sure that Requests uses
# URLFetch.
requests_toolbelt.adapters.appengine.monkeypatch()

from utilities.token_scraper import TokenScraper

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

ANNOTATIONS_SEARCH_URL = 'https://hypothes.is/api/search'
ANNOTATIONS_FETCH_URL = 'https://hypothes.is/api/annotations/{id}'


class UserToken(ndb.Model):
    """
    To Store scraped tokens for users
    """

    username = ndb.StringProperty()
    api_token = ndb.StringProperty()


class SavedAnnotation(ndb.Model):
    text = ndb.TextProperty()
    user = ndb.StringProperty()
    group = ndb.StringProperty()
    tags = ndb.JsonProperty()
    uri = ndb.StringProperty()
    id = ndb.StringProperty()
    added = ndb.DateTimeProperty(auto_now_add=True)


class LoginPage(webapp2.RequestHandler):

    def get(self):
        self.response.delete_cookie('token')
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
            usertoken = UserToken.query(UserToken.username==username).get()
            if usertoken:
                usertoken.api_token = token
            else:
                usertoken = UserToken(
                    username=username,
                    api_token=token
                )
            usertoken.put()
            self.response.set_cookie('token', usertoken.key.urlsafe())
            self.redirect('/')
        tempate = JINJA_ENVIRONMENT.get_template('login.html')
        self.response.write(tempate.render(template_context))


class ListPage(webapp2.RequestHandler):

    def get(self):
        headers = get_auth_headers(self.request.cookies.get('token'))
        if headers is None:
            self.response.delete_cookie('token')
            self.redirect('/hypoconn/login')
        else:
            is_valid, annotations = check_or_fetch_data(
                'annotations', 
                {
                    'url': ANNOTATIONS_SEARCH_URL,
                    'headers': headers,
                })
            if is_valid:
                self.response.write(
                    JINJA_ENVIRONMENT.get_template('index.html').render({
                        'annotations': annotations,
                        'world_view': True
                    })
                )
            else:
                self.response.write(annotations)


class SaveAnnotationPage(webapp2.RequestHandler):

    def get(self):
        annotations = SavedAnnotation.query(
            ancestor=ndb.Key(urlsafe=self.request.cookies.get('token'))
        ).order(-SavedAnnotation.added).fetch(20)
        self.response.write(
            JINJA_ENVIRONMENT.get_template('index.html').render({
                'annotations': annotations,
            })
        )


    def post(self):
        id = self.request.get('id')
        try: 
            response = urlfetch.fetch(url=ANNOTATIONS_FETCH_URL.format(id=id))
        except urlfetch.Error:
            return False, 'Error while fetching data from the api. Please refresh to retry!'
        else:
            data = json.loads(response.content)
        userkey = ndb.Key(urlsafe=self.request.cookies.get('token'))
        saved_annotation = SavedAnnotation.query(SavedAnnotation.id==id, ancestor=userkey).get()
        if not saved_annotation:
            saved_annotation = SavedAnnotation(
                user=data.get('user'),
                group=data.get('group'),
                uri=data.get('uri'),
                text=data.get('text'),
                tags=data.get('tags'),
                id=id,
                parent=userkey
            )
            saved_annotation.put()
        self.redirect('/hypoconn/save')


def check_or_fetch_data(key, request_data):
    data = memcache.get(key)
    if data is None:
        try:
            response = urlfetch.fetch(**request_data)
        except urlfetch.Error:
            return False, 'Error while fetching data from the api. Please refresh to retry!'
        else:
            data = json.loads(response.content).get('rows')
            memcache.add(key=key, value=data, time=900)
    return True, data


def get_auth_headers(urlsafe_key):
    user = ndb.Key(urlsafe=urlsafe_key).get() if urlsafe_key else None
    return {'Authorization': user.api_token} if user else None


application = webapp2.WSGIApplication([
    ('/hypoconn/save', SaveAnnotationPage),
    ('/hypoconn/login', LoginPage),
    ('/', ListPage)
], debug=True)