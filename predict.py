from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model            import PassiveAggressiveRegressor
from sklearn.utils.validation        import NotFittedError
from sklearn.externals               import joblib

from scipy.sparse import coo_matrix, hstack, vstack
import numpy as np

from PySide   import QtCore
from queue    import PriorityQueue
from datetime import datetime
from copy     import copy
import os

from database import Database


class Predictor:
    db    = Database()
    q     = PriorityQueue()
    allX  = []

    def __init__(self):
        if ("model.pkl" in os.listdir()) and ("enc.pkl" in os.listdir()):
            self.model = joblib.load("model.pkl")
            self.enc = joblib.load("enc.pkl")

        else:
            self.refit_from_scratch()


    def fit(self, data):
        x1 = self.enc.transform([" ".join(data["tags"])])
        x2 = self.fmt_numerical(data)
        x  = hstack((x1, coo_matrix(x2)))
        vstack((self.allX, x))
        self.model.partial_fit(x.getrow(0), [data["feedback"]])


    def refit_from_scratch(self):
        temp_model = PassiveAggressiveRegressor(0.1)
        temp_enc   = CountVectorizer()
        X = []   # binary matrix the presence of tags
        Z = []   # additional numerical data
        Y = []   # target (to predict) values
        db_size = self.db.size()
        for data in self.db.yield_all():
            feedback = data["feedback"]
            tags     = data[  "tags"  ]
            if feedback and tags:
                Y.append(   feedback   )
                X.append(" ".join(tags))
                Z.append(self.fmt_numerical(data))

        X = temp_enc.fit_transform(X)
        X = hstack((X, coo_matrix(Z)))
        self.allX = X
        for i in range(X.shape[0]):
            temp_model.partial_fit(X.getrow(i), [Y[0]])
        self.model = temp_model
        self.enc = temp_enc


    def predict(self, data):
        tags = " ".join(data["tags"])
        tags = self.enc.transform([tags])
        nums = coo_matrix(self.fmt_numerical(data))
        return self.model.predict( hstack((tags, nums)) )[0]


    def fmt_numerical(self, data):
        nums = []
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
        joblib.dump(self.enc, "enc.pkl")
        joblib.dump(self.model, "model.pkl")
