# -*- coding: utf-8 -*-
"""a QGraphicScene"""

import os
import logging
L = lambda: logging.getLogger(__name__)

from PyQt4.QtCore import Qt, QPointF, QSizeF, QSize, QRectF
from PyQt4.QtGui import QBrush, QColor, QPen, QPixmap
from PyQt4.QtGui import QGraphicsScene, QGraphicsRectItem

from input_tracker import InputTracker
from cluster_widget import ClusterWidget
from puzzleboard.puzzle_board import PuzzleBoard

KEYS = {
    # non-drag actions
    'grab': [Qt.LeftButton, Qt.Key_Space],
    'sel_clear': [Qt.Key_W],
    'sel_rearrange': [Qt.Key_E],
    'rotate_CW': [Qt.RightButton, Qt.Key_D],
    'rotate_CCW': [Qt.Key_A],
    'zoom': [Qt.Key_Q],
    
    # drag actions
    'pan': [Qt.LeftButton, Qt.Key_Space],
    'deselect': [Qt.Key_W],
    
    # both
    'select': [Qt.RightButton, Qt.Key_S],
}

class PuzzleScene(QGraphicsScene):
    def __init__(o, parent, puzzle_board, *args):
        QGraphicsScene.__init__(o, parent, *args)
        o._input_tracker = InputTracker(o, 
            accepts=sum(KEYS.values(), [])
        )
        
        o.setBackgroundBrush(QBrush(QColor("darkGray")))
        o.puzzle_board = puzzle_board
        o.cluster_map = {}
        o._display_puzzle_board(puzzle_board)
        
        
        # init piece movement
        o.grab_active = False
        o.grabbed_widgets = None
        o.move_grab_offsets = None
        o.move_rotation = 0
        o._old_clusters = set()
        
        # init selection
        o._drag_start = None
        o._rubberband = QGraphicsRectItem(QRectF(0., 0., 100., 100.))
        p = QPen(QColor(255,255,255))
        #p.setWidth(5)
        o._rubberband.setPen(p)
        o._rubberband.hide()
        o.addItem(o._rubberband)
        
        
    def _display_puzzle_board(o, puzzle_board):
        for cluster in puzzle_board.clusters:
            cw = ClusterWidget(puzzle_board=puzzle_board, cluster=cluster)
            o.addItem(cw)
            o.cluster_map[cluster] = cw
            cw.updatePos()
        o.updateSceneRect()
        
        
    def toggle_grab_mode(o, scene_pos, grab_active=None):
        if grab_active is None:
            grab_active = not o.grab_active
            
        if o.grabbed_widgets:
            if grab_active: return
            o.dropGrabbedWidgets()
        else:
            if not grab_active: return
            o.tryGrabWidgets(scene_pos)
            
        o.grab_active = bool(o.grabbed_widgets)
    
    def tryGrabWidgets(o, scene_pos):
        item = o.itemAt(scene_pos)
        if item:
            widget = item.parentWidget()
            if widget.isSelected():
                # lift all selected clusters
                o.grabbed_widgets = o.selectedItems()
            else:
                o.grabbed_widgets = [widget]
            o.move_grab_offsets = [w.pos() - scene_pos for w in o.grabbed_widgets]
            o.move_rotation = 0
        L().debug("lift: " + o.grabbed_widgets.__repr__())
        
    def rotateGrabbedWidgets(o, clockwise=False):
        o.move_rotation += (-1 if clockwise else 1)
        for widget in o.grabbed_widgets:
            r_deg = -360.*(widget.cluster.rotation + o.move_rotation)/widget.cluster.rotations
            L().debug('new rotation: %g, in deg: %g'%(o.move_rotation, r_deg))
            widget.setRotation(r_deg)
                
    def dropGrabbedWidgets(o):
        for widget in o.grabbed_widgets:
            o.dropWidget(widget)
        for widget in o.grabbed_widgets:
            o.checkJoin(widget)
        o.grabbed_widgets = None
        L().debug('dropped')
        o.updateSceneRect()
            
    def dropWidget(o, widget):
        new_pos = widget.pos()
        rotation = (o.move_rotation + widget.cluster.rotation) % widget.cluster.rotations
        if rotation<0:
            rotation += widget.cluster.rotations
        o.puzzle_board.move_cluster(cluster=widget.cluster, x=new_pos.x(), y=new_pos.y(), rotation=rotation)
        
    def checkJoin(o, widget):
        jc = o.puzzle_board.joinable_clusters(widget.cluster)
        if jc:
            o.puzzle_board.join(clusters=jc, to_cluster=widget.cluster)
            # The clusters in jc have been merged into to_cluster. move piece items accordingly.
            for other_cluster in jc:
                cw = o.cluster_map[other_cluster]
                # reparent piece images
                for item in cw.childItems():
                    item.setParentItem(widget)
                # delete item
                if cw in o.grabbed_widgets:
                    o.grabbed_widgets.remove(cw)
                o.removeItem(cw)
                del o.cluster_map[other_cluster]
                # apparently Qt does not take it so well when the old cluster is GC'd
                # at the wrong time. prevent by keeping around a ref.
                # FIXME: mem leak...
                o._old_clusters.add(cw)
            # update position from puzzleboard
            widget.updatePos()

        
    def repositionGrabbedPieces(o, scene_pos):
        for widget, ofs in zip(o.grabbed_widgets, o.move_grab_offsets):
            x, y = widget.cluster.rotate(ofs.x(), ofs.y(), o.move_rotation)
            widget.setPos(scene_pos + QPointF(x, y))
            
            
    def selectionRearrange(o, pos=None):
        items = o.selectedItems()
        clusters = [i.cluster for i in items]
        # FIXME: get center of mass from clusters
        pos = (pos.x(), pos.y()) if pos else None
        # fixme: order by position
        o.puzzle_board.rearrange(clusters, pos)
        for item in items:
            item.setPos(item.cluster.x, item.cluster.y)
        o.updateSceneRect()
        
    def updateSceneRect(o):
        r = o.itemsBoundingRect()
        w, h = r.width(), r.height()
        a = .1
        r = r.adjusted(-w*a, -h*a, w*a, h*a)
        o.setSceneRect(r)
    
    
    # events
    def mouseMoveEvent(o, ev):
        QGraphicsScene.mouseMoveEvent(o, ev)
        o._input_tracker.mouseMoveEvent(ev)
        if o.grab_active:
            o.repositionGrabbedPieces(ev.scenePos())
            
    # disable default behaviour
    def mouseDoubleClickEvent(o, ev):
        pass
            
    def onInputDown(o, iev):
        if iev.key in KEYS['rotate_CW']+KEYS['rotate_CCW']:
            # if no pieces are grabbed, try to get some
            if not o.grab_active and iev.key!=Qt.RightButton:
                o.toggle_grab_mode(iev.startScenePos)
            if o.grab_active:
                o.rotateGrabbedWidgets(clockwise=(iev.key in KEYS['rotate_CW']))
                o.repositionGrabbedPieces(iev.startScenePos)
        elif iev.key in KEYS['zoom']:
            o.parent().toggleZoom()
    
    def onInputMove(o, iev):
        if iev.isDrag:
            if iev.key in KEYS['select']+KEYS['deselect']:
                if not o.grab_active:
                    # continuously update drag
                    o._drag_start = iev.startScenePos
                    o._rubberband.setRect(QRectF(o._drag_start, iev.lastScenePos))
                    o._rubberband.show()
            if iev.key in KEYS['pan']:
                o.parent().togglePan(True)
    
    def onInputUp(o, iev):
        if iev.isDrag:
            if iev.key in KEYS['select']+KEYS['deselect']:
                print('end of select/deselect')
                frame = QRectF(o._drag_start, iev.lastScenePos)
                items = o.items(frame, Qt.ContainsItemBoundingRect, Qt.AscendingOrder)
                # deselect on Shift+Select or Deselect key.
                select = True
                if iev.key in KEYS['deselect'] or (iev.modifiers & Qt.ShiftModifier):
                    select=False
                print( '..')
                for item in items:
                    if not isinstance(item, ClusterWidget): continue
                    item.setSelected(select)
                print('B')
                o._drag_start = None
                o._rubberband.hide()
                print('C')
            if iev.key in KEYS['pan']:
                o.parent().togglePan(False)
        else:
            if iev.key in KEYS['select']:
                if not o.grab_active:
                    item = o.itemAt(iev.startScenePos)
                    if not item: return
                    widget = item.parentWidget()
                    widget.setSelected(not widget.isSelected())
            elif iev.key in KEYS['sel_rearrange']:
                o.selectionRearrange(iev.lastScenePos)
            elif iev.key in KEYS['sel_clear']:
                o.clearSelection()
            elif iev.key in KEYS['grab']:
                o.toggle_grab_mode(iev.startScenePos)