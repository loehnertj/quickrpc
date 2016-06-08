# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'mainwindow.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(800, 600)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(_fromUtf8(":/applications-graphics.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        MainWindow.setWindowIcon(icon)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.centralwidget)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.mainView = MainView(self.centralwidget)
        self.mainView.setObjectName(_fromUtf8("mainView"))
        self.verticalLayout_2.addWidget(self.mainView)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 38))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        self.menu_File = QtGui.QMenu(self.menubar)
        self.menu_File.setObjectName(_fromUtf8("menu_File"))
        self.menu_Insert = QtGui.QMenu(self.menubar)
        self.menu_Insert.setObjectName(_fromUtf8("menu_Insert"))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        MainWindow.setStatusBar(self.statusbar)
        self.toolBar = QtGui.QToolBar(MainWindow)
        self.toolBar.setMovable(False)
        self.toolBar.setObjectName(_fromUtf8("toolBar"))
        MainWindow.addToolBar(QtCore.Qt.TopToolBarArea, self.toolBar)
        self.dock_boxes = QtGui.QDockWidget(MainWindow)
        self.dock_boxes.setEnabled(True)
        self.dock_boxes.setFeatures(QtGui.QDockWidget.AllDockWidgetFeatures)
        self.dock_boxes.setObjectName(_fromUtf8("dock_boxes"))
        self.dockWidgetContents_2 = QtGui.QWidget()
        self.dockWidgetContents_2.setObjectName(_fromUtf8("dockWidgetContents_2"))
        self.verticalLayout = QtGui.QVBoxLayout(self.dockWidgetContents_2)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.dock_boxes.setWidget(self.dockWidgetContents_2)
        MainWindow.addDockWidget(QtCore.Qt.DockWidgetArea(1), self.dock_boxes)
        self.action_Quit = QtGui.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme(_fromUtf8("application-exit"))
        self.action_Quit.setIcon(icon)
        self.action_Quit.setObjectName(_fromUtf8("action_Quit"))
        self.action_view_all = QtGui.QAction(MainWindow)
        self.action_view_all.setObjectName(_fromUtf8("action_view_all"))
        self.actionOpen = QtGui.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme(_fromUtf8("document-open"))
        self.actionOpen.setIcon(icon)
        self.actionOpen.setObjectName(_fromUtf8("actionOpen"))
        self.actionSave = QtGui.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme(_fromUtf8("document-save"))
        self.actionSave.setIcon(icon)
        self.actionSave.setObjectName(_fromUtf8("actionSave"))
        self.actionSave_as = QtGui.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme(_fromUtf8("document-save-as"))
        self.actionSave_as.setIcon(icon)
        self.actionSave_as.setObjectName(_fromUtf8("actionSave_as"))
        self.actionAutosave = QtGui.QAction(MainWindow)
        self.actionAutosave.setCheckable(True)
        self.actionAutosave.setChecked(True)
        self.actionAutosave.setObjectName(_fromUtf8("actionAutosave"))
        self.actionSelRearrange = QtGui.QAction(MainWindow)
        self.actionSelRearrange.setObjectName(_fromUtf8("actionSelRearrange"))
        self.actionReset = QtGui.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme(_fromUtf8("document-revert"))
        self.actionReset.setIcon(icon)
        self.actionReset.setObjectName(_fromUtf8("actionReset"))
        self.actionSelClear = QtGui.QAction(MainWindow)
        self.actionSelClear.setObjectName(_fromUtf8("actionSelClear"))
        self.menu_File.addAction(self.actionOpen)
        self.menu_File.addAction(self.actionAutosave)
        self.menu_File.addAction(self.actionSave)
        self.menu_File.addAction(self.actionSave_as)
        self.menu_File.addSeparator()
        self.menu_File.addAction(self.actionReset)
        self.menu_File.addSeparator()
        self.menu_File.addAction(self.action_Quit)
        self.menu_Insert.addAction(self.actionSelRearrange)
        self.menu_Insert.addAction(self.actionSelClear)
        self.menubar.addAction(self.menu_File.menuAction())
        self.menubar.addAction(self.menu_Insert.menuAction())
        self.toolBar.addAction(self.action_view_all)

        self.retranslateUi(MainWindow)
        QtCore.QObject.connect(self.action_Quit, QtCore.SIGNAL(_fromUtf8("activated()")), MainWindow.close)
        QtCore.QObject.connect(self.action_view_all, QtCore.SIGNAL(_fromUtf8("activated()")), self.mainView.viewAll)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "Puzzle", None))
        self.menu_File.setTitle(_translate("MainWindow", "&Puzzle", None))
        self.menu_Insert.setTitle(_translate("MainWindow", "&Selection", None))
        self.toolBar.setWindowTitle(_translate("MainWindow", "toolBar", None))
        self.dock_boxes.setWindowTitle(_translate("MainWindow", "&Tags", None))
        self.action_Quit.setText(_translate("MainWindow", "&Quit", None))
        self.action_Quit.setShortcut(_translate("MainWindow", "Ctrl+Q", None))
        self.action_view_all.setText(_translate("MainWindow", "View all", None))
        self.actionOpen.setText(_translate("MainWindow", "&Open...", None))
        self.actionOpen.setShortcut(_translate("MainWindow", "Ctrl+O", None))
        self.actionSave.setText(_translate("MainWindow", "&Save", None))
        self.actionSave.setShortcut(_translate("MainWindow", "Ctrl+S", None))
        self.actionSave_as.setText(_translate("MainWindow", "Save &as...", None))
        self.actionAutosave.setText(_translate("MainWindow", "A&utosave", None))
        self.actionSelRearrange.setText(_translate("MainWindow", "&Rearrange", None))
        self.actionSelRearrange.setShortcut(_translate("MainWindow", "Ctrl+R", None))
        self.actionReset.setText(_translate("MainWindow", "&Restart", None))
        self.actionSelClear.setText(_translate("MainWindow", "&Clear", None))
        self.actionSelClear.setShortcut(_translate("MainWindow", "Ctrl+D", None))

from main_view import MainView
import icons_rc
