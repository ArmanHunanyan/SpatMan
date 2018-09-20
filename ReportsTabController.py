
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QPlainTextEdit
from PyQt5.QtWidgets import QFrame
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QComboBox
from PyQt5.QtWidgets import QGridLayout
from PyQt5.QtWidgets import QLayout
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QSpacerItem
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QCheckBox
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtCore import QAbstractTableModel
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QModelIndex
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QSize

import ReportAPI
from io import StringIO
import sys

import os.path

class ReportItem:
    def __init__(self, name, descr, tp, scr, scriptPath, storeInFile):
        self.name = name
        self.description = descr
        self.type = tp
        self.script = scr
        self.storeInFile = storeInFile
        self.scriptPath = scriptPath

    def displayTuple(self):
        return (self.name, self.description, self.type, self.scriptPath, self.storeInFile)

class ReportsModel(QAbstractTableModel):

    columns = ("Name", "Description", "Type", "Script")
    rowCountChanged = pyqtSignal()

    def __init__(self, schema, database):
        super(ReportsModel, self).__init__()

        self.m_reportList = []
        self.m_schema = schema
        self.m_database = database

        self.loadReports()

    def loadReports(self):
        self.m_reportList = []
        for report in self.m_database.reportList():
            self.m_reportList.append(ReportItem(*report))

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return __class__.columns[section]

    def rowCount(self, parent=None):
        return len(self.m_reportList)

    def columnCount(self, parent=None):
        return len(__class__.columns)

    def insertReport(self, row, report):
        self.rowsAboutToBeInserted.emit(QModelIndex(), row, row)
        self.m_reportList.insert(row, report)
        self.m_database.insertReport(row, report)
        self.rowsInserted.emit(QModelIndex(), row, row)
        self.rowCountChanged.emit()

    def reportItem(self, idx):
        return self.m_reportList[idx]

    def setReport(self, row, report):
        self.m_database.updateReport(row, report)
        self.m_reportList[row] = report
        self.dataChanged.emit(self.createIndex(row, 0),
                              self.createIndex(row, len(__class__.columns) - 1))

    def data(self, index, role):
        if role == Qt.DisplayRole:
            if index.column() == 0:
                return self.m_reportList[index.row()].name
            elif index.column() == 1:
                return self.m_reportList[index.row()].description
            elif index.column() == 2:
                return self.m_reportList[index.row()].type
            elif index.column() == 3:
                if self.m_reportList[index.row()].storeInFile:
                    return self.m_reportList[index.row()].scriptPath
                else:
                    return "<IN DATABASE>"
        return None

    def flags(self, index):
        return super(QAbstractTableModel, self).flags(index)

    def deleteReport(self, row):
        self.rowsAboutToBeRemoved.emit(QModelIndex(), row, row)
        self.m_database.deleteReport(row)
        del self.m_reportList[row]
        self.rowsRemoved.emit(QModelIndex(), row, row)
        self.rowCountChanged.emit()

class ReportSerializer:
    def save(self, reportItem, scriptContent):
        if reportItem.storeInFile:
            with open(reportItem.scriptPath, 'w') as file:
                file.write(scriptContent)
            reportItem.script = ""
        else:
            reportItem.script = scriptContent

    def load(self, reportItem):
        if reportItem.storeInFile:
            with open(reportItem.scriptPath, 'r') as file:
                return file.read()
        else:
            return reportItem.script

class EditReportWidget(QDialog):

    def __init__(self, parent, title, reportSerializer, reportItem):
        super(EditReportWidget, self).__init__(parent)

        self.m_reportSerializer = reportSerializer
        self.m_reportItem = reportItem

        self.setWindowTitle(title)

        self.resize(859, 704)
        self.m_mainLayout = QVBoxLayout(self)
        self.m_scriptEdit = QPlainTextEdit(self)
        self.m_mainLayout.addWidget(self.m_scriptEdit)
        self.m_line1 = QFrame(self)
        self.m_line1.setFrameShape(QFrame.HLine)
        self.m_line1.setFrameShadow(QFrame.Sunken)
        self.m_mainLayout.addWidget(self.m_line1)
        self.m_attriburesWidget = QWidget(self)
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.m_attriburesWidget.sizePolicy().hasHeightForWidth())
        self.m_attriburesWidget.setSizePolicy(sizePolicy)
        self.m_attriburesWidget.setMinimumSize(QSize(0, 100))
        self.verticalLayout = QVBoxLayout(self.m_attriburesWidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.m_attributesLayout = QGridLayout()
        self.m_attributesLayout.setSizeConstraint(QLayout.SetDefaultConstraint)
        self.m_descrPTEdit = QPlainTextEdit(self.m_attriburesWidget)
        self.m_descrPTEdit.setMaximumSize(QSize(16777215, 90))
        self.m_attributesLayout.addWidget(self.m_descrPTEdit, 1, 1, 1, 1)
        self.m_descriptionLabel = QLabel(self.m_attriburesWidget)
        self.m_descriptionLabel.setAlignment(Qt.AlignLeading | Qt.AlignLeft | Qt.AlignTop)
        self.m_attributesLayout.addWidget(self.m_descriptionLabel, 1, 0, 1, 1)
        self.m_typeLabel = QLabel(self.m_attriburesWidget)
        self.m_attributesLayout.addWidget(self.m_typeLabel, 2, 0, 1, 1)
        self.m_nameLabel = QLabel(self.m_attriburesWidget)
        self.m_attributesLayout.addWidget(self.m_nameLabel, 0, 0, 1, 1)
        self.m_nameEdit = QLineEdit(self.m_attriburesWidget)
        self.m_attributesLayout.addWidget(self.m_nameEdit, 0, 1, 1, 1)
        self.m_typeLayout = QHBoxLayout()
        self.m_typeComboBox = QComboBox(self.m_attriburesWidget)
        self.m_typeComboBox.addItem("")
        self.m_typeComboBox.addItem("")
        self.m_typeLayout.addWidget(self.m_typeComboBox)
        spacerItem = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.m_typeLayout.addItem(spacerItem)
        self.m_attributesLayout.addLayout(self.m_typeLayout, 2, 1, 1, 1)
        self.verticalLayout.addLayout(self.m_attributesLayout)
        self.m_saveLayout = QHBoxLayout()
        self.m_saveLayout.setSpacing(0)
        self.m_storeInFileCheckBox = QCheckBox(self.m_attriburesWidget)
        self.m_saveLayout.addWidget(self.m_storeInFileCheckBox)
        self.m_browseLayout = QHBoxLayout()
        self.m_browseLayout.setSpacing(0)
        self.m_filePathEdit = QLineEdit(self.m_attriburesWidget)
        self.m_browseLayout.addWidget(self.m_filePathEdit)
        self.m_filePathBrowseBtn = QPushButton(self.m_attriburesWidget)
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.m_filePathBrowseBtn.sizePolicy().hasHeightForWidth())
        self.m_filePathBrowseBtn.setSizePolicy(sizePolicy)
        self.m_filePathBrowseBtn.setMaximumSize(QSize(25, 16777215))
        self.m_browseLayout.addWidget(self.m_filePathBrowseBtn)
        self.m_saveLayout.addLayout(self.m_browseLayout)
        self.verticalLayout.addLayout(self.m_saveLayout)
        self.m_mainLayout.addWidget(self.m_attriburesWidget)
        self.m_line2 = QFrame(self)
        self.m_line2.setFrameShape(QFrame.HLine)
        self.m_line2.setFrameShadow(QFrame.Sunken)
        self.m_mainLayout.addWidget(self.m_line2)
        self.m_buttonsLayout = QHBoxLayout()
        spacerItem1 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.m_buttonsLayout.addItem(spacerItem1)
        self.m_saveBtn = QPushButton(self)
        self.m_buttonsLayout.addWidget(self.m_saveBtn)
        self.m_saveAndCloseBtn = QPushButton(self)
        self.m_buttonsLayout.addWidget(self.m_saveAndCloseBtn)
        self.m_cancelBtn = QPushButton(self)
        self.m_buttonsLayout.addWidget(self.m_cancelBtn)
        self.m_mainLayout.addLayout(self.m_buttonsLayout)

        self.m_descriptionLabel.setText("Description:")
        self.m_typeLabel.setText("Type:")
        self.m_nameLabel.setText("Name:")
        self.m_typeComboBox.setItemText(0, "SQL")
        self.m_typeComboBox.setItemText(1, "Python")
        self.m_storeInFileCheckBox.setText("Store In File")
        self.m_filePathBrowseBtn.setText("...")
        self.m_saveBtn.setText("Save")
        self.m_saveAndCloseBtn.setText("Save And Close")
        self.m_cancelBtn.setText("Cancel")

        self.m_filePathBrowseBtn.pressed.connect(self.browse)
        self.m_storeInFileCheckBox.toggled.connect(self.storeCheckboxToggled)

        self.storeCheckboxToggled()

        self.m_saveBtn.pressed.connect(self.save)
        self.m_saveAndCloseBtn.pressed.connect(self.saveAndAccept)
        self.m_cancelBtn.pressed.connect(self.close)

        if self.m_reportItem is not None:
            self.m_nameEdit.setText(self.m_reportItem.name)
            self.m_descrPTEdit.setPlainText(self.m_reportItem.description)
            self.m_typeComboBox.setCurrentText(self.m_reportItem.type)
            self.m_filePathEdit.setText(self.m_reportItem.scriptPath)
            self.m_storeInFileCheckBox.setChecked(self.m_reportItem.storeInFile)
            self.m_scriptEdit.setPlainText(self.m_reportSerializer.load(self.m_reportItem))

    def save(self):
        try:
            self.m_reportItem = ReportItem(self.m_nameEdit.text(), self.m_descrPTEdit.toPlainText(), self.m_typeComboBox.currentText(),
                              "", self.m_filePathEdit.text(), self.m_storeInFileCheckBox.isChecked())
            self.m_reportSerializer.save(self.selectedReport(), self.m_scriptEdit.toPlainText())
        except Exception as e:
            QMessageBox.warning(self, "Error", "Failed to save script\n\t%s" % e)
            return False
        return True

    def saveAndAccept(self):
        if self.save():
            self.accept()

    def close(self):
        if QMessageBox.question(self, "Close Window?", "All changes will be lost. Do you want to close widget?", QMessageBox.Yes, QMessageBox.No) == QMessageBox.Yes:
            self.reject()

    def browse(self):
        if self.m_filePathEdit.text() != "":
            startDir = os.path.dirname(self.m_filePathEdit.text())
        else:
            startDir = "" #self.m_startDir
        path = QFileDialog.getSaveFileName(None, "File path", startDir)[0]
        if len(path) != 0:
            self.m_filePathEdit.setText(path)


    def storeCheckboxToggled(self):
        if self.m_storeInFileCheckBox.isChecked():
            self.m_filePathEdit.setEnabled(True)
            self.m_filePathBrowseBtn.setEnabled(True)
        else:
            self.m_filePathEdit.setDisabled(True)
            self.m_filePathBrowseBtn.setDisabled(True)

    def selectedReport(self):
        return self.m_reportItem

class ViewRunResultWidget(QDialog):

    def __init__(self, parent, result, output):
        super(ViewRunResultWidget, self).__init__(parent)

        self.setWindowTitle("Result")

        self.resize(859, 704)
        self.m_mainLayout = QVBoxLayout(self)
        self.m_resultEdit = QPlainTextEdit(self)
        self.m_resultEdit.setReadOnly(True)
        self.m_resultEdit.setPlainText((result))
        self.m_mainLayout.addWidget(self.m_resultEdit)

        self.m_outputEdit = QPlainTextEdit(self)
        self.m_outputEdit.setReadOnly(True)
        self.m_outputEdit.setPlainText(output)
        self.m_mainLayout.addWidget(self.m_outputEdit)

        self.m_buttonsLayout = QHBoxLayout()
        spacerItem1 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.m_buttonsLayout.addItem(spacerItem1)
        self.m_saveBtn = QPushButton(self)
        self.m_buttonsLayout.addWidget(self.m_saveBtn)
        self.m_cancelBtn = QPushButton(self)
        self.m_buttonsLayout.addWidget(self.m_cancelBtn)
        self.m_mainLayout.addLayout(self.m_buttonsLayout)

        self.m_saveBtn.setText("Save")
        self.m_cancelBtn.setText("Cancel")

        self.m_saveBtn.pressed.connect(self.saveAndAccept)
        self.m_cancelBtn.pressed.connect(self.reject)

    def saveAndAccept(self):
        try:
            filePath = QFileDialog.getSaveFileName(self, "File path to save")
            file = open(filePath[0], "w")
            file.write(self.m_resultEdit.toPlainText())
            file.close()
        except Exception as e:
            QMessageBox.warning(self, "Error", "Failed to save result\n\t%s" % e)
            return
        self.accept()

class ReportsTabController(QObject):
    def __init__(self, ui, database, schema, connId, host, port, dbName, user, password):
        super(ReportsTabController, self).__init__()
        self.ui = ui
        self.m_database = database
        self.m_schema = schema
        self.m_connId = connId
        self.m_currentSchemaHost = host
        self.m_currentSchemaPort = port
        self.m_currentSchemaDBName = dbName
        self.m_currentSchemaUserName = user
        self.m_currentSchemaPassword = password

        self.m_model = ReportsModel(self.m_schema, self.m_database.localDatabase())
        self.ui.reportsReportsTable.setModel(self.m_model)
        self.ui.reportsReportsTable.table().horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)

        self.ui.reportsReportsTable.showEdit(True)

        self.ui.reportsReportsTable.addBtn().pressed.connect(self.addReportPressed)
        self.ui.reportsReportsTable.editBtn().pressed.connect(self.editReportPressed)
        self.ui.reportsReportsTable.deleteBtn().pressed.connect(self.deleteReportPressed)

        self.ui.reportsRunSelectedBtn.pressed.connect(self.runSelected)
        self.ui.reportsReportsTable.table().selectionModel().selectionChanged.connect(self.updateRunButtonState)
        self.updateRunButtonState()

    def updateRunButtonState(self):
        selecteds = self.ui.reportsReportsTable.table().selectionModel().selectedIndexes()
        self.ui.reportsRunSelectedBtn.setEnabled(len(selecteds) != 0)

    def runSelected(self):
        selecteds = self.ui.reportsReportsTable.table().selectionModel().selectedIndexes()
        if len(selecteds) == 0:
            return

        idx = selecteds[-1].row()
        serializer = ReportSerializer()
        report = self.m_model.reportItem(idx)
        script = serializer.load(report)
        try:
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            fake_stdout = StringIO()
            sys.stdout = fake_stdout
            sys.stderr = fake_stdout

            ReportAPI.xml = ""
            exec(script)
        except Exception as e:
            QMessageBox.warning(self.ui.reportsReportsTable, "Error", "Failed to execute script\n\t%s" % e)
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        viewRes = ViewRunResultWidget(self.ui.reportsReportsTable, ReportAPI.xml, fake_stdout.getvalue())
        fake_stdout.close()

        viewRes.exec()

    def newRowIndex(self):
        selecteds = self.ui.reportsReportsTable.table().selectionModel().selectedIndexes()
        if len(selecteds) != 0:
            idx = selecteds[-1].row() + 1
        else:
            idx = self.ui.reportsReportsTable.model().rowCount()

        return idx

    def addReportPressed(self):
        serializer = ReportSerializer()
        dlg = EditReportWidget(self.ui.exchangeValidateInputTable, "New Script", serializer, None)
        res = dlg.exec()
        if res == QDialog.Rejected:
            return
        idx = self.newRowIndex()
        report = dlg.selectedReport()
        self.m_model.insertReport(idx, report)

    def editReportPressed(self):
        saver = ReportSerializer()
        selecteds = self.ui.reportsReportsTable.table().selectionModel().selectedIndexes()
        if len(selecteds) == 0:
            return
        idx = selecteds[-1].row()
        serializer = ReportSerializer()
        dlg = EditReportWidget(None, "Edit Script", serializer, self.m_model.reportItem(idx))
        res = dlg.exec()
        if res == QDialog.Rejected:
            return
        report = dlg.selectedReport()
        self.m_model.setReport(idx, report)

    def deleteReportPressed(self):
        res = QMessageBox.question(None, 'Delete report?',
                                   "Do you want to delete this report? \n"
                                   "All related information will be removed from database",
                                   QMessageBox.Yes, QMessageBox.No)
        if res == QMessageBox.No:
            return
        selecteds = self.ui.reportsReportsTable.table().selectionModel().selectedIndexes()
        if len(selecteds) == 0:
            return
        idx = selecteds[-1].row()
        self.m_model.deleteReport(idx)