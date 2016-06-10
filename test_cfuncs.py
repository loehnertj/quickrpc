import os, sys
from ctypes import cdll, create_string_buffer, c_ulonglong, c_ulong
base = sys.path[0]

sofile = os.path.join(base, 'cfuncs.so')
print('loading cfuncs from %s'%sofile)
try:
    cfuncs = cdll.LoadLibrary(sofile)
except OSError:
    print('could not import cfuncs')
    sys.exit(1)
    
def fill(value, imgptr, width, height):
    cfuncs.fill(value, c_ulonglong(imgptr), c_ulonglong(width*height))

def outline(imgptr, width, height):
    cfuncs.outline(c_ulonglong(imgptr), c_ulong(width), c_ulong(height))

#value = 0xdeadbeef
#array = create_string_buffer(20)
#array_size = 5

#cfuncs.fill(value, array, array_size)
#from binascii import hexlify
#print(hexlify(array.raw))

from PyQt4.QtGui import QApplication, QImage, QPixmap, QLabel
a = QApplication(sys.argv)
myImage = QImage()
myImage.load("puzzles/outtest/pieces/piece15.png")

w, h = myImage.width(), myImage.height()

outline(myImage.bits(), w, h)

myLabel = QLabel()
myLabel.setPixmap(QPixmap.fromImage(myImage.scaled(5*w, 5*h)))
myLabel.show()
a.exec_()