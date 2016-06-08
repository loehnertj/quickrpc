# -*- coding: utf-8 -*-
"""implements a QGraphicsWidget representing and showing a picture"""
import logging as L 

from PyQt4.QtCore import Qt, QPointF, QSizeF, QSize, QRectF
from PyQt4.QtGui import QPixmap, QColor, QStaticText
from PyQt4.QtGui import QGraphicsWidget

class PictureWidget(QGraphicsWidget):
    loaded=False
    filename=''
    
    def __init__(self, filename=""):
        super(PictureWidget, self).__init__()
        self.filename = filename
        self.pxm = QPixmap(self.filename)
        
    def boundingRect(self):
        w, h = self.pxm.width(), self.pxm.height()
        L.debug("boundingrect: %r %r"%(w,h))
        return QRectF(0,0, w, h)
        
    def paint(self, painter, option, widget):
        painter.drawPixmap(0, 0, self.pxm)