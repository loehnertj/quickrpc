import os, sys
import struct
from ctypes import cdll, create_string_buffer, c_ulonglong, c_ulong, Structure, c_int, c_float
base = sys.path[0]

sofile = os.path.join(base, 'render_outline.so')
print('loading cfuncs from %s'%sofile)
try:
    cfuncs = cdll.LoadLibrary(sofile)
except OSError:
    print('could not import cfuncs')
    sys.exit(1)
    
class _RenderSettings(Structure):
    _fields_ = [
        ("border_width", c_int),
        ("max_strength", c_int),
        ("rel_strength", c_float),
        ("illum_x", c_float),
        ("illum_y", c_float),
    ]
    
class RenderSettings(object):
    def __init__(self, border_width, illum_x=0, illum_y=-1, rel_strength=.015, max_strength=144):
        self._settings = _RenderSettings(int(border_width), max_strength, rel_strength, illum_x, illum_y)
        
    def get_struct(self):
        return self._settings
    
def outline(imgptr, width, height, settings):
    cfuncs.outline(c_ulonglong(imgptr), c_int(width), c_int(height), settings.get_struct())


from PyQt4.QtGui import QApplication, QImage, QPixmap, QLabel
a = QApplication(sys.argv)
myImage = QImage()
myImage.load("puzzles/outtest/pieces/piece15.png")

w, h = myImage.width(), myImage.height()
bw = max(w, h)/20
outline(myImage.bits(), w, h, RenderSettings(bw, illum_x=-.5, illum_y=-.866))

myLabel = QLabel()
myLabel.setPixmap(QPixmap.fromImage(myImage.scaled(5*w, 5*h)))
myLabel.show()
a.exec_()