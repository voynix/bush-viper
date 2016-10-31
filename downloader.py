import sys

from api import *
from db import *

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
    with DBAdapter() as db:
        requester = TumblrRequester()
        posts = requester.get_posts(sys.argv[1])
        if posts is not None:
            for post in posts['posts']:
                process_post(post, db)
