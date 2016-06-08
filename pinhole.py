# -*- coding: utf-8 -*-

import os,sys

# Import Qt modules
from PyQt4.QtGui import QApplication

from mainwindow import MainWindow

def main():
    # Again, this is boilerplate, it's going to be the same on
    # almost every app you write
    app = QApplication(sys.argv)
    windows=[MainWindow()]
    windows[0].container = windows
    windows[0].show()
    # It's exec_ because exec is a reserved word in Python
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())

