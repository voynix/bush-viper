import os
import os.path
import threading
import urllib2
import Queue

CHUNK_SIZE = 16384  # 16 KB, chosen randomly

OUTFILE_FOLDER = 'images'
OUTFILE_PATTERN = os.path.join(OUTFILE_FOLDER, '%s')

class ThreadPool(object):
    """
    Manages and coordinates between a pool of threads for downloading images
    """

    def __init__(self, num_threads=5):
        print 'Checking for %s' % OUTFILE_FOLDER
        if not os.path.exists(OUTFILE_FOLDER):
            print 'Creating %s' % OUTFILE_FOLDER
            os.mkdir(OUTFILE_FOLDER)
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
            response = urllib2.urlopen(url)
            if response.getcode() not in [200, 201, 301]:
                print 'Failed to retrieve %s with error code %i' % (url, response.getcode())
                queue.task_done()
                continue
            outfile_path = OUTFILE_PATTERN % url.split('/')[-1]  # this is super janky
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
