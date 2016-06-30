import webbrowser
import requests
from lxml import html

from PySide import QtCore

import csv
import re
from datetime import datetime

from xvideos.gallery import *
from misc            import fmt_gallery, memoize
from predict         import Predictor
from database        import Database


def download(url):
    r = requests.get(url)
    r.raise_for_status()
    r.close()
    return html.fromstring(r.text)


@memoize
def scrape_video(url):
    assert type(url) == str
    if "xvideos" in url:
        dirty = re.compile("[^a-zA-Z0-9\ _]*")
        clean = lambda s: dirty.sub("", s).lower()
        try:
            pg = download(url)
        except requests.exceptions.HTTPError:
            # This is needed when a deleted video shows up in the gallery
            return False
        with open("xvideos/vid_data.csv") as f:
            xpaths = {k: v for k, v in csv.reader(f, delimiter="|")}
        data = {}
        data["name"]  = clean(pg.xpath(xpaths["name"])[0])
        data["url"]   = url
        data["img"]   = None
        data["stars"] = [clean(star) for star in pg.xpath(xpaths["stars"])]
        data["tags"]  = [clean(tag)  for tag  in pg.xpath(xpaths["tags"]) ]
        data["tags"] += data["name"].split()
        data["views"] = float(clean(pg.xpath(xpaths["views"])[0]))
        data["likes"] = float(clean(pg.xpath(xpaths["likes"])[0]))
        data["scrape_date"] = (datetime.now() - datetime.utcfromtimestamp(0)).total_seconds()

        # Calculating the length of the video is a pain in the ass.
        dur = 0
        segments = pg.xpath(xpaths["dur"])[0].split()
        while segments:
            if segments[0] == "-":
                segments.pop(0)

            if segments[1] == "sec":
                dur += float(segments[0]) / 60
                segments.pop(0)
                segments.pop(0)

            elif segments[1] == "min":
                dur += float(segments[0])
                segments.pop(0)
                segments.pop(0)

            elif segments[0][-1] == "h":
                dur += float(segments[0][:-1]) * 60
                segments.pop(0)
        data["dur"] = dur

        return data

    else:
        raise NotImplementedError


def scrape_gallery(url):
    if "xvideos" in url:
        base = "http://www.xvideos.com"
        pg = download(url)
        vid_urls = pg.xpath(vid_xpath)
        img_urls = [img_munge(elem) for elem in pg.xpath(img_xpath)]
        img_urls = [mozaique_munge(url) for url in img_urls]
        for vid, img in zip(vid_urls, img_urls):
            yield base + vid, img

    else:
        raise NotImplementedError


class PopulateQ(QtCore.QThread):
    updateProgress = QtCore.Signal(int)
    def __init__(self,       site,    niche,   q,
                 start_pg,   max_pgs, winlock, predictor):
        QtCore.QThread.__init__(self)
        self.site       = site
        self.niche      = niche
        self.q          = q
        self.start_pg   = start_pg
        self.max_pgs    = max_pgs
        self.winlock    = winlock
        self.exit_flag  = False
        self.exit_ready = False
        self.pred = predictor

    def run(self):
        db = Database()
        for i in range(self.start_pg, self.start_pg + self.max_pgs + 1):
            gal_url = fmt_gallery(self.site, self.niche, i)
            for j, (vid_url, img_url) in enumerate(scrape_gallery(gal_url)):
                # update progress bar
                progress = (i * 20 + j) / ((self.max_pgs+1) * 20) * 100
                self.updateProgress.emit(progress)

                assert vid_url
                with self.winlock:
                    if self.exit_flag:
                        print("Thread here; exit call recevied")
                        self.exit_ready = True
                        return None

                data = scrape_video(vid_url)
                if not data:
                    continue
                data["img"] = img_url
                if not db.has_feedback(data["url"]):
                    db.save(data)
                    with self.winlock:
                        self.q.put((-self.pred.predict(data), data["url"]))
        self.updateProgress.emit(100)
