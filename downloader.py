import sys

from api import *
from db import *


if __name__ == '__main__':
    with DBAdapter() as db:
        requester = TumblrRequester(db)
        requester.get_blog(sys.argv[1], int(sys.argv[2]))
