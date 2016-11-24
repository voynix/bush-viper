import sys

from api import *
from db import *
from renderer import *


if __name__ == '__main__':
    with DBAdapter() as db:
        if sys.argv[1] == 'render':
            renderer = Renderer(db)
            renderer.dump_posts()
        else:
            requester = TumblrRequester(db)
            requester.get_blog(sys.argv[1], int(sys.argv[2]))
