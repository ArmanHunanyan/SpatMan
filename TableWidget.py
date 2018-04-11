
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QFrame
from PyQt5.QtWidgets import QMenu
from PyQt5.QtWidgets import QTableView
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QAbstractItemView
from PyQt5.QtWidgets import QToolButton
from PyQt5.QtWidgets import QSpacerItem
from PyQt5.QtWidgets import QSizePolicy

from PyQt5.QtGui import QIcon
from PyQt5.QtGui import QPixmap

from PyQt5.QtCore import Qt

class TableWidget(QWidget):

    def __init__(self, parent):
        super(TableWidget, self).__init__(parent)

        self.m_frame = QFrame(self)
        self.m_frame.setFrameShape(QFrame.Panel)
        self.m_frame.setFrameShadow(QFrame.Plain)

        horizontalLayout = QHBoxLayout(self.m_frame)
        horizontalLayout.setContentsMargins(0, 0, 0, 0)
        horizontalLayout.setSpacing(0)

        self.m_table = QTableView(self.m_frame)
        self.m_table.setStatusTip("")
        self.m_table.setLayoutDirection(Qt.LeftToRight)
        self.m_table.setFrameShape(QFrame.NoFrame)
        self.m_table.setFrameShadow(QFrame.Plain)
        self.m_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        horizontalLayout.addWidget(self.m_table)

        self.m_line = QFrame(self.m_frame)
        self.m_line.setFrameShadow(QFrame.Plain)
        self.m_line.setFrameShape(QFrame.VLine)
        horizontalLayout.addWidget(self.m_line)

        self.m_toolBtnFrame = QFrame(self.m_frame)
        self.m_toolBtnFrame.setLayoutDirection(Qt.RightToLeft)
        self.m_toolBtnFrame.setFrameShape(QFrame.NoFrame)
        self.m_toolBtnFrame.setFrameShadow(QFrame.Plain)

        self.m_verticalLayout = QVBoxLayout(self.m_toolBtnFrame)
        self.m_verticalLayout.setContentsMargins(1, 1, 1, 1)
        self.m_verticalLayout.setSpacing(1)

        self.m_addBtn = QToolButton(self.m_toolBtnFrame)
        icon = QIcon()
        icon.addPixmap(QPixmap(":/icons/plus.png"), QIcon.Normal, QIcon.Off)
        self.m_addBtn.setIcon(icon)
        self.m_addBtn.setAutoRaise(True)
        self.m_addBtn.setArrowType(Qt.NoArrow)
        self.m_verticalLayout.addWidget(self.m_addBtn)

        self.m_deleteBtn = QToolButton(self.m_toolBtnFrame)
        icon1 = QIcon()
        icon1.addPixmap(QPixmap(":/icons/minus.png"), QIcon.Normal, QIcon.Off)
        self.m_deleteBtn.setIcon(icon1)
        self.m_deleteBtn.setAutoRaise(True)
        self.m_verticalLayout.addWidget(self.m_deleteBtn)

        self.m_clearAllBtn = QToolButton(self.m_toolBtnFrame)
        icon1 = QIcon()
        icon1.addPixmap(QPixmap(":/icons/clear.png"), QIcon.Normal, QIcon.Off)
        self.m_clearAllBtn.setIcon(icon1)
        self.m_clearAllBtn.setAutoRaise(True)
        self.m_verticalLayout.addWidget(self.m_clearAllBtn)
        self.m_clearAllBtn.setVisible(False)

        self.m_browseBtn = QToolButton(self.m_toolBtnFrame)
        icon1 = QIcon()
        icon1.addPixmap(QPixmap(":/icons/local.png"), QIcon.Normal, QIcon.Off)
        self.m_browseBtn.setIcon(icon1)
        self.m_browseBtn.setAutoRaise(True)
        self.m_verticalLayout.addWidget(self.m_browseBtn)
        self.m_browseBtn.setVisible(False)

        self.m_editBtn = QToolButton(self.m_toolBtnFrame)
        icon1 = QIcon()
        icon1.addPixmap(QPixmap(":/icons/edit.png"), QIcon.Normal, QIcon.Off)
        self.m_editBtn.setIcon(icon1)
        self.m_editBtn.setAutoRaise(True)
        self.m_verticalLayout.addWidget(self.m_editBtn)
        self.m_editBtn.setVisible(False)

        self.m_pdfBtn = QToolButton(self.m_toolBtnFrame)
        icon1 = QIcon()
        icon1.addPixmap(QPixmap(":/icons/pdf.png"), QIcon.Normal, QIcon.Off)
        self.m_pdfBtn.setIcon(icon1)
        self.m_pdfBtn.setAutoRaise(True)
        self.m_verticalLayout.addWidget(self.m_pdfBtn)
        self.m_pdfBtn.setVisible(False)

        self.m_htmlBtn = QToolButton(self.m_toolBtnFrame)
        icon1 = QIcon()
        icon1.addPixmap(QPixmap(":/icons/html.png"), QIcon.Normal, QIcon.Off)
        self.m_htmlBtn.setIcon(icon1)
        self.m_htmlBtn.setAutoRaise(True)
        self.m_verticalLayout.addWidget(self.m_htmlBtn)
        self.m_htmlBtn.setVisible(False)

        self.m_textBtn = QToolButton(self.m_toolBtnFrame)
        icon1 = QIcon()
        icon1.addPixmap(QPixmap(":/icons/text.png"), QIcon.Normal, QIcon.Off)
        self.m_textBtn.setIcon(icon1)
        self.m_textBtn.setAutoRaise(True)
        self.m_verticalLayout.addWidget(self.m_textBtn)
        self.m_textBtn.setVisible(False)

        spacerItem = QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.m_verticalLayout.addItem(spacerItem)
        horizontalLayout.addWidget(self.m_toolBtnFrame)

        mainLayout = QHBoxLayout()
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.addWidget(self.m_frame)

        self.setLayout(mainLayout)

    def addActionToAddBtn(self, action):
        menu = self.m_addBtn.menu()
        if menu is None:
            self.m_addBtn.setMenu(QMenu())
            self.m_addBtn.setPopupMode(QToolButton.MenuButtonPopup)
            menu = self.m_addBtn.menu()

        menu.addAction(action)

    def showClearAll(self, show):
        self.m_clearAllBtn.setVisible(show)

    def showBrowse(self, show):
        self.m_browseBtn.setVisible(show)

    def showEdit(self, show):
        self.m_editBtn.setVisible(show)

    def showPdfBtn(self, show):
        self.m_pdfBtn.setVisible(show)

    def showHtmlBtn(self, show):
        self.m_htmlBtn.setVisible(show)

    def showTextBtn(self, show):
        self.m_textBtn.setVisible(show)

    def showAddBtn(self, show):
        self.m_addBtn.setVisible(show)

    def showDeleteBtn(self, show):
        self.m_deleteBtn.setVisible(show)

    def showBtns(self, show):
        self.m_toolBtnFrame.setVisible(show)

    def model(self):
        return self.m_table.model()

    def setModel(self, model):
        self.m_table.setModel(model)
        if self.m_table.selectionModel() is not None:
            self.m_table.selectionModel().selectionChanged.connect(self.updateDeleteBtnState)
            self.updateDeleteBtnState()
            self.m_table.selectionModel().selectionChanged.connect(self.updateEditBtnState)
            self.updateEditBtnState()
            self.m_table.selectionModel().selectionChanged.connect(self.updatePdfBtnState)
            self.updatePdfBtnState()
            self.m_table.selectionModel().selectionChanged.connect(self.updateHtmlBtnState)
            self.updateHtmlBtnState()
            self.m_table.selectionModel().selectionChanged.connect(self.updateTextBtnState)
            self.updateTextBtnState()

    def updateDeleteBtnState(self):
        enable = self.m_table.selectionModel().hasSelection()
        self.m_deleteBtn.setEnabled(enable)

    def updateEditBtnState(self):
        enable = self.m_table.selectionModel().hasSelection()
        self.m_editBtn.setEnabled(enable)

    def updateHtmlBtnState(self):
        enable = self.m_table.selectionModel().hasSelection()
        self.m_htmlBtn.setEnabled(enable)

    def updatePdfBtnState(self):
        enable = self.m_table.selectionModel().hasSelection()
        self.m_pdfBtn.setEnabled(enable)

    def updateTextBtnState(self):
        enable = self.m_table.selectionModel().hasSelection()
        self.m_textBtn.setEnabled(enable)

    def addBtn(self):
        return self.m_addBtn

    def deleteBtn(self):
        return self.m_deleteBtn

    def clearAllBtn(self):
        return self.m_clearAllBtn

    def browseBtn(self):
        return self.m_browseBtn

    def editBtn(self):
        return self.m_editBtn

    def pdfBtn(self):
        return self.m_pdfBtn

    def htmlBtn(self):
        return self.m_htmlBtn

    def textBtn(self):
        return self.m_textBtn

    def table(self):
        return self.m_table