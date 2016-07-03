import webbrowser
import requests
from lxml import html

import os, re, csv
from datetime import datetime


def site_selector(site_name):
    if "xvideos" in site_name:
        return XvideosScraper()
    else:
        raise NotImplementedError


class Scraper:
    """ Interface between the internet and functions
      which want data from that internet. """

    def __init__(self):
        """ Open and load csv files, mostly. """
        with open("%s/niches.csv"   % self.site_name) as f:
            self.niches = {k: v for k, v in csv.reader(f)}

        with open("%s/vid_data.csv" % self.site_name) as f:
            self.meta_xpaths = {k: v for k, v in csv.reader(f, delimiter="|")}

        with open("%s/gal_data.csv" % self.site_name) as f:
            self.gal_xpaths = {k: v for k, v in  csv.reader(f, delimiter="|")}

        self.base_url = self.niches["base_url"]


    def download(self, url):
        r = requests.get(url)
        r.raise_for_status()
        r.close()
        return html.fromstring(r.text)


    def scrape_gallery(self, url):
        """ Yield a pair of video urls and image urls. """
        pg = self.download(url)
        v_xpth, i_xpth = self.gal_xpaths["vid_xpath"], self.gal_xpaths["img_xpath"]
        for vid, img in zip(pg.xpath(v_xpth), pg.xpath(i_xpth)):
            yield self.vid_munge(vid), self.img_munge(img)


    def scrape_video(self, url):
        """ Get a dictonary of video metadata. """
        self.dirty = re.compile("[^a-zA-Z0-9\ _]*")
        self.clean = lambda s: self.dirty.sub("", s).lower()

        try:
            pg = self.download(url)

        except requests.exceptions.HTTPError as e:
            print(e, url)
            return False


        data = {}
        data["img"] = None
        data["url"] = url
        data["scrape_date"] = (datetime.now() - datetime.utcfromtimestamp(0)).total_seconds()

        return self.scrape_video_extra(pg, data)


    def scrape_video_extra(self, pg, data):
        """
        This function will be overriden by child classes to
        do scraping and formatting specific to that site.
        """
        return data


class XvideosScraper(Scraper):
    def __init__(self):
        self.site_name = "xvideos"
        self.thumb_regex    = re.compile("(http://img).*(.jpg)")
        self.mozaique_regex = re.compile("/[0-9a-f]*\.[0-9]*\.jpg")
        Scraper.__init__(self)


    def img_munge(self, element):
        # for xvideos, the url is hidden deep inside an elements classes
        url = self.thumb_regex.search(element.text).group()
        return self.mozaique_regex.sub("/mozaiquehome.jpg", url)


    def vid_munge(self, url):
        return self.base_url + url


    def fmt_gallery(self, niche, page):
        """
        Get the url of a gallery page given the niche and page
        number. This is necessary since some categories may
        require extra logic and formatting.
        """
        base_url = self.niches["base_url"]
        sub_url  = self.niches[niche]
        if "New" in niche:
            if page == 0:
                return base_url
            else:
                return base_url + "/new/" + str(page)

        elif "Best" in niche:
            return base_url + sub_url + "/" + str(page)

        else:
            return base_url + sub_url.replace("/c/", "/c/%i/" % page)


    def scrape_video_extra(self, pg, data):
        """ Continue scraping video data with logic specific to xvideos. """
        data["name"]  = self.clean(pg.xpath(self.meta_xpaths["name"])[0])
        data["stars"] = [self.clean(star) for star in pg.xpath(self.meta_xpaths["stars"])]
        data["tags"]  = [self.clean(tag)  for tag  in pg.xpath(self.meta_xpaths["tags"]) ]
        data["tags"] += data["name"].split()
        data["views"] = float(self.clean(pg.xpath(self.meta_xpaths["views"])[0]))
        data["likes"] = float(self.clean(pg.xpath(self.meta_xpaths["likes"])[0]))

        # Calculating the length of the video is a pain in the ass.
        dur = 0
        segments = pg.xpath(self.meta_xpaths["dur"])[0].split()
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
