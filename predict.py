from sklearn.feature_extraction.text import CountVectorizer
from sklearn.ensemble                import RandomForestRegressor as RandomForest
from sklearn.decomposition           import PCA
from sklearn.utils.validation        import NotFittedError
from sklearn.externals               import joblib

from scipy.sparse import coo_matrix, hstack, vstack
import numpy as np

from PySide   import QtCore
from queue    import PriorityQueue
from datetime import datetime
from copy     import copy
import os, sys, shutil

from database import Database


class Predictor:
    """
    Will the user like a particular video? Give the predictor
    the data dict you got from scraping the video url and the
    predictor will tell you what the user will rate it.

    Uses a takes a random sample of data from the user's history,
    does PCA on it to condense highly correlated features, turns
    that into a vector of numbers, then fits a random forest on
    it.
    """
    db    = Database()
    q     = PriorityQueue()
    threaded_fit = None

    def __init__(self):
        fs = os.listdir()
        if  ("model.pkl" in fs) and ("enc.pkl" in fs) and ("pca.pkl" in fs):
            self.model = joblib.load("model.pkl")
            self.enc   = joblib.load("enc.pkl")
            self.pca   = joblib.load("pca.pkl")

        else:
            self.refit_from_scratch()


    def fit(self, data):
        """
        Currently does nothing, but did (and might in
        the future) update the model incrementally.
        """
        pass


    def refit_from_scratch(self):
        """ Create a new model directly from the database, rather
         than rely on the one saved from last time."""
        print("Model is being retrained. This may take a moment.")
        # In the background fit a much larger random forest.
        self.threaded_fit = ThreadedFit()
        self.threaded_fit.signal_finished.connect(self.__init__)
        self.threaded_fit.start()

        temp_model = RandomForest(max_features="sqrt", n_jobs=-1)
        temp_enc   = CountVectorizer()
        X = []   # binary matrix the presence of tags
        Z = []   # additional numerical data
        Y = []   # target (to predict) values
        db_size = self.db.size()
        for data in self.db.yield_some(250):
            feedback = data["feedback"]
            tags     = data[  "tags"  ]
            if feedback and tags:
                Y.append(   feedback   )
                X.append(" ".join(tags))
                Z.append(self.fmt_numerical(data))

        X = temp_enc.fit_transform(X)
        X = hstack((X, coo_matrix(Z)))
        self.allX = X
        pca = PCA(min(X.shape[0], 200))
        reduced_X = pca.fit_transform(X.todense())
        temp_model.fit(reduced_X, Y)

        self.pca   = pca
        self.model = temp_model
        self.enc   = temp_enc


    def predict(self, data):
        """ Given a dict of video data, predict how much
         the user will like the video. """
        tags = " ".join(data["tags"])
        tags = self.enc.transform([tags])
        nums = coo_matrix(self.fmt_numerical(data))
        x = hstack((tags, nums))
        x = self.pca.transform(x.todense())
        return self.model.predict(x)[0]


    def fmt_numerical(self, data):
        """
        There are two categories of data Porn Sieve gathers:
          1.Tag data, represented as a binary, mostly zero array of numbers
          2. Data which is continuous, such as duration, average review, etc.

        For the tags, I can just use CountVectorizer out-of-the-box, but for
        the other data, we need to put it all together in a list on our own.
        """
        nums = []
        # sorted to ensure the data is always in the same order
        for k in sorted(data.keys()):
            if k in ["feedback", "img"]:
                pass

            elif type(data[k]) == list:
                pass

            elif data[k] == None:
                nums.append(0)

            elif (k == "scrape_date") and (type(data[k]) != float):
                stamp = datetime.strptime(data[k], "%Y-%m-%d %H:%M:%S.%f")
                epoch = datetime.utcfromtimestamp(0)
                nums.append((stamp - epoch).total_seconds())

            elif np.isreal(data[k]):
                nums.append(data[k])
        return nums


    def quit(self):
        # this no longer does anything
        pass


class ThreadedFit(QtCore.QThread, Predictor):
    signal_finished = QtCore.Signal()  # used to reload model when done

    def __init__(self):
        QtCore.QThread.__init__(self)

    def run(self):
        # making a copy of the database seems to keep
        # the scraper fast since there's not much need
        # for waiting around for the lock.
        shutil.copyfile("default.db", "_temp.db")
        db = Database("_temp.db")
        temp_model = RandomForest(max_features="sqrt", n_jobs=-1)
        temp_enc   = CountVectorizer()
        X = []   # binary matrix the presence of tags
        Z = []   # additional numerical data
        Y = []   # target (to predict) values
        db_size = db.size()
        for i, data in enumerate(db.yield_rated()):
            if self.verbose: print(i, end=" ")
            sys.stdout.flush()
            feedback = data["feedback"]
            tags     = data[  "tags"  ]
            if feedback and tags:
                Y.append(   feedback   )
                X.append(" ".join(tags))
                Z.append(self.fmt_numerical(data))

        sys.stdout.flush()
        X = temp_enc.fit_transform(X)
        X = hstack((X, coo_matrix(Z)))
        self.allX = X
        sys.stdout.flush()
        pca = PCA(min(X.shape[0], 200))
        reduced_X = pca.fit_transform(X.todense())
        sys.stdout.flush()
        temp_model.fit(reduced_X, Y)
        sys.stdout.flush()

        pca   = pca
        model = temp_model
        enc   = temp_enc

        joblib.dump(enc,   "enc.pkl"  )
        joblib.dump(model, "model.pkl")
        joblib.dump(pca,   "pca.pkl"  )

        del db
        os.remove("_temp.db")

        sys.stdout.flush()
        self.signal_finished.emit()
