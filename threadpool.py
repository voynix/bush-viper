import os
import os.path
import re
import threading
import urllib2
import Queue

from renderer import OUTFILE_FOLDER as POSTS_FOLDER

CHUNK_SIZE = 16384  # 16 KB, chosen randomly

OUTFILE_FOLDER = 'images'
OUTFILE_PATTERN = os.path.join(POSTS_FOLDER, OUTFILE_FOLDER, '%s')

TUMBLR_IMAGE_REGEX = r'https://\d+\.media\.tumblr\.com/\w+/\w+\.\w{3}'


class ThreadPool(object):
    """
    Manages and coordinates between a pool of threads for downloading images
    """

    def __init__(self, num_threads=5):
        print 'Checking for %s' % POSTS_FOLDER
        if not os.path.exists(POSTS_FOLDER):
            print 'Creating %s' % POSTS_FOLDER
            os.mkdir(POSTS_FOLDER)
        print 'Checking for %s' % OUTFILE_FOLDER
        if not os.path.exists(os.path.join(POSTS_FOLDER, OUTFILE_FOLDER)):
            print 'Creating %s' % OUTFILE_FOLDER
            os.mkdir(os.path.join(POSTS_FOLDER, OUTFILE_FOLDER))
        self.queue = Queue.Queue()
        self.threads = []
        for x in xrange(0, num_threads):
            print 'Created thread'
            self.threads.append(threading.Thread(target=download_images, kwargs={'queue': self.queue, 'id': x}))
        for thread in self.threads:
            thread.daemon = True  # daemonize child threads so they die with the parent
            thread.start()
            print 'Started thread'

    def __del__(self):
        self.block_on_queue()

    def insert(self, url):
        """
        Adds a URL to the queue to be downloaded

        :param url: the URL to download
        :return: None
        """
        self.queue.put(url)

    def rewrite_and_download_url(self, url):
        """
        Rewrites a URL that points to an external image to point to a bush-viper-downloaded local image and downloads the image

        :param url: the URL to rewrite and download
        :return: the rewritten URL
        """

        new_url = os.path.join(OUTFILE_FOLDER, url.split('/')[-1])
        self.insert(url)
        print 'Rewrote %s to %s' % (url, new_url)
        return new_url

    def replace_urls(self, text):
        """
        Finds URLs of images hosted on tumblr and replaces them with local URLs

        :param text: the text to replace URLs in
        :return: the text, with tumblr image URLs rewritten
        """

        def handle_url(matched_url):
            return self.rewrite_and_download_url(matched_url.group(0))
        return re.sub(TUMBLR_IMAGE_REGEX, handle_url, text)

    def block_on_queue(self):
        """
        Blocks until the queue has been emptied; ie all images have been downloaded

        :return: None
        """
        print 'Waiting for image queue to empty before terminating threadpool'
        self.queue.join()
        print 'Queue emptied; terminating threadpool'


def download_images(queue, id):
    """
    Downloads images from a queue

    :param queue: the queue to pull images to download from
    :param id: an ID number for this thread, to allow for better logging
    :return: None
    """
    while True:
        url = queue.get()
        try:
            outfile_path = OUTFILE_PATTERN % url.split('/')[-1]  # this is super janky
            if os.path.exists(outfile_path):
                print '%s has already been downloaded to %s; thread %i moving on' % (url, outfile_path, id)
                # we don't need to call task_done() here since the finally clause takes care of it for us
                continue
            response = urllib2.urlopen(url)
            if response.getcode() not in [200, 201, 301]:
                print 'Thread %i failed to retrieve %s with HTTP status %i' % (id, url, response.getcode())
                queue.task_done()
                continue
            print 'Thread %i now downloading %s to %s' % (id, url, outfile_path)
            with open(outfile_path, 'w') as outfile:
                while True:
                    data = response.read(CHUNK_SIZE)
                    if data:
                        outfile.write(data)
                    else:
                        print 'Thread %i finished downloading %s' % (id, url)
                        break
        except Exception as e:  # if anything whatsoever goes wrong
            print 'Failure in thread %i: %s' % (id, repr(e))
        finally:
            queue.task_done()
