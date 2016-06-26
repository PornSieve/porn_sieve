import sys, time, random

from threading import Thread, RLock
from queue     import PriorityQueue

from PySide import QtGui, QtCore
import requests
import webbrowser

from misc      import get_niche_xpaths, fmt_img, redo_predictions
from scraper   import PopulateQ
from database  import Database
from predict   import Predictor


class Window(QtGui.QWidget):
    """ The graphical interface to the software that the user sees. """
    def __init__(self):
        super(Window, self).__init__()
        self.site     = "xvideos"
        self.xpaths   = get_niche_xpaths(self.site)
        self.start_pg = 0
        self.max_pgs  = 0
        self.cur_vid  = None
        self.cur_img  = None

        self.winlock    = RLock()
        self.thr        = None

        self.db  = Database()
        self.q   = PriorityQueue()

        self.default_img_flag = True

        self.init_ui()
        self.predict = Predictor()


    def init_ui(self):
        """ Create the entirety of the GUI and
          link to appropriate functions. """
        self.setWindowTitle('Porn!')
        self.layout = QtGui.QGridLayout()

        # NICHE COMBO: make dropdown menu to select a fetish
        self.niche_combo = QtGui.QComboBox(self)
        keys = sorted(self.xpaths.keys())
        for k in keys:
            self.niche_combo.addItem(k)
        self.niche_combo.setCurrentIndex(0)
        self.niche = keys[0]
        self.niche_combo.activated[str].connect(self.set_niche)
        self.layout.addWidget(self.niche_combo, 0, 0, 1, 2)

        # START PG: spinbox to indicate the page to start scraping on
        self.start_lbl = QtGui.QLabel(self)
        self.start_lbl.setText("start page")
        self.layout.addWidget(self.start_lbl, 2, 0, 1, 1)

        self.start_pg_spn = QtGui.QSpinBox(self)
        self.start_pg_spn.valueChanged[int].connect(self.set_start_pg)
        self.layout.addWidget(self.start_pg_spn, 3, 0, 1, 1)

        # NUM PGS: spinbox to indicate the number of pages to scrape
        self.n_pgs_lbl = QtGui.QLabel(self)
        self.n_pgs_lbl.setText("pages to scrape")
        self.layout.addWidget(self.n_pgs_lbl, 2, 1, 1, 1)

        self.n_pgs_spn = QtGui.QSpinBox(self)
        self.n_pgs_spn.setMinimum(1)
        self.n_pgs_spn.valueChanged[int].connect(self.set_max_pgs)
        self.layout.addWidget(self.n_pgs_spn, 3, 1, 1, 1)

        # PROGRESS BAR: tracks the progress of the scraper
        self.prog = QtGui.QProgressBar(self)
        self.layout.addWidget(self.prog, 6, 0, 1, 2)

        # SCRAPE: begin scraping
        self.scrape_btn = QtGui.QPushButton("scrape", self)
        self.scrape_btn.clicked.connect(self.scrape)
        self.layout.addWidget(self.scrape_btn, 7, 0, 1, 2)

        # RETRAIN: manual retraining of prediction algorithm
        self.train_btn = QtGui.QPushButton("recalculate prediction model", self)
        self.train_btn.clicked.connect(self.retrain)
        self.layout.addWidget(self.train_btn, 9, 0, 1, 2)

        # QUIT: make quit button
        self.quit_btn = QtGui.QPushButton("quit", self)
        self.quit_btn.clicked.connect(self.quit)
        self.layout.addWidget(self.quit_btn, 11, 0, 1, 2)

        # IMGS: images which will display the video preview
        img_len = 12
        self.imgs = []
        pic_num = 0
        pixmap = QtGui.QPixmap("0.jpg")
        img_lbl = QtGui.QLabel(self)
        img_lbl.setPixmap(pixmap)
        self.imgs.append(img_lbl)
        self.layout.addWidget(img_lbl, 0, 3, img_len, img_len)

        # SLIDER: slide to rate the quality of the video
        self.slider = QtGui.QSlider(self, QtCore.Qt.Vertical)
        self.slider.setTickPosition(QtGui.QSlider.TicksBothSides)
        self.slider.setTickInterval(20)
        self.layout.addWidget(self.slider, 0, img_len + 3, img_len, 1)

        # RATE button
        self.rate_btn = QtGui.QPushButton("rate", self)
        self.rate_btn.clicked.connect(self.rate)
        self.layout.addWidget(self.rate_btn, 0, img_len + 4, 1, 2)

        # OPEN button
        self.open_btn = QtGui.QPushButton("open", self)
        self.open_btn.clicked.connect(lambda: webbrowser.open(self.cur_vid))
        self.layout.addWidget(self.open_btn, 1, img_len + 4, 1, 2)

        # INFO box
        self.info_box = QtGui.QLabel(self)
        self.info_box.setText("")
        self.layout.addWidget(self.info_box, 3, img_len + 4, 1, 1)

        # SKIP button
        self.skip_btn = QtGui.QPushButton("skip", self)
        self.skip_btn.clicked.connect(self.skip)
        self.layout.addWidget(self.skip_btn, img_len - 1, img_len + 4, 1, 2)

        self.setLayout(self.layout)
        self.show()


    def retrain(self):
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        self.predict.refit_from_scratch()
        redo_predictions(self.predict, self.q.qsize(), self.q)
        QtGui.QApplication.restoreOverrideCursor()


    def refresh_images(self):
        r = requests.get(self.cur_img)
        if r.status_code == 200:
            pixmap = QtGui.QPixmap()
            pixmap.loadFromData(r.content)
            pixmap.scaledToWidth(255)     # 255 is just an arbitrary size
            pixmap.scaledToHeight(255)
            self.imgs[0].setPixmap(pixmap)
            self.imgs[0].update()
            self.repaint()
        r.close()
        data = self.db.get(self.cur_vid)

        self.setWindowTitle(data["name"])
        info_str = "dur: {}\n\nviews: {}\n\nprediction: {}\n\ntags: {}"

        n_tags = 15
        tag_str = ""
        if data["tags"]:
            tags = [tag for tag in data["tags"] if len(tag) > 2]
            tags = tags[:min(n_tags, len(data["tags"]))]
            for tag in tags:
                tag_str += "\n" + tag


        info_str = info_str.format(data["dur"],
                                   data["views"],
                                   round(self.last_pred, 2),
                                   tag_str)
        self.info_box.setText(info_str)


    def pop_video(self):
        if self.q.empty():
            self.info_box.setText("Video queue empty.")
            return self.last_pred, self.cur_vid
        self.last_pred, self.cur_vid = self.q.get()
        self.last_pred *= -1
        self.cur_img = self.db.get_img(self.cur_vid)
        return self.last_pred, self.cur_vid


    def set_start_pg(self, num):
        self.start_pg = num


    def set_max_pgs(self, num):
        self.max_pgs = num


    def scrape(self):
        if self.thr:
            self.thr.exit_flag = True
            while not self.thr.exit_ready:
                time.sleep(0.5)
        self.update_prog(0)
        self.thr = PopulateQ(
                              self.site,        self.niche,        self.q,
                              self.start_pg,    self.max_pgs,      self.winlock,
                              self.predict
                            )
        self.thr.updateProgress.connect(self.update_prog)
        self.thr.start()


    def rate(self):
        self.db.give_feedback(self.cur_vid, self.slider.value()/100*6)
        data = self.db.get(self.cur_vid)
        data["feedback"] = self.slider.value() + 0.0001 # db doesn't like 0s
        with self.winlock:
            self.predict.fit(data)
        self.pop_video()
        self.refresh_images()


    def update_prog(self, progress):
        self.prog.setValue(progress)
        if self.default_img_flag:
            if not self.q.empty():
                _, vid_url = self.pop_video()
                self.refresh_images()
                self.default_img_flag = False


    def update_prog_init(self, progress):
        self.prog.setValue(progress)
        self.repaint()


    def skip(self):
        self.pop_video()
        self.refresh_images()


    def set_niche(self, text):
        if text == "select niche":
            self.niche = None
        self.niche = text


    def quit(self):
        self.db.cnx.close()
        self.predict.quit()
        if self.thr:
            self.thr.exit_flag = True
            while not self.thr.exit_ready:
                pass
        QtCore.QCoreApplication.instance().quit()


def main():
    app = QtGui.QApplication(sys.argv)
    win = Window()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
