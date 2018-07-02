import os
import json
import webapp2
import jinja2
import urllib

from google.appengine.ext import ndb
from google.appengine.api import urlfetch
from google.appengine.api import memcache


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'youtube_demo')),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

BASE_URL = 'https://www.googleapis.com/youtube/v3'
ACTIVITIES_URL = '/activities'
KEY = 'AIzaSyCafUQ9rlkZvgOJ0yH4m8Yr7_cW-mhm7Us'

SECONDS_IN_DAY = 24*3600


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


def get_app_thumbnail(pkg_name):
    thumb_url = memcache.get(key=pkg_name)
    if not thumb_url:
        response = urlfetch.fetch(
            url='https://cloud.bluestacks.com/app/icon?pkg={}'.format(pkg_name),
            follow_redirects=False
        )
        memcache.add(key=pkg_name, value=response.headers['location'], time=SECONDS_IN_DAY)
        return response.headers['location']
    return thumb_url


class ListPage(webapp2.RequestHandler):

    def get(self):
        liked_apps = ['com.igg.android.lordsmobile', 'com.funplus.kingofavalon',
                      'com.diandian.gog', 'com.ea.gp.candcwarzones']
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
            'liked_apps': {pkg_name: get_app_thumbnail(pkg_name) for pkg_name in liked_apps}
        }))


application = webapp2.WSGIApplication([
    ('/', ListPage),
], debug=True)
