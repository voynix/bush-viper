import json
import os
import os.path
import urllib
import urllib2

import oauth2 as oauth
from httplib2 import RedirectLimit


API_URL = 'https://api.tumblr.com/v2/'

JSON_PATH = os.path.join(os.getcwd(), ".bush_viper")

with open(os.path.join(os.getcwd(), "secret_key")) as key_file:
    secrets = json.load(key_file)
    CONSUMER_KEY = secrets['consumer_key']


class TumblrRequester(object):
    """
    A wrapper around the Tumblr API
    """

    __version = '0.1.0'

    def __init__(self, host=API_URL):
        self.host = host
        self.headers = {
            'User-Agent': 'bush-viper/' + self.__version
        }

    def get(self, url, params=None):
        """
        Issues a GET request against the API.

        :param url: the URL requested
        :param params: a dict of parameters for the request
        :returns: a dict parsed from the JSON response or None if the request failed
        """
        if params is None:
            params = {'api_key': CONSUMER_KEY}
        else:
            params['api_key'] = CONSUMER_KEY

        url = self.host + url + "?" + urllib.urlencode(params)

        try:
            request = urllib2.Request(url=url, headers=self.headers)
            response = urllib2.urlopen(request)
            if response.getcode() not in [200, 201, 301]:
                print 'Failed to retrieve %s with error code %i' % (url, response.getcode())
                return None
            content = response.read()
        except urllib2.URLError, e:
            print 'Failed to retrieve %s with error %s' % (url, str(e))
            return None

        return self.json_parse(content)

    def json_parse(self, content):
        """
        Performs content validation and JSON parsing on API responses.

        :param content: The JSON content to parse
        :returns: a dict parsed from the JSON
        """
        try:
            data = json.loads(content)
        except ValueError:
            data = {'meta': {'status': 500, 'msg': 'Server Error'},
                    'response': {'error': 'Malformed JSON or HTML was returned.'}}

        #We only really care about the response if we succeed
        #and the error if we fail
        if data['meta']['status'] in [200, 201, 301]:
            return data['response']
        else:
            return data

    def get_posts(self, blog, offset=0):
        """
        Gets posts from the indicated blog.

        get_posts() attempts to retrieve 20 posts from the indicated blog. (20 is the most allowed by the tumblr API.)

        :param blog: the URL of the blog to get
        :param offset: which post to start at
        :return: a dict of the posts or None if the request failed
        """
        results = self.get('blog/%s/posts' % blog, {'offset': offset, 'limit': 20})
        if results is None:  # HTTP error from get()
            print 'Failed to get posts: catastrophic HTTP error'
            return None
        if 'meta' in results:  # application-level error from tumblr
            print 'Failed to get posts: %s' % results['error']
            return None
        else:
            print 'Got posts %i to %i out of %i (%s)' % (offset, offset+len(results['posts'])-1, results['total_posts'],
                                                         blog)
            return results
