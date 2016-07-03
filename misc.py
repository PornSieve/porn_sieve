import csv
import re

from database import Database
from predict  import Predictor


def memoize(callback):
    memos = {}
    def inner(datum):
        if datum not in memos:
            memos[datum] = callback(datum)
        return memos[datum]
    return inner


@memoize  # not a big deal, but I don't want to reload this more than once
def get_niche_xpaths(site_name):
    with open("{}/niches.csv".format(site_name)) as f:
        return {k: v for k, v in csv.reader(f)}


def fmt_img(img_url, pic_num, total_pics):
    """ Replace the image preview url with a link to
      some preview in between. Indexes from zero. """
    # All preview images are between 1 and 30 inclusive.
    interval = 29 / total_pics
    pic_id = str(int(pic_num * interval + 1))
    new_url = re.sub("(?<=\.)[0-9]*(?=\.jpg$)", pic_id, img_url)
    return new_url


def redo_predictions(predictor, iterations, q):
    db = Database()
    out_of_q = []
    for i in range(iterations):
        if not q.empty():
            old_pred, url = q.get()
            new_pred = predictor.predict(db.get(url))
            out_of_q.append((new_pred, url))
    for new_pred, url in out_of_q:
        q.put((-new_pred, url))
