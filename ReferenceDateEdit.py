
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QMenu
from PyQt5.QtWidgets import QTableWidget
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtWidgets import QComboBox
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QDateEdit
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QGridLayout
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QGroupBox
from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtWidgets import QSpacerItem
from PyQt5.QtWidgets import QItemDelegate
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QDate
from PyQt5.QtCore import Qt
import xml.etree.ElementTree as et
import codecs

class DateDelegate(QItemDelegate):
    def __init__(self):
        super(DateDelegate, self).__init__()

    def createEditor(self, parent, option, proxyModelIndex):
        edit = QDateEdit(parent)
        edit.editingFinished.connect(self.commitAndClose)
        return edit

    def setEditorData(self, editor, index):
        val = index.model().data(index, Qt.EditRole)
        editor.setDate(QDate.fromString(val, editor.displayFormat()))

    def setModelData(self, edit, model, index):
        text = edit.text()
        model.setData(index, text, Qt.EditRole)

    def commitAndClose(self):
        self.commitData.emit(self.sender())
        self.closeEditor.emit(self.sender())

class ReferenceDateEdit(QWidget):

    textChanged = pyqtSignal(str)

    def __init__(self, parent):
        super(ReferenceDateEdit, self).__init__(parent)

        self.m_mainLayout = QVBoxLayout()
        self.m_groupBox = QGroupBox(self)
        self.m_groupLayout = QVBoxLayout(self.m_groupBox)
        self.m_tableWidget = QTableWidget(self.m_groupBox)
        self.m_groupLayout.addWidget(self.m_tableWidget)
        self.m_inputsLayout = QGridLayout()
        self.m_typeLabel = QLabel(self.m_groupBox)
        self.m_inputsLayout.addWidget(self.m_typeLabel, 0, 0, 1, 1)
        self.m_typeCombo = QComboBox(self.m_groupBox)
        sizePolicy = QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.m_typeCombo.sizePolicy().hasHeightForWidth())
        self.m_typeCombo.setSizePolicy(sizePolicy)
        self.m_inputsLayout.addWidget(self.m_typeCombo, 0, 1, 1, 1)
        self.m_dateLabel = QLabel(self.m_groupBox)
        self.m_inputsLayout.addWidget(self.m_dateLabel, 1, 0, 1, 1)
        self.m_dateEdit = QDateEdit(self.m_groupBox)
        self.m_dateEdit.setCalendarPopup(True)
        self.m_inputsLayout.addWidget(self.m_dateEdit, 1, 1, 1, 1)
        self.m_groupLayout.addLayout(self.m_inputsLayout)
        self.m_buttonLayout = QHBoxLayout()
        spacerItem1 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.m_buttonLayout.addItem(spacerItem1)
        self.m_addButton = QPushButton(self.m_groupBox)
        self.m_buttonLayout.addWidget(self.m_addButton)
        self.m_groupLayout.addLayout(self.m_buttonLayout)
        self.m_mainLayout.addWidget(self.m_groupBox)
        spacerItem2 = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.m_mainLayout.addItem(spacerItem2)

        self.m_typeCombo.addItem("creation")
        self.m_typeCombo.addItem("publication")
        self.m_typeCombo.addItem("revision")

        self.m_typeLabel.setText("Type")
        self.m_dateLabel.setText("Date")
        self.m_addButton.setText("Add")
        self.m_groupBox.setTitle("Reference Date")

        self.setLayout(self.m_mainLayout)

        self.m_tableWidget.setColumnCount(3)
        self.m_tableWidget.setHorizontalHeaderLabels(["Type", "Rev", "Date"])
        self.m_tableWidget.horizontalHeader().show()
        self.m_tableWidget.verticalHeader().hide()
        self.m_tableWidget.horizontalHeader().setStretchLastSection(True)
        self.m_tableWidget.setItemDelegateForColumn(2, DateDelegate())

        self.m_addButton.pressed.connect(self.addPressed)

        self.m_tableWidget.model().dataChanged.connect(self.modelDataChanged)
        self.m_tableWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.m_tableWidget.customContextMenuRequested.connect(self.tableWidgetContextMenu)
        self.m_tableWidget.setSelectionBehavior(QTableWidget.SelectRows)

    def tableWidgetContextMenu(self, point):
        globalPos = self.m_tableWidget.mapToGlobal(point)
        menu = QMenu()
        menu.addAction("Delete", self.deteleRevision)
        menu.exec(globalPos)

    def deteleRevision(self):
        sel = self.m_tableWidget.selectionModel().selectedIndexes()
        if len(sel) == 0:
            return
        row = sel[0].row()

        type = self.m_tableWidget.item(row, 0).text()
        rev = self.m_tableWidget.item(row, 1).text()
        date = self.m_tableWidget.item(row, 2).text()

        res = QMessageBox.question(None, 'Delete Revision?',
                                   "Delete revision (%s '%s' %s) ? \n" % (type, rev, date),
                                   QMessageBox.Yes, QMessageBox.No)
        if res == QMessageBox.No:
            return

        self.m_tableWidget.removeRow(row)
        self.textChanged.emit(self.text())

    def modelDataChanged(self):
        self.textChanged.emit(self.text())

    def addPressed(self):
        type = self.m_typeCombo.currentText()
        date = self.m_dateEdit.text()
        dateD = self.m_dateEdit.date()
        if type != "revision":
            for row in range(self.m_tableWidget.rowCount()):
                if self.m_tableWidget.item(row, 0).text() == type:
                    QMessageBox.warning(self, "Warning", "'%s' already in table" % type)
                    return

        pos = 0
        for idx in range(self.m_tableWidget.rowCount()):
            currDate = QDate.fromString(self.m_tableWidget.item(idx, 2).text(), self.m_dateEdit.displayFormat())
            if currDate > dateD:
                break
            pos = idx + 1
        else:
            pos = self.m_tableWidget.rowCount()

        self.m_tableWidget.insertRow(pos)
        self.setRevision(pos, type, str(pos) + ".0", date)
        self.textChanged.emit(self.text())

    def setRevision(self, pos, type, rev, date):
        typeItem  = QTableWidgetItem(type)
        typeItem.setFlags(typeItem.flags() & ~Qt.ItemIsEditable)
        dateItem = QTableWidgetItem(date)
        dateItem.setFlags(dateItem.flags() | Qt.ItemIsEditable)
        revItem = QTableWidgetItem(rev)

        self.m_tableWidget.setItem(pos, 0, typeItem)
        self.m_tableWidget.setItem(pos, 1, revItem)
        self.m_tableWidget.setItem(pos, 2, dateItem)

    def setText(self, text):
        if self.text() == text:
            return

        self.m_tableWidget.setRowCount(0)
        if text == "":
            self.textChanged.emit(self.text())
            return

        root = et.fromstring(text)
        revs = list()
        for child in root:
            type = child.tag
            rev = child.attrib["rev"]
            date = child.attrib["date"]
            revs.append((type, rev, date))

        revs.sort(key = lambda x : QDate.fromString(x[2], self.m_dateEdit.displayFormat()))

        self.m_tableWidget.setRowCount(len(revs))
        for pos in range(len(revs)):
            self.setRevision(pos, *revs[pos])

        self.textChanged.emit(self.text())

    def text(self):
        if self.m_tableWidget.rowCount() == 0:
            return ""

        root = et.Element("revs")
        for row in range(self.m_tableWidget.rowCount()):
            attrs = dict()
            revItem = self.m_tableWidget.item(row, 1)
            if revItem is None:
                return ""
            attrs["rev"] = revItem.text()
            dateItem = self.m_tableWidget.item(row, 2)
            if dateItem is None:
                return ""
            attrs["date"] = dateItem.text()

            typeItem = self.m_tableWidget.item(row, 0)
            if typeItem is None:
                return ""

            elem = et.SubElement(root, typeItem.text(), **attrs)

        xml = codecs.escape_encode(et.tostring(root))[0].decode("utf-8")
        return xml
