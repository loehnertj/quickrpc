# -*- coding: utf-8 -*-
import logging as L 
import os

from PyQt4.QtCore import Qt, QPointF, QSizeF, QSize, QRectF
from PyQt4.QtGui import QPixmap, QColor, QStaticText, QStyle
from PyQt4.QtGui import QGraphicsItem, QGraphicsWidget, QGraphicsPixmapItem

class ClusterWidget(QGraphicsWidget):
    def __init__(o, puzzle_board, cluster):
        super(ClusterWidget, o).__init__()
        o.setFlags(QGraphicsItem.ItemIsSelectable)
        o.puzzle_board = puzzle_board
        o.cluster = cluster
        for piece in cluster.pieces:
            o.add_piece(piece)
            
    def add_piece(o, piece, pixmap=None):
        if not pixmap:
            path = os.path.join(o.puzzle_board.imagefolder, piece.image)
            pixmap = QPixmap(path)
        item = QGraphicsPixmapItem(pixmap, parent=o)
        item.setPos(piece.x0, piece.y0)
            
    def boundingRect(o):
        return o.childrenBoundingRect()
            
    def paint(o, painter, option, widget):
        QGraphicsWidget.paint(o, painter, option, widget)
        if o.isSelected():
            painter.fillRect(o.boundingRect().adjusted(-5, -5, 5, 5), QColor("lightGray"))
            
    def updatePos(o):
        o.setPos(o.cluster.x, o.cluster.y)
        o.setRotation(-360.*o.cluster.rotation/o.cluster.rotations)
