import os
import os.path
import sqlite3

DATABASE_PATH = os.path.join(os.getcwd(), 'scrape.sql')
METADATA_TABLE = 'metadata'
POSTS_TABLE = 'posts'


class DBAdapter(object):
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