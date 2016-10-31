import sqlite3

from api import *

DATABASE_PATH = os.path.join(os.getcwd(), 'scrape.sql')
METADATA_TABLE = 'metadata'
POSTS_TABLE = 'posts'

class DBAdapter:
    """
    A wrapper around sqlite
    """

    def __init__(self):
        self.conn = None
        self.curs = None

    def __enter__(self):
        self.connect_to_db()
        self.create_tables()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect_from_db()

    def connect_to_db(self, db=DATABASE_PATH):
        """
        Connects to a SQLilte database file.

        Prints an error message and exit()s if the database cannot be connected to.

        :param db: the database file to connect to
        :return: None
        """
        try:
            self.conn = sqlite3.connect(db)
        except:
            print u'Could not connect to database {}'.format(db)
            print 'Exiting'
            exit(1)
        self.curs = self.conn.cursor()

    def disconnect_from_db(self):
        """
        Closes the connection to the database, committing any transactions in progress.

        :return: None
        """
        self.conn.commit()
        self.conn.close()

    def create_tables(self):
        """
        Creates the tables for storing blog metadata and post data.

        :return: None
        """
        self.curs.execute('CREATE TABLE IF NOT EXISTS %s (url TEXT, title TEXT, last_update INTEGER)' % METADATA_TABLE)
        self.curs.execute('''CREATE TABLE IF NOT EXISTS %s (id INTEGER PRIMARY KEY, type TEXT, time INTEGER, date TEXT,
                             tags TEXT, source_url TEXT, source_title TEXT, state TEXT, aux_info TEXT)''' % POSTS_TABLE)
        self.conn.commit()

    def insert_post(self, post):
        """
        Stores a post in the database.

        :param post: the post to store
        :return: None
        """
        command = u'INSERT INTO %s VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)' % POSTS_TABLE
        values = (post['id'], post['type'], post['timestamp'], post['date'], post['tags'], post['source_url'],
                  post['source_title'], post['state'], post['aux'])
        self.curs.execute(command, values)
        self.conn.commit()


def process_post(post, db):
    """
    Extracts the relevant data from a post and stores it in the given database.

    Post must be a dict as returned by TumblrRequester.get_posts().

    Posts may contain a variety of type-specific data. For unified handling this data is dumped to JSON and stored in the 'aux' field of the post.

    Tags are merged from an array into a comma (',') delimited string. (Commas are not allowed in tags, so individual tags can be recovered later.)

    :param post: the post to process
    :param db: a DBAdapter to store the post in
    :return: None
    """

    print 'processing %s post %i' % (post['type'], post['id'])

    post['tags'] = ','.join(post['tags'])
    post['source_url'] = None if 'source_url' not in post else post['source_url']
    post['source_title'] = None if 'source_title' not in post else post['source_title']

    if post['type'] == 'text':
        post['aux'] = json.dumps({'title': post['title'], 'body': post['body']})
    elif post['type'] == 'quote':
        post['aux'] = json.dumps({'text': post['text'], 'source': post['source']})
    elif post['type'] == 'link':
        post['aux'] = json.dumps({'title': post['title'], 'url': post['url'], 'author': post['author'], 'excerpt': post['excerpt'], 'publisher': post['publisher'], 'photos': post['photos'], 'description': post['description']})
    elif post['type'] == 'answer':
        post['aux'] = json.dumps({'asking_name': post['asking_name'], 'asking_url': post['asking_url'], 'question': post['question'], 'answer': post['answer']})
    elif post['type'] == 'video':
        post['aux'] = json.dumps({'caption': post['caption'], 'player': post['player']})
    elif post['type'] == 'audio':
        post['aux'] == json.dumps({'caption': post['caption'], 'player': post['player'], 'plays': post['plays']})
    elif post['type'] == 'chat':
        post['aux'] = json.dumps({'title': post['title'], 'dialogue': post['dialogue']})
    elif post['type'] == 'photo':
        post['aux'] = json.dumps({'photos': post['photos'], 'caption': post['caption']})

    db.insert_post(post)


if __name__ == '__main__':
    if not os.path.exists(JSON_PATH):
        tokens = get_token()
    else:
        with open(JSON_PATH, 'r') as token_file:
            tokens = json.load(token_file)
    with DBAdapter() as db:
        requester = TumblrRequester(**tokens)
        posts = requester.get_posts('staff.tumblr.com')
        if posts is not None:
            for post in posts['posts']:
                process_post(post, db)

