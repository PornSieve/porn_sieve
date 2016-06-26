import unittest
import requests
import responses
import os
import time

from PySide.QtGui  import *
from PySide.QtCore import *
from PySide.QtTest import *

from main     import *
from scraper  import *
from misc     import *
from database import *


class FunctionTests(unittest.TestCase):
    def setUp(self):
        self.niches = get_niche_xpaths("xvideos")


    def test_download(self):
        pg = download("http://www.google.com")
        self.assertIsNotNone(pg.xpath("//html"))


    def test_niche_xpaths(self):
        self.assertEqual(type(self.niches), dict)
        self.assertEqual(len(self.niches.keys()), 35)
        self.assertEqual(self.niches["Amateur"], "/c/Amateur-17")
        self.assertEqual(self.niches["Teen"], "/c/Teen-13")


    def test_fmt_gallery(self):
        fmted = fmt_gallery("xvideos", "Amateur", 0)
        self.assertEqual(fmted, "http://www.xvideos.com/c/0/Amateur-17")

        fmted = fmt_gallery("xvideos", "New", 0)
        self.assertEqual(fmted, "http://www.xvideos.com")

        fmted = fmt_gallery("xvideos", "New", 1)
        self.assertEqual(fmted, "http://www.xvideos.com/new/1")

        fmted = fmt_gallery("xvideos", "Teen", 123456)
        self.assertEqual(fmted, "http://www.xvideos.com/c/123456/Teen-13")


    @responses.activate
    def test_scrape_video(self):
        fake_vid = "http://www.xvideos.mock/video1234/buttfuckpussysquirt"

        with open("mock_data/mock_vid.dat") as f:
            fake_data = f.readlines()

        responses.add(responses.GET,
                      fake_vid,
                      body="{%s}" % fake_data,
                      content_type="application/json",
                      status=200)

        data = scrape_video(fake_vid)
        self.assertAlmostEqual(data["dur"], 73)
        self.assertEqual(data["name"], 'bobbi starr and dana dearmind gang bang ')
        self.assertAlmostEqual(data["views"], 4227718)
        for tag in ["anal", "black", "tits", "ass", "slut", "suck", "fuck",
                    "swallow", "dp", "gape", "pussyfucking", "gangbang",
                    "assfucking", "cumswap", "loads", "blowbang", "loads",
                    "gang", "bang"]:
            self.assertTrue(tag in data["tags"])
        self.assertTrue("bobbi starr" in data["stars"])


app = QApplication(sys.argv)
class GUITests(unittest.TestCase):
    def setUp(self):
        self.win = Window()
        self.paths = get_niche_xpaths("xvideos")


    def test_press_all_the_buttons(self):
        QTest.mouseClick(self.win.quit_btn , Qt.LeftButton)
        QTest.mouseClick(self.win.rate_btn , Qt.LeftButton)
        QTest.mouseClick(self.win.skip_btn , Qt.LeftButton)
        QTest.mouseClick(self.win.train_btn, Qt.LeftButton)


    def test_combobox_values(self):
        for i, niche in enumerate(sorted(self.paths.keys())):
            self.assertEqual(self.win.niche_combo.currentText(), niche)
            self.win.niche_combo.setCurrentIndex(i+1)


    def test_spinboxes(self):
        self.win.start_pg_spn.setValue(-1)
        self.assertEqual(self.win.start_pg_spn.value(), 0)

        self.win.n_pgs_spn.setValue(0)
        self.assertEqual(self.win.n_pgs_spn.value(), 1)

    @responses.activate
    def test_lock(self):
        # generate a fake gallery page
        fake_vid = "http://www.xvideos.com/c/0/Amateur-17"

        with open("mock_data/mock_gallery.dat") as f:
            fake_data = f.readlines()

        responses.add(responses.GET,
                      fake_vid,
                      body="{%s}" % fake_data,
                      content_type="application/json",
                      status=200)

        # now we have to generate fake links that come from that page
        links = list(scrape_gallery(fake_vid))

        with open("mock_data/mock_vid.dat") as f:
            fake_vid = f.readlines()

        for link, _ in links:
            responses.add(responses.GET,
                          link,
                          body="{%s}" % fake_data,
                          content_type="application/json",
                          status=200)

        self.win.scrape()
        print("sleeping 10 seconds")
        time.sleep(10)
        print("done sleeping")
        with self.win.winlock:
            print("winlock acquired")
            self.assertFalse(self.win.q.empty())
            self.win.exit_flag = True
        print("sleeping again")
        time.sleep(2)
        print("done sleeping")
        self.win.scrape()


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.db = Database(dbname="test.db")

    def test_db_functions(self):
        data = {"url": "http://www.test.com",
                "img": "http://www.test.com/img.jpg",
                "name": "hot unit tests gone wild",
                "views":    77,
                "likes":    0.75,
                "dur":      23.3,
                "tags": ['anal', 'oral', 'vaginal']}
        self.db.save(data)
        got_back = self.db.get(data["url"])
        for k in data.keys():
            if k == "tags":
                for tag in data["tags"]:
                    self.assertTrue(tag in got_back["tags"])
            self.assertAlmostEqual(data[k], got_back[k])

        self.assertTrue(self.db.was_visited(data["url"]))
        self.db.save_feedback(data["url"], 3.37)

        self.db.delete(data["url"])
        self.assertFalse(self.db.was_visited(data["url"]))

    def tearDown(self):
        os.remove("test.db")


if __name__ == '__main__':
    unittest.main()
