import unittest
import os
import sys
import random
from itertools import chain

from database import *


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.db = Database(dbname="_test.db")


    def test_all_functions(self):
        """ Test every function. """
        # data goes in
        vid_data = {
                     "url":   "http://www.unixxx.net/man_touch.html",
                     "img":   "http://www.unixxx.net/penetration_tester.html",
                     "name":  "payload injected through backdoor vulnerability",
                     "views": 15,
                     "likes": 52,
                     "dur":   2.03,
                     "stars": ["ada", "brittany", "charlise"],
                     "tags":  ["apple", "banana", "cucumber", "durian"]
                   }
        self.db.save(vid_data)
        self.db.save_feedback(vid_data["url"], 5)

        # data comes out
        got = self.db.get(vid_data["url"])

        # is it the same data?
        self.assertTrue(self.db.was_visited(vid_data["url"]))
        self.assertEqual(self.db.get_img(vid_data["url"]), vid_data["img"])
        for k in vid_data.keys():
            if k not in ["tags", "stars"]:
                self.assertEqual(vid_data[k], got[k])

        for data in self.db.yield_all():
            self.assertTrue(data)

        for data in self.db.yield_rated():
            self.assertTrue(data["feedback"])

        for i, data in enumerate(self.db.yield_some(self.db.size() - 1)):
            i = 0

        self.assertEqual(self.db.amt_of_feedback(), 2)


        # is it different in the way it's supposed to be different?
        for tag in chain(vid_data["tags"], vid_data["stars"]):
            self.assertTrue(tag in got["tags"])


        # can I delete a record?
        self.db.delete(vid_data["url"])
        self.assertEqual(self.db.size(), 1)


    def test_fuzzy(self):
        """ Throw some gobbledygook into the database to see if it breaks. """
        def gobbledy():
            letters = []
            for _ in range(random.randint(1, 100)):
                letters.append( chr(random.randint(0, 10000)) )
            return " ".join(letters)

        print("Fuzzing:", end="")
        for i in range(100):
            if i % 10 == 0:
                print(end="\n\t")
            print(str(i).ljust(4), end="")
            sys.stdout.flush()
            vid_data = {
                         "url":   "http://www." + gobbledy() + ".com",
                         "img":   "http://www." + gobbledy() + ".com",
                         "name":  gobbledy(),
                         "views": random.randint(0, 10000),
                         "likes": random.randint(0, 10000),
                         "dur":   random.random(),
                         "stars": [gobbledy() for _ in range(random.randint(0, 1000))],
                         "tags":  [gobbledy() for _ in range(random.randint(0, 1000))]
                       }
            # The rest is identical to test_save
            # data comes out
            self.db.save(vid_data)
            self.db.save_feedback(vid_data["url"], 5)

            # is it the same data?
            got = self.db.get(vid_data["url"])
            self.assertTrue(self.db.was_visited(vid_data["url"]))
            self.assertEqual(self.db.get_img(vid_data["url"]), vid_data["img"])
            for k in vid_data.keys():
                if k not in ["tags", "stars"]:
                    self.assertEqual(vid_data[k], got[k])

            for data in self.db.yield_all():
                self.assertTrue(data)

            for data in self.db.yield_rated():
                self.assertTrue(data["feedback"])

            for i, data in enumerate(self.db.yield_some(self.db.size() - 1)):
                i = 0

            self.assertEqual(self.db.amt_of_feedback(), i+2)


            # is it different in the way it's supposed to be different?
            for tag in chain(vid_data["tags"], vid_data["stars"]):
                self.assertTrue(tag in got["tags"])


            # can I delete a record?
            self.db.delete(vid_data["url"])
            self.assertEqual(self.db.size(), 1)


    def tearDown(self):
        os.remove("_test.db")


if __name__ == "__main__":
    unittest.main()
