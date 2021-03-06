import json
import os.path
import urllib
import urllib2

import threadpool

API_URL = 'https://api.tumblr.com/v2/'
API_POST_LIMIT = 20

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

    def get_metadata(self, blog):
        """
        Get metadata for the indicated blog and store it in the database.

        :param blog: the URL for the blog
        :return:
        """
        metadata = self.get('blog/%s/info' % blog)
        if metadata is None:  # HTTP error from get()
            print 'Failed to get metadata; catastrophic HTTP error'
        elif 'meta' in metadata:  # application-level error from tumblr
            print 'Failed to get metadata: %s' % metadata['response']['error']
        else:
            print 'Got metadata for %s' % blog
            self.db.insert_metadata(blog, metadata['blog']['title'], metadata['blog']['updated'])

    def get_posts(self, blog, offset=0):
        """
        Gets posts from the indicated blog.

        get_posts() attempts to retrieve API_POST_LIMIT posts from the indicated blog.

        :param blog: the URL of the blog to get posts for
        :param offset: which post to start at
        :return: a dict of the posts or None if the request failed
        """
        results = self.get('blog/%s/posts' % blog, {'offset': offset, 'limit': API_POST_LIMIT})
        if results is None:  # HTTP error from get()
            print 'Failed to get posts: catastrophic HTTP error'
            return None
        elif 'meta' in results:  # application-level error from tumblr
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
            post['aux'] = json.dumps({'title': post['title'], 'body': self.threadpool.replace_urls(post['body'])})
        elif post['type'] == 'quote':
            post['aux'] = json.dumps({'text': self.threadpool.replace_urls(post['text']), 'source': post['source']})
        elif post['type'] == 'link':
            for photo in post['photos']:
                # unlike in photo posts, in link posts photos give their biggest available size in original_size
                # consistency!
                self.threadpool.insert(photo['original_size']['url'])
                photo['bv'] = {'url': self.threadpool.rewrite_and_download_url(photo['original_size']['url']),
                               'width': photo['original_size']['width'], 'height': photo['original_size']['height']}
            post['aux'] = json.dumps(
                {'title': post['title'], 'url': post['url'], 'author': post['link_author'], 'excerpt': post['excerpt'],
                 'publisher': post['publisher'], 'photos': post['photos'],
                 'description': self.threadpool.replace_urls(post['description'])})
        elif post['type'] == 'answer':
            post['aux'] = json.dumps(
                {'asking_name': post['asking_name'], 'asking_url': post['asking_url'], 'question': post['question'],
                 'answer': self.threadpool.replace_urls(post['answer'])})
        elif post['type'] == 'video':
            post['aux'] = json.dumps({'caption': self.threadpool.replace_urls(post['caption']),
                                      'player': post['player']})
        elif post['type'] == 'audio':
            post['aux'] = json.dumps({'caption': self.threadpool.replace_urls(post['caption']),
                                      'player': post['player'], 'plays': post['plays']})
        elif post['type'] == 'chat':
            post['aux'] = json.dumps({'title': post['title'], 'dialogue': post['dialogue']})
        elif post['type'] == 'photo':
            for photo in post['photos']:
                max_width = 0
                max_height = 0
                url = ''
                for alt in photo['alt_sizes']:
                    # make sure we get the largest available size
                    # tumblr seems to always put that first, but I'd rather not trust the API more than necessary
                    if alt['width'] + alt['height'] > max_width + max_height:
                        url = alt['url']
                        max_width = alt['width']
                        max_height = alt['height']
                self.threadpool.insert(url)
                photo['bv'] = {'url': self.threadpool.rewrite_and_download_url(url), 'width': max_width,
                               'height': max_height}
            post['aux'] = json.dumps({'photos': post['photos'],
                                      'caption': self.threadpool.replace_urls(post['caption'])})

        self.db.insert_post(post)

    def get_blog(self, blog, limit=None):
        """
        Retrieves posts from a blog and stores them in the database.

        Posts are retrieved starting from offset 0, the most recent post in the blog.

        :param blog: the URL of the blog to retreive posts from
        :param limit: how many posts to download; if `None`, unlimited
        :return: None
        """
        self.get_metadata(blog)

        print 'Retrieving %s posts from %s' % (str(limit) if limit is not None else 'unlimited', blog)

        posts_processed = 0
        offset = 0
        done = False

        while not done:
            posts = self.get_posts(blog, offset=offset)
            if posts is not None:
                if len(posts) == 0:  # we've run off the end of the blog
                    break
                for post in posts['posts']:
                    # tumblr, because tumblr, doesn't do stable pagination
                    # ie, since we get posts in blocks of 20 at fixed offsets from the most *recent* post
                    #  if a post is made while we're walking through the blog, the next block will contain a post
                    #  that was in the previous block, and if we put that in the database we'd violate the
                    #  uniqueness constraint on post ids
                    # thus, we do a SQL query to check for duplication before we insert the post into the db
                    if self.db.post_id_exists(post['id']):
                        continue
                    self.process_post(post)
                    posts_processed += 1
                    if posts_processed == limit:
                        done = True
                        break
                offset += API_POST_LIMIT

        print 'Successfully retreived %i posts from %s' % (posts_processed, blog)
