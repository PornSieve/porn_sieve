import sqlite3
from datetime import datetime, timedelta
from threading import RLock


class Database:
    lock = RLock()
    def __init__(self, dbname="usr_data/default.db"):
        # check to see if there's a database open
        self.cnx = sqlite3.connect(dbname)
        c = self.cnx.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS videos
                     (url         TEXT PRIMARY KEY,
                      img         TEXT,
                      name        TEXT,
                      views       INT ,
                      likes       REAL,
                      dur         REAL,
                      feedback    REAL,
                      scrape_date DATE);''')
        self.cnx.commit()

        c.execute("CREATE TABLE IF NOT EXISTS tags (url TEXT, tag TEXT);")
        self.cnx.commit()

        c.execute("CREATE TABLE IF NOT EXISTS stars (url TEXT, star TEXT);")
        self.cnx.commit()

        if self.amt_of_feedback() == 0:
            fake_data = {
                          "name": "hotswapping sluts volume 2",
                          "scrape_date": (datetime.now() - datetime.utcfromtimestamp(0)).total_seconds(),
                          "tags": [ "backdoor penetration", "master/slave threads", "debuggery", "leaky pipe"],
                          "likes": 0,
                          "dur": 15.97463007,
                          "stars": [ "Claudette Shannon", "Ada Lovelace", "Edsgar Dickstra" ],
                          "views": 42,
                          "url": "https://unixxx.net/",
                          "img": "https://unixxx.net/man_pages/pulse_injection.png"
                        }
            self.save(fake_data)
            self.save_feedback(fake_data["url"], 2)


    def save(self, data):
        with self.lock:
            c = self.cnx.cursor()
            c.execute("SELECT url FROM videos WHERE url = ?;", (data["url"],))
            if not c.fetchall():
                c.execute("INSERT INTO videos VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                           (data["url"]     ,
                            data["img"]     ,
                            data["name"]    ,
                            data["views"]   ,
                            data["likes"]   ,
                            data["dur"]     ,
                            None            ,
                            datetime.now()  ))
                self.cnx.commit()

                for tag in data["tags"]:
                    c.execute("INSERT INTO tags VALUES (?, ?);",
                               (data["url"], tag))
                self.cnx.commit()

                for star in data["stars"]:
                    c.execute("INSERT INTO tags VALUES (?, ?);",
                               (data["url"], star))
                self.cnx.commit()


    def save_feedback(self, url, amt):
        with self.lock:
            c = self.cnx.cursor()
            c.execute("UPDATE videos SET feedback = ? WHERE url = ?;", (amt, url))
            self.cnx.commit()


    def delete(self, url):
        with self.lock:
            c = self.cnx.cursor()
            c.execute("DELETE FROM videos WHERE url = ?;", (url,))
            self.cnx.commit()
            c.execute("DELETE FROM tags WHERE url = ?;", (url,))
            self.cnx.commit()


    def size(self):
        c = self.cnx.cursor()
        with self.lock:
            c.execute("SELECT COUNT(url) FROM videos;")
            return c.fetchone()[0]


    def amt_of_feedback(self):
        c = self.cnx.cursor()
        with self.lock:
            c.execute("SELECT COUNT(feedback) FROM videos;")
            return c.fetchone()[0]


    def give_feedback(self, url, feedback):
        with self.lock:
            c = self.cnx.cursor()
            c.execute("UPDATE videos SET feedback = ? WHERE url = ?;",
                       (feedback, url))
            self.cnx.commit()


    def was_visited(self, url):
        with self.lock:
            c = self.cnx.cursor()
            c.execute("SELECT url FROM videos WHERE url = ?;", (url,))
            fetched = c.fetchone()
            # Sometime we get [(None,)] which evaluates to true,
            # other times we get None which evaluates to false.
            if fetched:
                return any(fetched[0])
            else:
                return False


    def has_feedback(self, url):
        with self.lock:
            c = self.cnx.cursor()
            c.execute("SELECT feedback FROM videos WHERE url = ?;", (url,))
            fetched = c.fetchone()
            # Sometime we get [(None,)] which evaluates to true,
            # other times we get None which evaluates to false.
            if fetched:
                return fetched[0]
            else:
                return False


    def get_img(self, url):
        with self.lock:
            c = self.cnx.cursor()
            c.execute("SELECT img FROM videos WHERE url = ?;", (url,))
            got = c.fetchone()[0]
            return got


    def get(self, url):
        with self.lock:
            c = self.cnx.cursor()
            c.execute('''SELECT img, name, views,
                      likes, dur, feedback, scrape_date
                      FROM videos WHERE url = ?;''', (url,))
            img, name, views, likes, dur, feedback, date = c.fetchone()

            c.execute("SELECT tag FROM tags WHERE url = ?;", (url,))
            tags = [tag[0] for tag in c.fetchall()]

            c.execute("SELECT star FROM stars WHERE url = ?;", (url,))
            stars = [star[0] for star in c.fetchall()]

            data = {"url": url,
                    "img": img,
                    "name": name,
                    "views": views,
                    "likes": likes,
                    "dur": dur,
                    "feedback": feedback,
                    "scrape_date": date,
                    "tags": tags,
                    "stars": stars}

            return data


    def yield_all(self):
        with self.lock:
            c = self.cnx.cursor()
            # order by newid makes sure we get these back in random order
            c.execute("SELECT url FROM videos ORDER BY RANDOM();")
            all_urls = [f[0] for f in c.fetchall()]

            for url in all_urls:
                yield self.get(url)


    def yield_some(self, num):
        with self.lock:
            c = self.cnx.cursor()
            # order by newid makes sure we get these back in random order
            c.execute("SELECT url FROM videos ORDER BY RANDOM();")

            for _ in range(min(num, self.size())):
                url = c.fetchone()[0]
                yield self.get(url)


    def yield_rated(self):
        with self.lock:
            c = self.cnx.cursor()
            # order by newid makes sure we get these back in random order
            c.execute("SELECT url FROM videos WHERE feedback IS NOT NULL;")
            all_urls = [f[0] for f in c.fetchall()]

            for url in all_urls:
                yield self.get(url)
