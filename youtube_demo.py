import os
import json
import webapp2
import jinja2
import urllib

from google.appengine.ext import ndb
from google.appengine.api import urlfetch


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'youtube_demo')),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

BASE_URL = 'https://www.googleapis.com/youtube/v3'
ACTIVITIES_URL = '/activities'
KEY = 'AIzaSyCafUQ9rlkZvgOJ0yH4m8Yr7_cW-mhm7Us'


class YoutubeData(ndb.Model):
    channel_id = ndb.StringProperty()
    json_data = ndb.JsonProperty()


def get_activities(**kwargs):
    channel_id = kwargs['payload']['channelId']
    youtube_data = YoutubeData.query(YoutubeData.channel_id == channel_id).get()
    if not youtube_data:
        response = urlfetch.fetch(
          url='{}{}?{}'.format(BASE_URL, ACTIVITIES_URL, urllib.urlencode(kwargs.get('payload', {}))),
        )
        if response.status_code == 200:
            json_data = json.loads(response.content)
            YoutubeData(channel_id=channel_id, json_data=json_data).put()
            return json_data
        else:
            return {}
    return youtube_data.json_data


class ListPage(webapp2.RequestHandler):

    def get(self):
        data = get_activities(
            payload={
                'channelId': 'UCIvBHgnnLSVr9enuPvBuwyw',
                'maxResults': 20,
                'part': 'contentDetails,snippet',
                'key': KEY
            }
        )
        template = JINJA_ENVIRONMENT.get_template('list.html')
        self.response.write(template.render({
            'items': data.get('items', []),
            'name': 'Piuzinho',
            'avatar': 'https://api.adorable.io/avatars/248/blue%40adorable.io',
            'background_image': 'https://image.ibb.co/dxi7SJ/background_sample.png',
            'about_me': 'I love Bluestacks <3',
        }))


application = webapp2.WSGIApplication([
    ('/', ListPage),
], debug=True)
