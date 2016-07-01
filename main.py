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

        self.preview_size = 2**9  # arbitrary number

        # Create the entirety of the GUI and
        # link to appropriate functions.
        self.setWindowTitle('Porn!')
        self.layout = QtGui.QHBoxLayout()

        self.init_left_pane()
        self.init_middle_pane()
        self.init_right_pane()

        self.setLayout(self.layout)
        self.show()

        self.predict = Predictor()


    def init_left_pane(self):
        self.left_pane = QtGui.QVBoxLayout()

        # NICHE COMBO: make dropdown menu to select a fetish
        self.niche_combo = QtGui.QComboBox(self)
        keys = sorted(self.xpaths.keys())
        for k in keys:
            self.niche_combo.addItem(k)
        self.niche_combo.setCurrentIndex(0)
        self.niche = keys[0]
        self.niche_combo.activated[str].connect(self.set_niche)
        self.left_pane.addWidget(self.niche_combo)

        # START PG AND PGS TO SCRAPE
        self.left_pane.addSpacing(50)
        self.init_page_btns()
        self.left_pane.addSpacing(25)

        # PROGRESS BAR: tracks the progress of the scraper
        self.prog = QtGui.QProgressBar(self)
        self.left_pane.addWidget(self.prog)

        # SCRAPE: begin scraping
        self.scrape_btn = QtGui.QPushButton("scrape", self)
        self.scrape_btn.clicked.connect(self.scrape)
        self.left_pane.addWidget(self.scrape_btn)
        self.left_pane.addSpacing(25)

        # RETRAIN: manual retraining of prediction algorithm
        self.train_btn = QtGui.QPushButton("recalculate prediction model", self)
        self.train_btn.clicked.connect(self.retrain)
        self.left_pane.addWidget(self.train_btn)
        self.left_pane.addSpacing(75)

        # QUIT: make quit button
        self.quit_btn = QtGui.QPushButton("quit", self)
        self.quit_btn.clicked.connect(self.quit)
        self.left_pane.addWidget(self.quit_btn)

        self.layout.addLayout(self.left_pane)


    def init_middle_pane(self):
        self.mid_pane = QtGui.QHBoxLayout()

        # IMGS: images which will display the video preview
        pixmap = QtGui.QPixmap("0.jpg")
        pixmap.scaledToWidth(self.preview_size)
        pixmap.scaledToHeight(self.preview_size)
        img_lbl = QtGui.QLabel(self)
        img_lbl.setPixmap(pixmap)

        # Make sure the window isn't constantly resizing
        img_lbl.setScaledContents(True)
        img_lbl.setMaximumWidth(self.preview_size)
        img_lbl.setMaximumHeight(self.preview_size)

        self.img = img_lbl
        self.mid_pane.addWidget(self.img)

        # SLIDER: slide to rate the quality of the video
        self.slider = QtGui.QSlider(self, QtCore.Qt.Vertical)
        self.slider.setTickPosition(QtGui.QSlider.TicksBothSides)
        self.slider.setTickInterval(20)
        self.mid_pane.addWidget(self.slider)

        self.layout.addLayout(self.mid_pane)


    def init_right_pane(self):
        self.right_pane = QtGui.QVBoxLayout()

        # RATE button
        self.rate_btn = QtGui.QPushButton("rate", self)
        self.rate_btn.clicked.connect(self.rate)
        self.right_pane.addWidget(self.rate_btn)

        # OPEN button
        self.open_btn = QtGui.QPushButton("open", self)
        self.open_btn.clicked.connect(lambda: webbrowser.open(self.cur_vid))
        self.right_pane.addWidget(self.open_btn)

        # INFO box
        self.info_box = QtGui.QLabel(self)
        self.info_box.setText("")
        self.right_pane.addWidget(self.info_box)

        # SKIP button
        # by some magic this is aligned correctly
        self.skip_btn = QtGui.QPushButton("skip", self)
        self.skip_btn.clicked.connect(self.skip)
        self.right_pane.addWidget(self.skip_btn)

        self.layout.addLayout(self.right_pane)


    def init_page_btns(self):
        """
        Create the start page and pages to scrape buttons along
        with their corresponding labels. Each label and spinbox
        is first grouped together vertically, then put together
        with the other spinbox horizontally and finally into the
        main layout of our window.
        """
        self.pg_spinboxes = QtGui.QHBoxLayout()

        # START PG: spinbox to indicate the page to start scraping on
        self.start_pg_group = QtGui.QVBoxLayout()
        self.start_pg_group.setAlignment(QtCore.Qt.AlignTop)

        self.start_lbl = QtGui.QLabel(self)
        self.start_lbl.setText("start page")

        self.start_pg_spn = QtGui.QSpinBox(self)
        self.start_pg_spn.valueChanged[int].connect(self.set_start_pg)

        self.start_pg_group.addWidget(self.start_lbl)     # "start page"
        self.start_pg_group.addWidget(self.start_pg_spn)  # <spinbox>
        self.pg_spinboxes.addLayout(self.start_pg_group)
        self.pg_spinboxes.addSpacing(20)

        # NUM PGS: spinbox to indicate the number of pages to scrape
        self.n_pgs_group = QtGui.QVBoxLayout()
        self.n_pgs_group.setAlignment(QtCore.Qt.AlignTop)

        self.n_pgs_lbl = QtGui.QLabel(self)
        self.n_pgs_lbl.setText("pages to scrape")

        self.n_pgs_spn = QtGui.QSpinBox(self)
        self.n_pgs_spn.valueChanged[int].connect(self.set_max_pgs)
        self.n_pgs_spn.setMinimum(1)

        self.n_pgs_group.addWidget(self.n_pgs_lbl)        # "pages to scrape"
        self.n_pgs_group.addWidget(self.n_pgs_spn)        # <spinbox>
        self.n_pgs_group.setAlignment(QtCore.Qt.Vertical)
        self.pg_spinboxes.addLayout(self.n_pgs_group)

        # Combine both in a box.
        self.pg_spinboxes.setAlignment(QtCore.Qt.AlignTop)
        self.left_pane.addLayout(self.pg_spinboxes)


    def retrain(self):
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        self.predict.refit_from_scratch()
        redo_predictions(self.predict, self.q.qsize(), self.q)
        QtGui.QApplication.restoreOverrideCursor()


    def refresh_images(self):
        try:
            r = requests.get(self.cur_img)
        except:
            time.sleep(1)
            r = requests.get(self.cur_img)

        if r.status_code == 200:
            pixmap = QtGui.QPixmap()
            pixmap.loadFromData(r.content)
            pixmap.scaledToWidth(self.preview_size)
            pixmap.scaledToHeight(self.preview_size)
            self.img.setPixmap(pixmap)
            self.img.update()
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
                                   # old design had an out of 6 scale
                                   round(self.last_pred, 2),
                                   tag_str)
        self.info_box.setText(info_str)


    def pop_video(self):
        if self.q.empty():
            self.info_box.setText("Video queue empty.")
            self.repaint()
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
            for _ in range(4):
                if not self.thr.exit_ready:
                    time.sleep(0.25)
            del self.thr
        self.update_prog(0)
        self.thr = PopulateQ(
                              self.site,        self.niche,        self.q,
                              self.start_pg,    self.max_pgs,      self.winlock,
                              self.predict
                            )
        self.thr.updateProgress.connect(self.update_prog)
        self.thr.start()


    def rate(self):
        self.db.give_feedback(self.cur_vid, self.slider.value())
        data = self.db.get(self.cur_vid)
        data["feedback"] = self.slider.value() + 0.0001 # db doesn't like 0s
        with self.winlock:
            self.predict.fit(data)
        if self.q.empty():
            self.info_box.setText("Queue Empty")
            self.repaint()
            self.default_img_flag = True
        else:
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
        if self.q.empty():
            self.info_box.setText("Queue Empty")
            self.repaint()
            self.default_img_flag = True
        else:
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
            for _ in range(4):
                if not self.thr.exit_ready:
                    time.sleep(0.25)
        QtCore.QCoreApplication.instance().quit()


def main():
    app = QtGui.QApplication(sys.argv)
    win = Window()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
