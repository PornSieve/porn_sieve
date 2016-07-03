import webbrowser
import requests
from lxml import html

from PySide import QtCore

import csv
import re
from datetime import datetime

from site_interfaces import site_selector
from misc            import memoize
from predict         import Predictor
from database        import Database


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
        site = site_selector(self.site)
        for i in range(self.start_pg, self.start_pg + self.max_pgs + 1):
            gal_url = site.fmt_gallery(self.niche, i)
            for j, (vid_url, img_url) in enumerate(site.scrape_gallery(gal_url)):
                # update progress bar
                progress = (i * 20 + j) / ((self.max_pgs+1) * 20) * 100
                self.updateProgress.emit(progress)

                data = site.scrape_video(vid_url)
                if not data:
                    continue
                data["img"] = img_url
                if not db.has_feedback(data["url"]):
                    db.save(data)
                    with self.winlock:
                        self.q.put((-self.pred.predict(data), data["url"]))
        self.updateProgress.emit(100)
