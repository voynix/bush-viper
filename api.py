import json
import os
import os.path
import urllib
import urllib2

import threadpool

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

    def __init__(self, db, host=API_URL):
        self.db = db
        self.host = host
        self.headers = {
            'User-Agent': 'bush-viper/' + self.__version
        }
        self.threadpool = threadpool.ThreadPool()

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
            print 'Failed to get posts: %s' % results['response']['error']
            return None
        else:
            print 'Retrieved posts %i to %i out of %i (%s)' % (offset, offset+len(results['posts'])-1,
                                                               results['total_posts'], blog)
            return results

    def process_post(self, post):
        """
        Extracts the relevant data from a post and stores it in the database.

        Post must be a dict as returned by TumblrRequester.get_posts().

        Posts may contain a variety of type-specific data. For unified handling this data is dumped to JSON and stored in the 'aux' field of the post.

        Tags are merged from an array into a comma (',') delimited string. (Commas are not allowed in tags, so individual tags can be recovered later.)

        :param post: the post to process
        :return: None
        """

        print 'Processing %s post %i' % (post['type'], post['id'])

        post['tags'] = ','.join(post['tags'])
        post['source_url'] = None if 'source_url' not in post else post['source_url']
        post['source_title'] = None if 'source_title' not in post else post['source_title']

        if post['type'] == 'text':
            post['aux'] = json.dumps({'title': post['title'], 'body': post['body']})
        elif post['type'] == 'quote':
            post['aux'] = json.dumps({'text': post['text'], 'source': post['source']})
        elif post['type'] == 'link':
            post['aux'] = json.dumps(
                {'title': post['title'], 'url': post['url'], 'author': post['link_author'], 'excerpt': post['excerpt'],
                 'publisher': post['publisher'], 'photos': post['photos'], 'description': post['description']})
            for photo in post['photos']:
                self.threadpool.insert(photo['original_size']['url'])
        elif post['type'] == 'answer':
            post['aux'] = json.dumps(
                {'asking_name': post['asking_name'], 'asking_url': post['asking_url'], 'question': post['question'],
                 'answer': post['answer']})
        elif post['type'] == 'video':
            post['aux'] = json.dumps({'caption': post['caption'], 'player': post['player']})
        elif post['type'] == 'audio':
            post['aux'] = json.dumps({'caption': post['caption'], 'player': post['player'], 'plays': post['plays']})
        elif post['type'] == 'chat':
            post['aux'] = json.dumps({'title': post['title'], 'dialogue': post['dialogue']})
        elif post['type'] == 'photo':
            post['aux'] = json.dumps({'photos': post['photos'], 'caption': post['caption']})
            for photo in post['photos']:
                max_alt = 0
                url = ''
                for alt in photo['alt_sizes']:
                    # make sure we get the largest available size
                    # tumblr seems to always put that first, but I'd rather not trust the API
                    #  any farther than I have to
                    if alt['width'] + alt['height'] > max_alt:
                        url = alt['url']
                        max_alt = alt['width'] + alt['height']
                self.threadpool.insert(url)

        self.db.insert_post(post)

    def get_blog(self, blog, limit=None):
        """
        Retrieves posts from a blog and stores them in the database.

        Posts are retrieved starting from offset 0, the most recent post in the blog.

        :param blog: the URL of the blog to retreive posts from
        :param limit: how many posts to download; if `None`, unlimited
        :return: None
        """
        print 'Retrieving %s posts from %s' % (str(limit) if limit is not None else 'unlimited', blog)

        posts_processed = 0
        done = False

        while not done:
            posts_processed_prev = posts_processed
            posts = self.get_posts(blog, offset=posts_processed)
            if posts is not None:
                for post in posts['posts']:
                    posts_processed += 1
                    self.process_post(post)
                    if (limit is None and posts_processed == posts_processed_prev) or posts_processed == limit:
                        done = True
                        break

        print 'Successfully retreived %i posts from %s' % (posts_processed, blog)
