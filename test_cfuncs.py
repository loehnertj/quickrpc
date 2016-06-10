import os, sys
from render_outline import outline

from PyQt4.QtGui import QApplication, QImage, QPixmap, QLabel
a = QApplication(sys.argv)
myImage = QImage()
myImage.load("puzzles/outtest/pieces/piece15.png")

outline(myImage, illum_angle=-30)
w, h = myImage.width(), myImage.height()

myLabel = QLabel()
myLabel.setPixmap(QPixmap.fromImage(myImage.scaled(5*w, 5*h)))
myLabel.show()
a.exec_()