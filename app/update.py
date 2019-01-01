import json
import sys
import re
import os
import sys
from datetime import datetime, timedelta, date
from threading import Thread, Lock
from queue import Queue

import requests

from logger import CustomLogger


logger = CustomLogger(__name__)


ALLOWED_DATE_LAG = timedelta(days=7)
APOD_ARCHIVE_SOURCE_FNAME = "archive.html"
APOD_ARCHIVE_URL = "http://apod.nasa.gov/apod/archivepix.html"
APOD_POSTS_JSON_FNAME = "posts.json"
APOD_URL = "http://apod.nasa.gov/apod/"
# UP TO BUT NOT INCLUDING
POSTS_START_DATE = datetime(year=2000, month=1, day=1).date() - timedelta(1)
PATTERNS = {
    # January 1st, 2000 and after
    "post_2k": {
        # Capturing urls from main APOD archive links page
        "raw_info": re.compile(
            r"""\d{4}\s{1}[A-Z][a-z]{2,9}\s{1}\d{2}.*?</a""", re.X | re.S
        ),
        "info": re.compile(
            r"""(\d{4}\s[A-Z][a-z]{2,9}\s\d{2}).*?
                (ap\d{6}.html)">
                (.*?)</a""",
            re.X | re.S,
        ),
        # Captures image urls from main APOD post page
        "img": re.compile(
            r'''<body.*?\d{4}\s[A-Z][a-z]{2,8}\s\d{1,2}.*?<IMG\sSRC="(image.*?)"''',
            re.X | re.S,
        ),
        "vid": re.compile(
            r'''<iframe.*?src="(.*?)"(.*?)<\/iframe>''', re.X | re.S
        ),
        "expl": re.compile(r"""<b>\s?Explanation:\s?<\/b>(.*?)<p>""", re.X | re.S),
        "cred": re.compile(r'''<\/b>\s<br>(.*?)<\/(?:CENTER|center)>''', re.X | re.S),
        "date_format": "%Y %B %d",
    },
    # December 31st, 1999 and before
    "pre_2k": {
        "raw_info": re.compile(
            r"""[A-Z][a-z]{2,9}\s{1}\d{2}\s{1}\d{4}.{0,}.*>""", re.X | re.S
        ),
        "info": re.compile(
            r"""([A-Z][a-z]{2,9}\s{1}\d{1,2}\s{1}\d{4}).*?
                (ap\d{6}.html)">
                (.*?)</a""",
            re.X | re.S,
        ),
        "img": re.compile(
            r'''<center.*?
                [A-Z][a-z]{2,8}\s\d{1,2},\s\d{4}\s.*?
                "(image.*?)"''',
            re.X | re.S,
        ),
        "date_format": "%B %d %Y",
    },
}


class Worker(Thread):
    def __init__(self, tasks):
        """
        :param tasks: A queue containing the tasks for the worker instance.
        :type tasks: queue.Queue instance

        """
        Thread.__init__(self)
        self.tasks = tasks
        self.daemon = True
        self.start()

    def run(self):
        while True:
            func, args, kwargs = self.tasks.get()
            while True:
                try:
                    func(*args, **kwargs)
                except Exception as e:
                    print("Error: {}".format(e))
                    continue
                else:
                    self.tasks.task_done()
                    break


class ThreadPool:
    def __init__(self, thread_count):
        self.tasks = Queue(thread_count)
        for _ in range(thread_count):
            Worker(self.tasks)

    def add_task(self, func, *args, **kwargs):
        """ Add a new task to the queue. """
        self.tasks.put((func, args, kwargs))

    def wait_completion(self):
        """ Blocks until all tasks in queue have been processed. """
        self.tasks.join()


pool = ThreadPool(int(os.environ.get("THREAD_COUNT", 20)))
lock = Lock()


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, date):
            return obj.strftime("%Y-%m-%d")
        return json.JSONEncoder.default(self, obj)


def str_to_date(date_string):
    """ Expected to be in a form 2016-09-01 """
    if isinstance(date_string, date):
        return date_string
    return date(*list(map(int, date_string.split("-"))))


def download_source(url):
    return str(requests.get(url).text)


def retrieve_posts(src, until_date):
    posts = []

    def complete_post_data(post, patterns):
        post_src = download_source(post["link"])

        try:
            try:
                post["imag"] = APOD_URL + patterns["img"].findall(post_src)[0]
            except IndexError as e:
                try:
                    video_data = patterns["vid"].findall(post_src)[0]

                    post["vide"] = {
                        "src": video_data[0],
                        "attrs": video_data[1],
                    }
                except IndexError as e:
                    logger.error("Failed to find image or video")
                    raise

            try:
                post["expl"] = patterns["expl"].findall(post_src)[0]
            except IndexError as e:
                logger.error("Failed to find explanation")
                raise

            try:
                post["cred"] = patterns["cred"].findall(post_src)[0]
            except IndexError as e:
                logger.error("Failed to find credit")
                raise
        except Exception as e:
            logger.error(f'Failed URL: {post["link"]}, {str(e)}')
            return

        with lock:
            posts.append(post)

    for timeframe in ["post_2k", "pre_2k"]:
        for post in [
            p
            for p in [
                {
                    "date": datetime.strptime(
                        x[0], PATTERNS[timeframe]["date_format"]
                    ).date(),
                    "link": "".join([APOD_URL, x[1]]),
                    "desc": x[2],
                }
                for x in [
                    PATTERNS[timeframe]["info"].findall(u)[0]
                    for u in PATTERNS[timeframe]["raw_info"].findall(src)
                ]
            ]
            if p["date"] > until_date
        ]:
            pool.add_task(complete_post_data, post, PATTERNS[timeframe])

    pool.wait_completion()

    logger.info("Added {} posts.".format(len(posts)))

    return posts


def main():
    archive_page_source = None
    until_date = None
    posts = []

    if not os.path.isfile(APOD_ARCHIVE_SOURCE_FNAME):
        logger.info(f"Downloading first copy of source from '{APOD_ARCHIVE_URL}'...")

        archive_page_source = download_source(APOD_ARCHIVE_URL)
        with open(APOD_ARCHIVE_SOURCE_FNAME, "w") as f:
            f.write(archive_page_source)

        until_date = POSTS_START_DATE  # assume posts.json is empty

    else:
        with open(APOD_ARCHIVE_SOURCE_FNAME, "r") as f:
            archive_page_source = f.read()

        # Latest post's URL from archive source's <ul> of APOD Posts
        latest_url = PATTERNS["post_2k"]["raw_info"].findall(archive_page_source)[0]
        # take raw url, break into capture groups used during scraping
        # then pull first index which contains the date
        # formatting dates for easy comparison and use with timedelta
        latest_date = datetime.strptime(
            PATTERNS["post_2k"]["info"].findall(latest_url)[0][0], "%Y %B %d"
        ).date()

        # if the source is older than allowed time/date lag
        if latest_date < datetime.now().date() - ALLOWED_DATE_LAG:
            archive_page_source = download_source(APOD_ARCHIVE_URL)
            with open(APOD_ARCHIVE_SOURCE_FNAME, "w") as f:
                f.write(archive_page_source)

            logger.info(
                "Updated local archive source, scrape until {}.".format(latest_date)
            )

        else:
            logger.info("No updates to local archive source.")

        until_date = latest_date  # source is within allowed time lag

    logger.info(f"Updating posts.json with posts until {until_date}.")

    if os.path.isfile(APOD_POSTS_JSON_FNAME):
        with open(APOD_POSTS_JSON_FNAME, "r") as f:
            try:
                posts = json.load(f)
            except ValueError as e:
                pass

    # If empty or if each dict does not have below list of keys
    if not posts or not all(
        set(["link", "date", "desc", "imag"]).issuperset(post) for post in posts
    ):
        logger.info(
            f"JSON from local '{APOD_POSTS_JSON_FNAME}' is malformed, recreating..."
        )
        until_date = POSTS_START_DATE
    else:
        logger.info(f"Local '{APOD_POSTS_JSON_FNAME}' is valid, checking if updated...")
        latest_date = max(str_to_date(x["date"]) for x in posts)

        if latest_date < str_to_date(until_date):
            logger.info("Outdated, updating...")
            until_date = latest_date
        else:
            logger.info(f"Updated, latest post is from {latest_date}.")

    # for testing
    #until_date = datetime(year=2018, month=6, day=1).date() - timedelta(1)

    logger.info("Running until {}...".format(until_date))
    posts = sorted(
        posts + retrieve_posts(archive_page_source, until_date),
        key=lambda k: str_to_date(k["date"]),
        reverse=True,
    )

    logger.info("Writing sorted APOD Post JSON to '{}'.".format(APOD_POSTS_JSON_FNAME))
    open(APOD_POSTS_JSON_FNAME, "w").close()  # Empty all contents of file.
    with open(APOD_POSTS_JSON_FNAME, "w") as f:
        json.dump(posts, f, cls=DateTimeEncoder, indent=2)

    logger.info("Completed writing JSON to '{}'.".format(APOD_POSTS_JSON_FNAME))

    # Write the JSON to the spacescrape.db.
    pass


if __name__ == "__main__":
    main()
