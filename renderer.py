import codecs
import json
import os
import os.path

HEADER = '<html>\n<head>\n<meta charset="UTF-8">\n<title>%s</title>\n</head>\n<body>\n'
# TODO: source attribution block for posts with sources
FOOTER = '\n</body>\n</html>'

OUTFILE_FOLDER = 'posts'
OUTFILE_PATTERN = os.path.join(OUTFILE_FOLDER, '%i.html')


class Renderer(object):
    """
    Dumps downloaded posts from the database to HTML files
    """

    def __init__(self, db):
        self.db = db
        self.blog_title, self.blog_url = self.db.get_metadata()

    def dump_posts(self):
        print 'Checking for %s' % OUTFILE_FOLDER
        if not os.path.exists(OUTFILE_FOLDER):
            print '%s not found; exiting' % OUTFILE_FOLDER
            exit(1)
        for post in self.db.get_all_posts():
            post_id, post_type, time, date, tags, source_url, source_title, state, aux_info = post
            aux_info = json.loads(aux_info)
            outfile_name = OUTFILE_PATTERN % post_id
            with codecs.open(outfile_name, 'w', encoding='utf-8') as outfile:
                print 'Dumping %s post %i to %s' % (post_type, post_id, outfile_name)
                outfile.write(HEADER % self.blog_title)
                if post_type == 'text':
                    outfile.write('<h2>%s<h2>\n%s' % (aux_info['title'], aux_info['body']))
                elif post_type == 'photo':
                    for photo in aux_info['photos']:
                        photo_slug = '<img src="%s" width="%ipx" height="%ipx"' % (photo['bv']['url'],
                                                                                   photo['bv']['width'],
                                                                                   photo['bv']['height'])
                        if 'caption' in photo:
                            photo_slug += ' alt="%s" title="%s">\n<p>%s</p>\n' % (photo['caption'], photo['caption'],
                                                                                  photo['caption'])
                        else:
                            photo_slug += '>\n'
                        outfile.write(photo_slug)
                    outfile.write(aux_info['caption'])
                else:
                    print 'Skipping %s post %i' % (post_type, post_id)
                outfile.write(FOOTER)
