from api import *

if __name__ == '__main__':
    if not os.path.exists(JSON_PATH):
        tokens = get_token()
    else:
        with open(JSON_PATH, 'r') as token_file:
            tokens = json.load(token_file)

    requester = TumblrRequester(**tokens)
    requester.get_posts('pluspluspangolin.tumblr.com')
