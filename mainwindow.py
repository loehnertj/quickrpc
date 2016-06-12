# -*- coding: utf-8 -*-

"""The user interface for our app"""

import os,sys
import logging as L
L.basicConfig(level='DEBUG')


# Import Qt modules
from PyQt4 import QtCore,QtGui
from PyQt4.QtCore import Qt, QSettings # , pyqtSignature
from PyQt4.QtGui import QMainWindow, QFileDialog, QAction, QMessageBox, QGraphicsScene

# Import the compiled UI module
from mainwindowUI import Ui_MainWindow

from i18n import tr

from puzzle_scene import PuzzleScene

from puzzleboard.puzzle_board import PuzzleBoard
from puzzleboard.puzzle_board import as_jsonstring

from slicer.slicer_main import SlicerMain


# Create a class for our main window
class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.container = []

        # This is always the same
        self.ui=Ui_MainWindow()
        self.ui.setupUi(self)
        
        #self.ui.toolBar.addAction(self.ui.dock_boxes.toggleViewAction())
        self.ui.dock_boxes.hide()
        mappings = dict(
            actionSave=self.save,
            actionReset=self.reset_puzzle,
            actionSelRearrange=self.selection_rearrange,
            actionSelClear=self.selection_clear,
            actionNewPuzzle=self.new_puzzle,
            actionOpen=self.open,
        )
        for key,func in mappings.items():
            getattr(self.ui, key).triggered.connect(func)
        
        self.ui.actionAutosave.toggled.connect(self.toggle_autosave)
        self.ui.mainView.setScene(QGraphicsScene())

        self._slicer = None
        
        settings = QSettings()
        path = settings.value("LastOpened", "")
        if path:
            self.load_puzzle(path)
        self.ui.actionAutosave.setChecked(settings.value("Autosave", "true")=="true")
        
    def closeEvent(self, ev):
        self.ui.mainView.gl_widget.setParent(None)
        del self.ui.mainView.gl_widget
        
    def showEvent(self, ev):
        self.ui.mainView.viewAll()
        
    def save(self):
        self.puzzle_board.save_state()
        
    def open(self):
        path = QFileDialog.getOpenFileName(self, "Choose Puzzle", "puzzles", "Puzzle files (puzzle.json)")
        if path: self.load_puzzle(path)
        
    def new_puzzle(self):
        if not self._slicer:
            self._slicer=SlicerMain()
            self._slicer.onFinish = self.load_puzzle
        self._slicer.show()

    def load_puzzle(self, path):
        if path.endswith("puzzle.json"):
            path = os.path.dirname(path)
        self.puzzle_board = PuzzleBoard.from_folder(path)
        self.puzzle_board.on_changed = self.on_pb_changed
        self.scene = PuzzleScene(
            self.ui.mainView,
            self.puzzle_board,
        )
        self.ui.mainView.setScene(self.scene)
        settings = QSettings()
        settings.setValue("LastOpened", path)
    
    def toggle_autosave(self):
        settings = QSettings()
        settings.setValue("Autosave", self.ui.actionAutosave.isChecked())
    
    def reset_puzzle(self):
        if QMessageBox.Ok != QMessageBox.warning(self, "Reset puzzle", "Really reset the puzzle?", QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Cancel):
            return
        self.puzzle_board.reset_puzzle()
        self.scene = PuzzleScene(self.ui.mainView, self.puzzle_board)
        self.ui.mainView.setScene(self.scene)
        self.ui.mainView.viewAll()
        
    def selection_rearrange(self):
        self.scene.selectionRearrange()
        self.ui.mainView.viewAll()
        
    def selection_clear(self):
        self.scene.clearSelection()
        
    def on_pb_changed(self):
        if self.ui.actionAutosave.isChecked():
            L.debug('autosaving')
            self.save()
        if len(self.puzzle_board.clusters) == 1:
            self.on_solved()
        
    def on_solved(self):
        QMessageBox.information(self, "Puzzle solved.", "You did it!", "Yeehaw!!!")
        