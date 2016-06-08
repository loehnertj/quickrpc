import types 
import logging
L = lambda: logging.getLogger(__name__)

from PyQt4.QtCore import Qt, QPoint, QPointF, QSizeF, QSize, QRectF
from PyQt4.QtGui import QGraphicsView, QGraphicsScene

class InputTrackerEvent(object):
    def __init__(o):
        o.key = None
        o.modifiers = None
        o.startPos = o.startScreenPos = o.startScenePos = None
        o.lastPos = o.lastScreenPos = o.lastScenePos = None
        o.isDrag = False

class InputTracker(object):
    '''receives input events for the given widget and detects clicks and drags.
    
    Special in that "clicks" and "drags" for keyboard keys are detected as well.
    setMouseTracking(true) on the view!
    
    In turn, this calls event handlers of the widget:
    
     * onInputDown(ev): as soon as a button is down
     * onInputMove(ev): mouse move event with held button or key
     * onInputUp(ev): when button is up again
     
    `ev` has the properties:
        key: the key or mouse button that was used (Qt.XButton or Qt.Key_X)
        startPos, startScreenPos, startScenePos: where button went down
        lastPos, lastScreenPos, lastScenePos: current / end position
        modifiers: keyboard modifiers (at start time)
        isDrag: True if drag was detected (mouse moved >3px)
        
    NOTE that you do not have to "call" the properties (unlike as for Qt events).
    You will receive the same event instance all the time.
    
    Args:
        widget: the widget to handle
        accept: List of keys that the handler accepts: Qt.XButton or Qt.KeyX
        drag_treshold: the mouse movement in screen pixels to detect a drag.
                
    The input tracker requires forwarding of mouse{Press,Move,Release}Event and
    key{Press,Release}Event.
    
    If your widget does not implement any of those handlers, it will
    automatically added with the proper forward in place.
    
    However if you implement one of those handlers, call input_tracker.<handler>(ev) 
    explicitly. Otherwise InputTracker will not work as expected.
    '''
        
    def __init__(o, widget, accepts, drag_threshold=8):
        o.widget = widget
        o.accepts = accepts
        o.drag_threshold = drag_threshold
        
        # determine which handlers to autowire
        for key in 'MP,MM,MR,KP,KR'.split(','):
            # generate handler name
            method = (
                {'M':'mouse', 'K':'key'}[key[0]]
                + {'P': 'Press', 'M': 'Move', 'R': 'Release'}[key[1]]
                + 'Event'
            )
            # setup forwarding of widget.<method> to o.<method>
            
            def forward(method):
                def handle(ev):
                    if isinstance(widget, QGraphicsScene):
                        #getattr(QGraphicsScene, method)(widget, ev)
                        pass
                    elif isinstance(widget, QGraphicsView):
                        getattr(QGraphicsView, method)(widget, ev)
                    else:
                        print('dont know superclass')
                    getattr(o, method)(ev)
                setattr(widget, method, handle)
            
            if not hasattr(widget, method) or isinstance(getattr(widget, method), types.BuiltinFunctionType):
                L().debug('inputTracker: autoforward widget.'+method)
                forward(method)
            else:
                m = getattr(widget, method)
                L().debug('inputTracker: already there: %r'%getattr(widget,method))
        
        # create empty event handlers for my events if not there.
        for name in 'onInputDown', 'onInputUp', 'onInputMove':
            if not hasattr(widget, name):
                setattr(widget, name, lambda o, ev: None)
        
        # map of currently active events, by key
        o.active_events = {}
        o._last_mouse_pos = QPointF()
        o._last_mouse_screen_pos = QPoint()
        o._last_mouse_scene_pos = QPointF()
        
    def mouseMoveEvent(o, ev):
        o._last_mouse_pos = ev.pos()
        try:
            o._last_mouse_screen_pos = ev.screenPos()
            o._last_mouse_scene_pos = ev.scenePos()
        except AttributeError:
            pass
        # update all active events and send onInputMove
        for iev in o.active_events.values():
            iev.lastPos = QPointF(ev.pos())
            try:
                iev.lastScreenPos = QPoint(ev.screenPos())
                iev.lastScenePos = QPointF(ev.scenePos())
            except AttributeError:
                pass
            if iev.startScreenPos:
                if (iev.lastScreenPos - iev.startScreenPos).manhattanLength() > o.drag_threshold:
                    iev.isDrag = True
            elif iev.startPos:
                if (iev.lastPos - iev.startPos).manhattanLength() > o.drag_threshold:
                    iev.isDrag = True
            o.widget.onInputMove(iev)
        
    def mousePressEvent(o, ev):
        if ev.button() not in o.accepts:
            return
        #ev.accept()
        iev = InputTrackerEvent()
        iev.key = ev.button()
        iev.modifiers = ev.modifiers()
        iev.startPos = QPointF(ev.buttonDownPos(ev.button()))
        try:
            iev.startScreenPos = QPoint(ev.buttonDownScreenPos(ev.button()))
            iev.startScenePos = QPointF(ev.buttonDownScenePos(ev.button()))
        except AttributeError:
            pass
        o.active_events[ev.button()] = iev
        o.widget.onInputDown(iev)
    
    def mouseReleaseEvent(o, ev):
        if ev.button() not in o.accepts:
            return
        #ev.accept()
        try:
            iev = o.active_events[ev.button()]
            del o.active_events[ev.button()]
        except:
            L().debug('InputTracker: mouse Release without preceding press')
            iev = InputTrackerEvent()
        iev.lastPos = QPointF(ev.lastPos())
        try:
            iev.lastScreenPos = QPoint(ev.lastScreenPos())
            iev.lastScenePos = QPointF(ev.lastScenePos())
        except AttributeError:
            pass
        o.widget.onInputUp(iev)
        
    def keyPressEvent(o, ev):
        if ev.isAutoRepeat(): return
        if ev.key() not in o.accepts:
            return
        #ev.accept()
        iev = InputTrackerEvent()
        iev.key = ev.key()
        iev.modifiers = ev.modifiers()
        iev.startPos = o._last_mouse_pos
        try:
            iev.startScreenPos = o._last_mouse_screen_pos
            iev.startScenePos = o._last_mouse_scene_pos
        except AttributeError:
            pass
        o.active_events[ev.key()] = iev
        o.widget.onInputDown(iev)
    
    def keyReleaseEvent(o, ev):
        if ev.isAutoRepeat(): return
        if ev.key() not in o.accepts:
            return
        #ev.accept()
        try:
            iev = o.active_events[ev.key()]
            del o.active_events[ev.key()]
        except:
            L().debug('InputTracker: key Release without preceding press')
            iev = InputTrackerEvent()
        iev.lastPos = o._last_mouse_pos
        try:
            iev.lastScreenPos = o._last_mouse_screen_pos
            iev.lastScenePos = o._last_mouse_scene_pos
        except AttributeError:
            pass
        o.widget.onInputUp(iev)
    