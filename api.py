import json
import os
import os.path
import urllib
import urlparse

import oauth2 as oauth
from httplib2 import RedirectLimit


API_URL = 'https://api.tumblr.com/v2/'
OAUTH_REQUEST_URL = 'http://www.tumblr.com/oauth/request_token'
OAUTH_AUTHORIZE_URL = 'http://www.tumblr.com/oauth/authorize'
OAUTH_ACCESS_URL = 'http://www.tumblr.com/oauth/access_token'

JSON_PATH = os.path.join(os.getcwd(), ".bush_viper")

with open(os.path.join(os.getcwd(), "secret_key")) as key_file:
    secrets = json.load(key_file)
    CONSUMER_KEY = secrets['consumer_key']
    CONSUMER_SECRET = secrets['consumer_secret']


class TumblrRequester(object):
    """
    A simple request object that lets us query the Tumblr API
    """

    __version = '0.1.0'

    def __init__(self, consumer_key, consumer_secret, oauth_token, oauth_token_secret, host=API_URL):
        self.host = host
        self.consumer = oauth.Consumer(key=consumer_key, secret=consumer_secret)
        self.token = oauth.Token(key=oauth_token, secret=oauth_token_secret)
        self.headers = {
            'User-Agent': 'bush-viper/' + self.__version
        }

    def get(self, url, params=None):
        """
        Issues a GET request against the API.
        :param url: the URL requested
        :param params: a dict of parameters for the request
        :returns: a dict parsed from the JSON response
        """
        if params is None:
            params = {'api_key': CONSUMER_KEY}
        else:
            params['api_key'] = CONSUMER_KEY

        url = self.host + url
        url = url + "?" + urllib.urlencode(params)

        client = oauth.Client(self.consumer, self.token)
        try:
            client.follow_redirects = False
            resp, content = client.request(url, method="GET", redirections=False, headers=self.headers)
        except RedirectLimit, e:
            resp, content = e.args

        return self.json_parse(content)

    def json_parse(self, content):
        """
        Performs content validation and JSON parsing on API responses.

        :param content: The JSON content to parse
        :returns: a dict of the json response
        """
        try:
            data = json.loads(content)
        except ValueError, e:
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

        :param blog: the URL of the blog to get
        :param offset: which post to start at
        :return: a dict of the posts or None if the request failed
        """
        results = self.get('blog/%s/posts' % blog, {'offset': offset, 'limit': 20})
        if 'meta' in results:
            print 'Failed to get posts: %s' % results['error']
            return None
        else:
            print 'Got %i posts out of %i' % (len(results['posts']), results['total_posts'])
            return results


def get_token():
    """
    Does the OAuth authorization dance, saving the resulting token into TOKEN_FILE,
    and returning the token for use by TumblrRequester.

    :return: a dict of the OAuth values needed by TumblrRequester
    """

    consumer = oauth.Consumer(CONSUMER_KEY, CONSUMER_SECRET)
    client = oauth.Client(consumer)

    # Get request token
    resp, content = client.request(OAUTH_REQUEST_URL, "POST")
    request_token = urlparse.parse_qs(content)

    # Redirect to authentication page
    print 'Please go here and authorize:\n%s?oauth_token=%s' % (OAUTH_AUTHORIZE_URL, request_token['oauth_token'][0])
    redirect_response = raw_input('Paste the redirect URL here after authorizing:\n')

    # Retrieve oauth verifier
    url = urlparse.urlparse(redirect_response)
    query_dict = urlparse.parse_qs(url.query)
    oauth_verifier = query_dict['oauth_verifier'][0]

    # Request access token
    token = oauth.Token(request_token['oauth_token'], request_token['oauth_token_secret'][0])
    token.set_verifier(oauth_verifier)
    client = oauth.Client(consumer, token)

    resp, content = client.request(OAUTH_ACCESS_URL, "POST")
    access_token = urlparse.parse_qs(content)

    tokens = {
        'consumer_key': CONSUMER_SECRET,
        'consumer_secret': CONSUMER_SECRET,
        'oauth_token': access_token['oauth_token'][0],
        'oauth_token_secret': access_token['oauth_token_secret'][0]
    }

    with open(JSON_PATH, 'w+') as token_file:
        json.dump(tokens, token_file, indent=2)

    return tokens
