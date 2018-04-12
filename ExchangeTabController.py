
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QComboBox
from PyQt5.QtWidgets import QGridLayout
from PyQt5.QtWidgets import QSpacerItem
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QAbstractItemView
from TableListWithFiltersController import TableListWithFiltersController
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtCore import QAbstractTableModel
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QModelIndex
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtCore import QDateTime
import tempfile
import uuid
import shutil
import xml.etree.ElementTree as et
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebEngineWidgets import QWebEngineSettings
from PyQt5.QtCore import QUrl
from PyQt5.QtCore import QTimer
import bs4

from Configuration import Configuration
from GeoJSONParser import parseGeoJSON, GeoJSONVisitor

import os.path
import subprocess

def parseGML(gxml):
    gxml = str(gxml)
    gxml = "<root xmlns:gml = \"gml\" >" + gxml + "</root>"
    try:
        root = et.fromstring(gxml)
    except Exception as e:
        print("Wrong GML %s: %s" % (str(e), gxml))
        return None

    id = root.findall("./{gml}GeographicCRS/{gml}srsID/{gml}name")
    if len(id) == 0:
        return None

    return id[0].text

class Ogr2OgrFormats:
    def __init__(self, formats):
        self.m_formats = formats

    def formatNames(self):
        return [fmt[0] for fmt in self.m_formats]

    def extension(self, fmtName):
        for fmt in self.m_formats:
            if fmt[0] == fmtName:
                return fmt[2]
        return None

    def ogrFormatName(self, fmtName):
        for fmt in self.m_formats:
            if fmt[0] == fmtName:
                return fmt[1]
        return None

class ExchangeTabExportsController(QObject):
    def __init__(self, ui, database, schema, connId, host, port, dbName, user, password):
        super(ExchangeTabExportsController, self).__init__()
        self.ui = ui
        self.m_database = database
        self.m_schema = schema
        self.m_connId = connId
        self.m_currentSchemaHost = host
        self.m_currentSchemaPort = port
        self.m_currentSchemaDBName = dbName
        self.m_currentSchemaUserName = user
        self.m_currentSchemaPassword = password

        config = Configuration()
        self.m_ogr2ogrExec = os.path.join(config.ogr2ogrDir(), "ogr2ogr.exe")
        self.m_ogr2ogrFormats = Ogr2OgrFormats(config.ogr2ogrFormats())

        self.ui.exchangeExportCombo.clear()
        self.ui.exchangeExportCombo.addItems(self.m_ogr2ogrFormats.formatNames())

        self.ui.exchangeExportList.setSelectionMode(QAbstractItemView.SingleSelection)

        self.m_tableListWithFilterController = TableListWithFiltersController(self.m_database, self.m_schema, self.m_connId,
                        self.ui.exchangeExportList, self.ui.exchangeExportFilterEdit, self.ui.exchangeExportfilterBtn,
                                        lambda idx: False,
                                        lambda db, schema, connId : db.localDatabase().localTableList(connId, False))
        self.m_tableListWithFilterController.selectTableNameSignal.connect(self.tableSelected)
        self.m_tableListWithFilterController.deselectTableNameSignal.connect(self.tableDeselected)

        self.ui.exchangeExportList.selectionModel().selectionChanged.connect(self.updateExportButtonState)
        self.ui.exchangeExportDir.textChanged.connect(self.updateExportButtonState)
        self.updateExportButtonState()

        self.ui.exchangeExportList.selectionModel().selectionChanged.connect(self.updateFileName)
        self.ui.exchangeExportCombo.currentTextChanged.connect(self.updateFileName)
        self.updateFileName()

        self.ui.exchangeExportList.selectionModel().selectionChanged.connect(self.updateExportCmd)
        self.ui.exchangeExportDir.textChanged.connect(self.updateExportCmd)
        self.ui.exchangeExportSwitches.textChanged.connect(self.updateExportCmd)
        self.ui.exchangeExportFile.textChanged.connect(self.updateExportCmd)
        self.ui.exchangeExportSwitches.textChanged.connect(self.updateExportCmd)
        self.updateExportCmd()

        self.ui.exchangeExportGoButton.pressed.connect(self.doExport)

        self.ui.exchangeExportDirBrowseBtn.pressed.connect(self.browseOutputDir)

        self.ui.exchangeExportDir.setText(config.lastExportDir())

    def browseOutputDir(self):
        path = QFileDialog.getExistingDirectory(None, "Export to directory")
        if path != "":
            self.ui.exchangeExportDir.setText(path)

    def tableSelected(self, row, tableName):
        pass

    def tableDeselected(self, row, tableName):
        pass

    def updateExportButtonState(self):
        sel = self.ui.exchangeExportList.selectionModel().selectedIndexes()
        if len(sel) != 1:
            self.ui.exchangeExportGoButton.setDisabled(True)
            return

        if self.ui.exchangeExportDir.text() == "":
            self.ui.exchangeExportGoButton.setDisabled(True)
            return

        self.ui.exchangeExportGoButton.setDisabled(False)

    def updateFileName(self):
        sel = self.ui.exchangeExportList.selectionModel().selectedIndexes()
        if len(sel) != 1:
            self.ui.exchangeExportFile.setText("")
            return

        idx = sel[0].row()
        self.ui.exchangeExportFile.setText(self.ui.exchangeExportList.item(idx).text()
                                           + "." + self.currentFormatExtension())

    def currentFormatExtension(self):
        fmtName = self.ui.exchangeExportCombo.currentText()
        return self.m_ogr2ogrFormats.extension(fmtName)

    def currentFormatOgrName(self):
        fmtName = self.ui.exchangeExportCombo.currentText()
        return self.m_ogr2ogrFormats.ogrFormatName(fmtName)

    def updateExportCmd(self):
        sel = self.ui.exchangeExportList.selectionModel().selectedIndexes()
        if len(sel) != 1:
            self.ui.exchangeExportCmdEdit.setPlainText("")
            return

        if self.ui.exchangeExportDir.text() == "":
            self.ui.exchangeExportCmdEdit.setPlainText("")
            return

        idx = sel[0].row()
        formatName = self.currentFormatOgrName()
        self.m_currentTableName = "%s.%s" % (self.m_schema, self.ui.exchangeExportList.item(idx).text())
        self.m_currentFileName = os.path.join(self.ui.exchangeExportDir.text(), self.ui.exchangeExportFile.text())
        self.m_exportCmd = "-f \"%s\" \"%s\" PG:\"dbname='%s' host='%s' port='%s' user='%s' password='%s'\" -sql \"select * from %s\" %s" \
                        % (formatName, self.m_currentFileName, self.m_currentSchemaDBName, self.m_currentSchemaHost, self.m_currentSchemaPort, \
                                self.m_currentSchemaUserName, self.m_currentSchemaPassword, self.m_currentTableName,
                               self.ui.exchangeExportSwitches.text())
        self.ui.exchangeExportCmdEdit.setPlainText("ogr2ogr " + self.m_exportCmd)

    def doExport(self):
        command = self.m_ogr2ogrExec + " " + self.m_exportCmd
        print("Running command '%s'" % command)
        config = Configuration()
        config.setLastExportDir(self.ui.exchangeExportDir.text())
        try:
            subprocess.check_output(command, stderr=subprocess.STDOUT)
            QMessageBox.information(None, "Success",
                            "Table %s was successfully converted into '%s' as '%s'" % \
                                (self.m_currentTableName, self.m_currentFileName, self.currentFormatOgrName()))
        except OSError as e:
            QMessageBox.warning(None, "Error", "Failed to execute org2org:\n\t%s" % e)
        except subprocess.CalledProcessError as e:
            QMessageBox.warning(None, "Error", "Failed to execute %s:\n\t%s" % ("ogr2ogr", e.output.decode("utf-8")))

class ValidationItem:
    def __init__(self, fileName, tableName):
        self.fileName = fileName
        self.tableName = tableName

class ValidateFilesModel(QAbstractTableModel):

    columns = ("Name", "Table", "Path")
    rowCountChanged = pyqtSignal()

    def __init__(self, schema):
        super(ValidateFilesModel, self).__init__()

        self.m_fileList = []
        self.m_schema = schema

    def items(self):
        for file, table in self.m_fileList:
            yield  ValidationItem(file, table)

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return __class__.columns[section]

    def rowCount(self, parent=None):
        return len(self.m_fileList)

    def columnCount(self, parent=None):
        return len(__class__.columns)

    def insertFile(self, row, file, rules):
        self.rowsAboutToBeInserted.emit(QModelIndex(), row, row)
        self.m_fileList.insert(row, (file, rules))
        self.rowsInserted.emit(QModelIndex(), row, row)
        self.rowCountChanged.emit()

    def setFile(self, row, file, rules):
        self.m_fileList[row] = (file, rules)
        self.dataChanged.emit(self.createIndex(row, 0),
                              self.createIndex(row, len(__class__.columns) - 1))

    def filePath(self, row):
        return self.m_fileList[row][0]

    def rule(self, row):
        return self.m_fileList[row][1]

    def data(self, index, role):
        if role == Qt.DisplayRole:
            if index.column() == 0:
                return os.path.basename(self.m_fileList[index.row()][0])
            elif index.column() == 2:
                return self.m_fileList[index.row()][0]
            else:
                return self.m_schema + "." + str(self.m_fileList[index.row()][1])
        return None

    def flags(self, index):
        return super(QAbstractTableModel, self).flags(index)

    def deleteFile(self, row):
        self.rowsAboutToBeRemoved.emit(QModelIndex(), row, row)
        del self.m_fileList[row]
        self.rowsRemoved.emit(QModelIndex(), row, row)
        self.rowCountChanged.emit()

class ValidateResultsModel(QAbstractTableModel):

    columns = ("Name", "Table", "Path", "Status")
    rowCountChanged = pyqtSignal()

    def __init__(self, schema):
        super(ValidateResultsModel, self).__init__()

        self.m_resultsList = []
        self.m_schema = schema

    def report(self, idx):
        return self.m_resultsList[idx]

    def clear(self):
        self.modelAboutToBeReset.emit()
        del self.m_resultsList[:]
        self.modelReset.emit()

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return __class__.columns[section]

    def rowCount(self, parent=None):
        return len(self.m_resultsList)

    def columnCount(self, parent=None):
        return len(__class__.columns)

    def appendResult(self, report):
        row = self.rowCount()
        self.rowsAboutToBeInserted.emit(QModelIndex(), row, row)
        self.m_resultsList.append(report)
        self.rowsInserted.emit(QModelIndex(), row, row)
        self.rowCountChanged.emit()

    def data(self, index, role):
        if role == Qt.DisplayRole:
            if index.column() == 0:
                return os.path.basename(self.m_resultsList[index.row()].file())
            elif index.column() == 1:
                return self.m_schema + "." + self.m_resultsList[index.row()].table()
            elif index.column() == 2:
                return self.m_resultsList[index.row()].file()
            elif index.column() == 3:
                return "Passed" if self.m_resultsList[index.row()].passed() else "Failed"
        return None

    def flags(self, index):
        return super(QAbstractTableModel, self).flags(index)

class EditFileTaskWidget(QDialog):

    def __init__(self, parent, startDir, fileName, tableName, database, connId):
        super(EditFileTaskWidget, self).__init__(parent)

        self.m_database = database
        self.m_connId = connId

        self.m_fileEdit = QLineEdit(fileName)
        self.m_fileButton = QPushButton("...")
        self.m_fileButton.setFixedWidth(30)
        self.m_fileButton.pressed.connect(self.browse)
        self.m_startDir = startDir

        fileLayout = QHBoxLayout()
        fileLayout.setContentsMargins(0, 0, 0, 0)
        fileLayout.setSpacing(6)
        fileLayout.addWidget(self.m_fileEdit)
        fileLayout.addWidget(self.m_fileButton)

        self.m_tablesCombo = QComboBox()

        topLayout = QGridLayout()
        topLayout.setHorizontalSpacing(6)
        topLayout.setVerticalSpacing(6)
        topLayout.addWidget(QLabel("File name:"), 0, 0)
        topLayout.addItem(fileLayout, 0, 1)
        topLayout.addWidget(QLabel("Tables:"), 1, 0)
        topLayout.addWidget(self.m_tablesCombo, 1, 1)

        self.m_okButton = QPushButton("OK")
        self.m_cancelButton = QPushButton("Cancel")
        self.m_okButton.setDefault(True)
        btnLayout = QHBoxLayout()
        btnLayout.addItem(QSpacerItem(5, 1, QSizePolicy.Expanding, QSizePolicy.Minimum))
        btnLayout.addWidget(self.m_cancelButton)
        btnLayout.addWidget(self.m_okButton)

        mainLayout = QVBoxLayout()
        mainLayout.addItem(topLayout)
        mainLayout.addItem(QSpacerItem(1, 5, QSizePolicy.Minimum, QSizePolicy.Expanding))
        mainLayout.addItem(btnLayout)
        self.setLayout(mainLayout)

        self.m_okButton.pressed.connect(self.accept)
        self.m_cancelButton.pressed.connect(self.reject)

        self.resize(400, 150)
        self.setWindowTitle("Edit file task")

        self.m_tablesCombo.addItems(self.m_database.localDatabase().localTableList(self.m_connId, False))
        self.m_tablesCombo.setCurrentText(tableName)

    def browse(self):
        if self.m_fileEdit.text() != "":
            startDir = os.path.dirname(self.m_fileEdit.text().split(";")[0])
        else:
            startDir = self.m_startDir
        path = QFileDialog.getOpenFileNames(None, "File paths", startDir)[0]
        if len(path) != 0:
            self.m_fileEdit.setText(";".join(path))


    def selectedFile(self):
        return self.m_fileEdit.text()

    def selectedRule(self):
        return self.m_tablesCombo.currentText()

class ExchangeTabValidateController(QObject):
    def __init__(self, ui, database, schema, connId, host, port, dbName, user, password):
        super(ExchangeTabValidateController, self).__init__()
        self.ui = ui
        self.m_database = database
        self.m_schema = schema
        self.m_connId = connId
        self.m_currentSchemaHost = host
        self.m_currentSchemaPort = port
        self.m_currentSchemaDBName = dbName
        self.m_currentSchemaUserName = user
        self.m_currentSchemaPassword = password

        self.m_model = ValidateFilesModel(self.m_schema)
        self.ui.exchangeValidateInputTable.setModel(self.m_model)
        self.ui.exchangeValidateInputTable.table().horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

        self.ui.exchangeValidateInputTable.showEdit(True)

        self.ui.exchangeValidateInputTable.addBtn().pressed.connect(self.addFilePressed)
        self.ui.exchangeValidateInputTable.editBtn().pressed.connect(self.editFilePressed)
        self.ui.exchangeValidateInputTable.deleteBtn().pressed.connect(self.deleteFilePressed)

        self.ui.exchangeValidateGoButton.pressed.connect(self.doValidate)
        self.ui.exchangeValidateInputTable.model().rowCountChanged.connect(self.updateValidateButtonState)
        self.updateValidateButtonState()

        self.ui.exchangeValidateResultTable.showAddBtn(False)
        self.ui.exchangeValidateResultTable.showDeleteBtn(False)
        self.ui.exchangeValidateResultTable.showPdfBtn(True)
        self.ui.exchangeValidateResultTable.showHtmlBtn(True)
        self.ui.exchangeValidateResultTable.showTextBtn(True)

        self.m_resModel = ValidateResultsModel(self.m_schema)
        self.ui.exchangeValidateResultTable.setModel(self.m_resModel)
        self.ui.exchangeValidateResultTable.table().horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

        self.ui.exchangeValidateResultTable.textBtn().pressed.connect(self.generateTextReport)
        self.ui.exchangeValidateResultTable.pdfBtn().pressed.connect(self.generatePdfReport)
        self.ui.exchangeValidateResultTable.htmlBtn().pressed.connect(self.generateHtmlReport)

        config = Configuration()
        self.m_ogr2ogrExec = os.path.join(config.ogr2ogrDir(), "ogr2ogr.exe")
        self.m_gdalsrsinfoExec = os.path.join(config.ogr2ogrDir(), "gdalsrsinfo.exe")
        self.m_gdalData = os.path.join(config.ogr2ogrDir(), "..", "share", "epsg_csv")

        self.m_pdfConverters = list()

    class ReportGenerator:
        def __init__(self):
            pass

        def openFile(self, path):
            pass

        def writeSuccessHeader(self, header):
            pass

        def writeSuccessInfo(self, table, file, dbName, currTime):
            pass

        def writeFailedHeader(self, header):
            pass

        def writeFailedInfo(self, table, file, dbName, currTime):
            pass

        def writeSRIDMismatch(self, expectedSRID, actualSRID):
            pass

        def writeErrorField(self, report):
            pass

        def finalize(self):
            pass

    class ReportTextGenerator:
        def __init__(self):
            pass

        def genSuccessHeader(self, header):
            return header

        def genFailedHeader(self, header):
            return header

        def genSuccessInfo(self, table, file, dbName, currTime):
            res = dict()
            res["File Name"] = file
            res["Database Name"] = dbName
            res["Table Name"] = table
            res["Date Generated"] = currTime.toString("dd MMMM yyy hh:mm ap")
            return res

        def genFailedInfo(self, table, file, dbName, currTime):
            return self.genSuccessInfo(table, file, dbName, currTime)

        def genSRIDMismatch(self, expectedSRID, actualSRID):
            res = ""
            if actualSRID is not None:
                res = "SRID Mismatch: Expected %s but got %s" % (str(expectedSRID), str(actualSRID))
            else:
                res = "Missing SRID: Expected %s" % str(expectedSRID)
            return res

        def genErrorField(self, report):
            properties = report.properties()

            errors = dict()
            typeMismatch = report.typeMismatch()
            if typeMismatch is not None:
                errors["Type Mismatch"] = "Expected %s but got %s" % (typeMismatch[0], typeMismatch[1])

            extentViolation = report.extentViolation()
            if extentViolation is not None:
                northLat, southLat, westLong, eastLong, violatedCoords = extentViolation
                msg = "Following coordinates are out of extents" \
                      "NorthLat = %s, SouthLat = %s, WestLong = %s, EastLong = %s" % (northLat, southLat, westLong, eastLong)
                msg += "\t" + "\t".join(("(%s, %s)\n" % (coord[0], coord[1]) for coord in violatedCoords))
                errors["Extent Violation"] = msg

            missingFields = report.missingFields()
            extraFields = report.extraFields()
            nullFields = report.nullFields()
            rangeViolations = report.rangeViolations()

            if len(missingFields) != 0:
                errors["Missing fields"] = ",".join(("'%s'" % field for field in missingFields))

            if len(extraFields) != 0:
                errors["Extra fields"] = ",".join(("'%s'" % field for field in extraFields))

            if len(nullFields) != 0:
                errors["Null fields"] = ",".join(("'%s'" % field for field in nullFields))

            if len(rangeViolations) != 0:
                errors["Range Violations"] = ",".join(("('%s' min = %s, max = %s, val = %s)" % (field[0], field[1], field[2], field[3]) for field in rangeViolations))

            return (properties, errors)

    class TextGenerator(ReportGenerator):
        def __init__(self):
            self.m_file = None
            self.m_textGenerator = ExchangeTabValidateController.ReportTextGenerator()

        def openFile(self, path):
            self.m_file = open(path, "w")

        def writeSuccessHeader(self, header):
            self.m_file.write(self.m_textGenerator.genSuccessHeader(header) + "\n")

        def _makePropertyTable(self, propDict, prefix):
            msg = ""
            maxLen = max((len(key) for key in propDict.keys()))
            maxLen += 3
            for name, value in propDict.items():
                line = prefix + "%s:%s\n" % (name, (' ' * (maxLen - len(name))) + str(value))
                msg += line
            return msg

        def writeSuccessInfo(self, table, file, dbName, currTime):
            msg = self._makePropertyTable(self.m_textGenerator.genSuccessInfo(table, file, dbName, currTime), "")
            self.m_file.write(msg)

        def writeFailedHeader(self, header):
            self.m_file.write(self.m_textGenerator.genFailedHeader(header) + "\n")

        def writeFailedInfo(self, table, file, dbName, currTime):
            msg = self._makePropertyTable(self.m_textGenerator.genFailedInfo(table, file, dbName, currTime), "")
            self.m_file.write(msg)
            self.m_file.write("---------------------------------------------------------------------------------\n")

        def writeSRIDMismatch(self, expectedSRID, actualSRID):
            self.m_file.write("---------------------------------------------------------------------------------\n")
            self.m_file.write(self.m_textGenerator.genSRIDMismatch(expectedSRID, actualSRID) + "\n")

        def writeErrorField(self, report):
            self.m_file.write("---------------------------------------------------------------------------------\n")
            self.m_file.write("Feauture :\n")
            props, errors = self.m_textGenerator.genErrorField(report)
            msg = self._makePropertyTable(props, "\t")
            self.m_file.write(msg)
            msg = self._makePropertyTable(errors, "")
            self.m_file.write(msg)

        def finalize(self):
            self.m_file.close()
            return True

    class PdfGenerator(ReportGenerator):
        def __init__(self, dir, pdfConverter):
            self.m_htmlDir = dir
            self.m_htmlGenerator = ExchangeTabValidateController.HtmlGenerator()
            self.m_pdfConverter = pdfConverter

        def openFile(self, path):
            self.m_pdfPath = path
            self.m_htmlGenerator.openFile(self.m_htmlDir)

        def writeSuccessHeader(self, header):
            self.m_htmlGenerator.writeSuccessHeader(header)

        def writeSuccessInfo(self, table, file, dbName, currTime):
            self.m_htmlGenerator.writeSuccessInfo(table, file, dbName, currTime)

        def writeFailedHeader(self, header):
            self.m_htmlGenerator.writeFailedHeader(header)

        def writeFailedInfo(self, table, file, dbName, currTime):
            self.m_htmlGenerator.writeFailedInfo(table, file, dbName, currTime)

        def writeSRIDMismatch(self, expectedSRID, actualSRID):
            self.m_htmlGenerator.writeSRIDMismatch(expectedSRID, actualSRID)

        def writeErrorField(self, report):
            self.m_htmlGenerator.writeErrorField(report)

        def finalize(self):
            self.m_htmlGenerator.finalize()
            self.m_pdfConverter.startConversion(os.path.join(self.m_htmlDir, "report.html"), self.m_pdfPath)

    class HtmlGenerator(ReportGenerator):
        def __init__(self):
            self.m_textGenerator = ExchangeTabValidateController.ReportTextGenerator()

        def openFile(self, path):
            self.m_dir = path

            config = Configuration()
            self.m_reportTemplate = config.reportTemplateDir()

            try:
                shutil.rmtree(path)
            except:
                pass

            shutil.copytree(self.m_reportTemplate, path, symlinks=False, ignore=None)

            with open(os.path.join(self.m_dir, "report.html")) as reportFile:
                reportContent = reportFile.read()
                self.m_soup = bs4.BeautifulSoup(reportContent, "lxml")

            self.m_mainDiv = self.m_soup.find("div", {"id": "integreport"})
            self.m_mainDiv.append(self.m_soup.new_tag("br"))

        def writeSuccessHeader(self, header):
            headerDiv = self.m_soup.new_tag("div")
            headerText = self.m_soup.new_tag("h1")
            headerText.string = self.m_textGenerator.genSuccessHeader(header)
            headerDiv.append(headerText)
            self.m_mainDiv.append(headerDiv)

        def _makePropertyTable(self, propDict, border = 0, colWidth = None):
            tableTag = self.m_soup.new_tag("table", align="left", border=str(border), cellspacing="0", cellpadding="0", width="100%")
            if colWidth is not None:
                colTag = self.m_soup.new_tag("col", width=str(colWidth))
                tableTag.append(colTag)

            for name, value in propDict.items():
                rowTag = self.m_soup.new_tag("tr", align="left", valign="top")
                cellNameTag = self.m_soup.new_tag("td")
                cellNameTag.string = name
                cellValueTag = self.m_soup.new_tag("td")
                cellValueTag.string = str(value)
                rowTag.append(cellNameTag)
                rowTag.append(cellValueTag)
                tableTag.append(rowTag)

            return tableTag

        def writeSuccessInfo(self, table, file, dbName, currTime):
            infoDiv = self.m_soup.new_tag("p")
            infoDiv.append(self._makePropertyTable(self.m_textGenerator.genSuccessInfo(table, file, dbName, currTime)))
            self.m_mainDiv.append(infoDiv)

        def writeFailedHeader(self, header):
            headerDiv = self.m_soup.new_tag("p")
            headerText = self.m_soup.new_tag("h1")
            headerText.string = self.m_textGenerator.genFailedHeader(header)
            headerDiv.append(headerText)
            self.m_mainDiv.append(headerDiv)

        def writeFailedInfo(self, table, file, dbName, currTime):
            infoDiv = self.m_soup.new_tag("p")
            infoDiv.append(self._makePropertyTable(self.m_textGenerator.genFailedInfo(table, file, dbName, currTime)))
            self.m_mainDiv.append(infoDiv)

        def writeSRIDMismatch(self, expectedSRID, actualSRID):
            infoDiv = self.m_soup.new_tag("p")
            infoDiv.string = self.m_textGenerator.genSRIDMismatch(expectedSRID, actualSRID)
            self.m_mainDiv.append(infoDiv)

            mismatchDiv = self.m_soup.new_tag("p")
            mismatchText = self.m_soup.new_tag("h1")
            mismatchText.string = self.m_textGenerator.genSRIDMismatch(expectedSRID, actualSRID)
            mismatchDiv.append(mismatchText)
            self.m_mainDiv.append(mismatchDiv)

        def writeErrorField(self, report):
            props, errors = self.m_textGenerator.genErrorField(report)
            errorDiv = self.m_soup.new_tag("p")
            errorDiv.append(self._makePropertyTable(props, 1, 140))
            errorDiv.append(self._makePropertyTable(errors))
            self.m_mainDiv.append(errorDiv)

        def finalize(self):
            self.m_mainDiv.append(self.m_soup.new_tag("br"))
            with open(os.path.join(self.m_dir, "report.html"), "w") as outf:
                outf.write(str(self.m_soup))
            return True

    def generateTextReport(self):
        generator = __class__.TextGenerator()
        self.generateReport("txt", generator)

    class ParallelPDFConverter(QObject):
        def __init__(self, tmpDir):
            super(__class__, self).__init__()
            self.m_tmpDir = tmpDir
            self.m_shotters = []
            self.m_finalized = False
            self.m_shottersProgress = dict()
            self.m_timer = QTimer(self)
            self.m_timer.setSingleShot(False)
            self.m_timer.setInterval(200)
            self.m_timer.timeout.connect(self.fakeProgress)
            self.m_timer.start()

        finished = pyqtSignal()

        fileProgress = pyqtSignal(int, int, int)  # min max val

        def fakeProgress(self):
            for key, val in self.m_shottersProgress.items():
                if val >= 50 and val < 100:
                    break
            else:
                return
            self.m_shottersProgress[key] += 1
            newInterval = 10000 / (100 - val)
            self.m_timer.setInterval(newInterval)
            self.emitProgress()

        class PageShotter(QWebEngineView):
            def __init__(self, url, pdfPath, parent=None):
                QWebEngineView.__init__(self, parent)
                self.m_url = url
                self.m_pdfPath = pdfPath

                self.setAttribute(Qt.WA_DontShowOnScreen, True)
                self.show()

                QWebEngineSettings.globalSettings().setAttribute(QWebEngineSettings.PluginsEnabled, True)
                QWebEngineSettings.globalSettings().setAttribute(QWebEngineSettings.ScreenCaptureEnabled, True)

                self.loadFinished.connect(self.save)
                self.loadProgress.connect(self.onLoadProgress)

            finished = pyqtSignal()
            shottProgress = pyqtSignal(int)

            def onLoadProgress(self, p):
                self.shottProgress.emit(p)

            def shot(self):
                self.load(self.m_url)

            def save(self):
                self.page().pdfPrintingFinished.connect(self.printFinished)
                self.page().printToPdf(self.m_pdfPath)

            def printFinished(self):
                self.finished.emit()

        def startConversion(self, htmlFile, pdfFile):
            url = QUrl.fromLocalFile(htmlFile)
            shotter = __class__.PageShotter(url, pdfFile)
            self.m_shotters.append(shotter)
            self.m_shottersProgress[shotter] = 0
            shotter.finished.connect(self.shotterFinished)
            shotter.shottProgress.connect(self.shotterProgress)
            shotter.shot()

            self.emitProgress()

        def emitProgress(self):
            min = 0
            max = 0
            val = 0
            for key, pr in self.m_shottersProgress.items():
                max += 100
                val += pr

            self.fileProgress.emit(min, max, val)

        def shotterProgress(self, p):
            self.m_shottersProgress[self.sender()] = (p / 2)
            self.emitProgress()

        def shotterFinished(self):
            self.m_shottersProgress[self.sender()] = 100
            self.emitProgress()
            del self.m_shottersProgress[self.sender()]
            self.m_shotters.remove(self.sender())
            if self.m_finalized:
                if len(self.m_shotters) == 0:
                    self.finishJob()

        def finishJob(self):
            shutil.rmtree(self.m_tmpDir)
            self.finished.emit()

        def finalize(self):
            self.m_finalized = True
            if len(self.m_shotters) == 0:
                self.finishJob()

    def generatePdfReport(self):
        dir = tempfile.mkdtemp()
        pdfConverter = __class__.ParallelPDFConverter(dir)
        pdfConverter.finished.connect(self.pdfConversionFinished)
        pdfConverter.fileProgress.connect(self.fileProgress)
        self.ui.progressBar.setFormat("Printing PDFs %p%")
        self.ui.progressBar.setTextVisible(True)
        self.m_pdfConverters.append(pdfConverter)
        generator = __class__.PdfGenerator(dir, pdfConverter)
        self.generateReport("pdf", generator)
        pdfConverter.finalize()

    def fileProgress(self, min, max, val):
        self.ui.progressBar.show()
        self.ui.progressBar.setMinimum(min)
        self.ui.progressBar.setMaximum(max)
        self.ui.progressBar.setValue(val)

    def pdfConversionFinished(self):
        self.m_pdfConverters.remove(self.sender())
        self.m_timer = QTimer(self)
        self.m_timer.setSingleShot(True)
        self.m_timer.setInterval(1000)
        self.m_timer.timeout.connect(self.ui.progressBar.hide)
        self.m_timer.start()

    def generateHtmlReport(self):
        generator = __class__.HtmlGenerator()
        self.generateReport("", generator)

    def generateReport(self, extension, generator):
        reports, reportPaths = self.generateReportPaths(extension)
        for report in reports:
            generator.openFile(reportPaths[report.table()])
            report.generate(generator)
            generator.finalize()

    def generateReportPaths(self, extension):
        selecteds = self.ui.exchangeValidateResultTable.table().selectionModel().selectedIndexes()
        if len(selecteds) == 0:
            return
        ids = list(set(sel.row() for sel in selecteds))
        reports = [self.ui.exchangeValidateResultTable.table().model().report(idx) for idx in ids]

        dir = QFileDialog.getExistingDirectory(None, "Reports directory")

        reportPaths = dict()
        answer = None
        for report in reports:
            reportPathWithoutExtension = os.path.join(dir, report.table() + "_" + os.path.basename(report.file()))
            reportPath = reportPathWithoutExtension + ("." + extension if extension != "" else "")
            if os.path.exists(reportPath):
                if answer is None or answer in [QMessageBox.Yes, QMessageBox.No]:
                    answer = QMessageBox.question(None, 'Report exists',
                                                  "File '%s' already exists. Do you want to overwrite it?\n" \
                                                  "Note: If no is pressed numeric postfix will be added to make filename unique" % reportPath,
                                                  QMessageBox.Yes | QMessageBox.YesToAll | QMessageBox.No | QMessageBox.NoToAll)

                if answer in [QMessageBox.YesToAll, QMessageBox.Yes]:
                    pass # File will be overwritten
                elif answer in [QMessageBox.NoToAll, QMessageBox.No]:
                    id = 2
                    reportPathWithoutExtensionCurr = reportPathWithoutExtension + "(%s)" % str(id)
                    id += 1
                    reportPath = reportPathWithoutExtension + ("." + extension if extension != "" else "")
                    while os.path.exists(reportPath):
                        reportPathWithoutExtensionCurr = reportPathWithoutExtension + "(%s)" % str(id)
                        id += 1
                        reportPath = reportPathWithoutExtension + ("." + extension if extension != "" else "")

            reportPaths[report.table()] = reportPath
        return (reports, reportPaths)

    def updateValidateButtonState(self):
        cnt = self.ui.exchangeValidateInputTable.model().rowCount()
        self.ui.exchangeValidateGoButton.setEnabled(cnt != 0)

    def getSRID(self, fileName):
        cmd = self.m_gdalsrsinfoExec + " -p -o xml " + fileName
        try:
            gxml = subprocess.check_output(cmd)
            return parseGML(gxml)
        except OSError as e:
            QMessageBox.warning(None, "Error", "Failed to execute gdalsrsinfo:\n\t%s" % e)
            return False
        except subprocess.CalledProcessError as e:
            QMessageBox.warning(None, "Error",
                                "Failed to execute %s:\n\t%s" % ("gdalsrsinfo", e.output.decode("utf-8")))
            return False

    def convertToGeoJSON(self, fileName, geoJSONName):
        srid = self.getSRID(fileName)
        if srid is None:
            srid = self.m_expectedSRID
            self.m_noSRIDFiles.append(fileName)
        gdalData = "--config GDAL_DATA " + self.m_gdalData
        cmd = self.m_ogr2ogrExec + " -f \"GeoJSON\" -a_srs EPSG:%s %s %s %s" %(str(int(srid)), geoJSONName, fileName, gdalData)
        try:
            print(cmd)
            subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except OSError as e:
            QMessageBox.warning(None, "Error", "Failed to execute org2org:\n\t%s" % e)
            return False
        except subprocess.CalledProcessError as e:
            QMessageBox.warning(None, "Error",
                                 "Failed to execute %s:\n\t%s" % ("ogr2ogr", e.output.decode("utf-8")))
            return False

        return True

    def doValidate(self):
        self.m_noSRIDFiles = []
        self.m_expectedSRID = self.m_database.localDatabase().schemaProperties(self.m_connId).properties[3]
        if self.ui.exchangeValidateResultTable.model().rowCount() != 0:
            res = QMessageBox.question(None, 'Delete Results?',
                                       "Previous validation results are exists. Delete previous results? \n"
                                       "Note: report files will not be deleted",
                                       QMessageBox.Yes, QMessageBox.No)
            if res == QMessageBox.No:
                return
            self.ui.exchangeValidateResultTable.model().clear()
            QCoreApplication.processEvents()

        dir = tempfile.mkdtemp()
        try:
            self.doValidateImpl(dir)
        except:
            raise
        finally:
            shutil.rmtree(dir)
            pass

        if len(self.m_noSRIDFiles) != "":
            QMessageBox.warning(None, "No SRID", "Following files have no associated SRID. Database SRID "
                                      "%s will be used instead\n\t %s" % (self.m_expectedSRID,
                                      "\n\t".join(self.m_noSRIDFiles)))

    def doValidateImpl(self, dir):
        model = self.ui.exchangeValidateInputTable.model()
        for item in model.items():
            file = item.fileName
            geoJSONName = os.path.basename(file) + str(uuid.uuid4()) + ".json"
            geoJSONName = os.path.join(dir, geoJSONName)
            table = item.tableName
            if self.convertToGeoJSON(file, geoJSONName):
                self.compareGeoJSONWithTable(file, geoJSONName, table)

    def compareGeoJSONWithTable(self, file, geoJSONName, table):
        columnInfo = self.m_database.localDatabase().columnInfoByTable(table)
        tableInfo = self.m_database.localDatabase().tableInfo(table, self.m_connId)
        metadata = self.m_database.metadata(self.m_connId, table, self.m_schema)
        report = __class__.ValidateReport(file, table, self.m_database)
        tester = __class__.GeoJSONTester(report, self.m_expectedSRID, columnInfo, tableInfo, metadata)
        try:
            parseGeoJSON(geoJSONName, tester)
        except Exception as e:
            QMessageBox.warning(None, "Error", "Failed to parse json file:\n\t%s" % e)
            return
        self.ui.exchangeValidateResultTable.model().appendResult(report)
        QCoreApplication.processEvents()

    class ValidateReport:
        def __init__(self, file, table, database):
            self.m_sridMismatch = None
            self.m_feautureReports = []
            self.m_file = file
            self.m_table = table
            self.m_database = database

        def file(self):
            return self.m_file

        def table(self):
            return self.m_table

        def setSRIDMismatch(self, expectedSRID, actualSRID):
            self.m_sridMismatch = (expectedSRID, actualSRID)

        def addFeautureReport(self, report):
            self.m_feautureReports.append(report)

        def generate(self, generator):
            # generator.writeLogo()
            if self.passed():
                generator.writeSuccessHeader("Predefined Passed header")
                generator.writeSuccessInfo(self.table(), self.file(), self.m_database.localDatabase().name(),
                                           QDateTime.currentDateTime())
            else:
                generator.writeFailedHeader("Predefined Failed header")
                generator.writeFailedInfo(self.table(), self.file(), self.m_database.localDatabase().name(),
                                           QDateTime.currentDateTime())
                if self.m_sridMismatch is not None:
                    generator.writeSRIDMismatch(self.m_sridMismatch[0], self.m_sridMismatch[1])

                for fReport in self.m_feautureReports:
                    fReport.generate(generator)

        def dump(self):
            error = False
            if self.m_sridMismatch is not None:
                print("SRID mismatch %s %s" % self.m_sridMismatch)
                error = True

            for fReport in self.m_feautureReports:
                fReport.dump()
                error = True

            if not error:
                print("Passed")

        def passed(self):
            error = (self.m_sridMismatch is not None) or (len(self.m_feautureReports) != 0)
            return not error

    class FeautureReport:
        def __init__(self, propsDict, geomObj):
            self.m_propsDict = propsDict
            self.m_geomObj = geomObj
            self.m_typeMismatch = None
            self.m_missingFields = []
            self.m_extraFields = []
            self.m_nullFields = []
            self.m_rangeViolations = []
            self.m_extentViolation = None

        def properties(self):
            return self.m_propsDict

        def typeMismatch(self):
            return self.m_typeMismatch

        def extentViolation(self):
            return self.m_extentViolation

        def missingFields(self):
            return self.m_missingFields

        def extraFields(self):
            return self.m_extraFields

        def nullFields(self):
            return self.m_nullFields

        def rangeViolations(self):
            return self.m_rangeViolations

        def markTypeMismatch(self, expected, actual):
            self.m_typeMismatch = (expected, actual)

        def addMissingField(self, fieldName):
            self.m_missingFields.append(fieldName)

        def addExtraField(self, fieldName):
            self.m_extraFields.append(fieldName)

        def addNullField(self, fieldName):
            self.m_nullFields.append(fieldName)

        def addRangeViolation(self, fieldName, min, max, value):
            self.m_rangeViolations.append((fieldName, min, max, value))

        def markExtentViolation(self, northLat, southLat, westLong, eastLong, violatedCoords):
            self.m_extentViolation = (northLat, southLat, westLong, eastLong, violatedCoords)

        def generate(self, generator):
            generator.writeErrorField(self)

        def dump(self):
            if self.m_typeMismatch:
                print("Type mismatch for feauture %s (%s)" % (str(self.m_propsDict), self.m_geomObj.type))

            if len(self.m_missingFields) != 0:
                print("Missing fields %s : %s" % (str(self.m_missingFields), str(self.m_propsDict)))

            if len(self.m_extraFields) != 0:
                print("Extra fields %s : %s" % (str(self.m_extraFields), str(self.m_propsDict)))

            if len(self.m_nullFields) != 0:
                print("Null fields (Should be not null) %s : %s" % (str(self.m_nullFields), str(self.m_propsDict)))

            if len(self.m_rangeViolations) != 0:
                print("Range violations for %s : %s" % (str(self.m_rangeViolations), str(self.m_propsDict)))

            if self.m_extentViolation:
                print("Extent violation for %s" % str(self.m_propsDict))

    class GeoJSONTester(GeoJSONVisitor):
        def __init__(self, report, expectedSRID, columnInfo, tableInfo, metadata):
            self.m_report = report
            self.m_expectedSRID = expectedSRID
            self.m_columns = dict()
            group, title, description, isSpatial, spatialType, local = tableInfo
            self.m_spatialType = spatialType
            for col_name, col_desc, col_type, col_size, col_scale, \
                col_units, default_value, lu_table, column_maxval, \
                column_minval, is_primary_key, nullok in columnInfo:
                if is_primary_key == 'Y':
                    continue
                self.m_columns[col_name.lower()] = (col_type, column_maxval, column_minval, True if nullok == 'Y' else 'N')

            self.m_westLong = metadata.westLong.originalValue
            self.m_eastLong = metadata.eastLong.originalValue
            self.m_southLat = metadata.southLat.originalValue
            self.m_northLat = metadata.northLat.originalValue

            if self.m_westLong == "":
                self.m_westLong = None

            if self.m_eastLong == "":
                self.m_eastLong = None

            if self.m_southLat == "":
                self.m_southLat = None

            if self.m_northLat == "":
                self.m_northLat = None

        def visitType(self, type):
            pass

        def visitName(self, name):
            pass

        def visitSRID(self, SRID):
            config = Configuration()
            gdalsrsinfoExec = os.path.join(config.ogr2ogrDir(), "gdalsrsinfo.exe")

            cmd = gdalsrsinfoExec + " -p -o xml " + SRID
            try:
                gxml = subprocess.check_output(cmd)
                SRID = parseGML(gxml)
            except:
                pass

            if SRID != self.m_expectedSRID:
                self.m_report.setSRIDMismatch(self.m_expectedSRID, SRID)

        def beginFeatures(self):
            pass

        def endFeatures(self):
            pass

        def visitGeometry(self, propsDictOrig, geomObj):
            fReport = ExchangeTabValidateController.FeautureReport(propsDictOrig, geomObj)
            error = False
            if geomObj.type.lower() != self.m_spatialType.lower():
                error = True
                fReport.markTypeMismatch(self.m_spatialType, geomObj.type.lower())

            propsDict = dict()
            for key, value in propsDictOrig.items():
                propsDict[key.lower()] = value

            fields = list(propsDict.keys())
            reqFields = self.m_columns.keys()
            for req in reqFields:
                if req not in fields:
                    error = True
                    fReport.addMissingField(req)
                else:
                    fields.remove(req)

            for extra in fields:
                error = True
                fReport.addExtraField(extra)

            for req in reqFields:
                if self.m_columns[req][-1] == 'N': # Testing nullok
                    if propsDict.get(req, None) is None:
                        error = True
                        fReport.addNullField(req)

            for req in reqFields:
                max_val = self.m_columns[req][1]
                min_val = self.m_columns[req][2]
                type = self.m_columns[req][0]
                if type.lower() in ["smallint", "integer", "bigint"]:
                    type = int
                else:
                    type = float

                if max_val == "":
                    max_val = None

                if min_val == "":
                    min_val = None

                if max_val is not None or min_val is not None:
                    val = propsDict[req]
                    try:
                        if max_val is not None and type(val) > type(max_val) or \
                                min_val is not None and type(val) < type(min_val):
                            error = True
                            fReport.addRangeViolation(req, min_val, max_val, val)
                    except:
                        pass

            violatedCoords = []
            coords = geomObj.coordinates
            if geomObj.type.lower() == "point":
                coords = [coords]
            for coord in coords:
                long, lat = coord

                if self.m_northLat is not None and int(lat) > int(self.m_northLat) or \
                    self.m_southLat is not None and int(lat) < int(self.m_southLat) or \
                    self.m_westLong is not None and int(long) > int(self.m_westLong) or \
                    self.m_eastLong is not None and int(long) < int(self.m_eastLong):

                    error = True
                    violatedCoords.append(coord)

            if len(violatedCoords) != 0:
                fReport.markExtentViolation(self.m_northLat, self.m_southLat, self.m_westLong, self.m_eastLong, violatedCoords)

            if error:
                self.m_report.addFeautureReport(fReport)

    def newRowIndex(self):
        selecteds = self.ui.exchangeValidateInputTable.table().selectionModel().selectedIndexes()
        if len(selecteds) != 0:
            idx = selecteds[-1].row() + 1
        else:
            idx = self.ui.exchangeValidateInputTable.model().rowCount()

        return idx

    def addFilePressed(self):
        dlg = EditFileTaskWidget(None, self.ui.exchangeExportDir.text(), "", "", self.m_database, self.m_connId)
        res = dlg.exec()
        if res == QDialog.Rejected:
            return
        idx = self.newRowIndex()
        self.m_model.insertFile(idx, dlg.selectedFile(), dlg.selectedRule())

    def editFilePressed(self):
        selecteds = self.ui.exchangeValidateInputTable.table().selectionModel().selectedIndexes()
        if len(selecteds) == 0:
            return
        idx = selecteds[-1].row()
        dlg = EditFileTaskWidget(None, "", self.m_model.filePath(idx), self.m_model.rule(idx), self.m_database, self.m_connId)
        res = dlg.exec()
        if res == QDialog.Rejected:
            return
        file = dlg.selectedFile()
        self.m_model.setFile(idx, file, dlg.selectedRule())

    def deleteFilePressed(self):
        selecteds = self.ui.exchangeValidateInputTable.table().selectionModel().selectedIndexes()
        if len(selecteds) == 0:
            return
        idx = selecteds[-1].row()
        self.m_model.deleteFile(idx)

class ExchangeTabImportsController(QObject):
    def __init__(self, ui, database, schema, connId, host, port, dbName, user, password):
        super(ExchangeTabImportsController, self).__init__()
        self.ui = ui
        self.m_database = database
        self.m_schema = schema
        self.m_connId = connId
        self.m_currentSchemaHost = host
        self.m_currentSchemaPort = port
        self.m_currentSchemaDBName = dbName
        self.m_currentSchemaUserName = user
        self.m_currentSchemaPassword = password

        self.m_prefix = self.m_database.globalNamingConv[0]  # Assuming is spatial

        config = Configuration()
        self.m_ogr2ogrExec = os.path.join(config.ogr2ogrDir(), "ogr2ogr.exe")

        self.ui.exchangeImportsUsePrefix.toggled.connect(self.usePrefixToggled)
        self.usePrefixToggled(False)

        self.m_database.tableListChanged.connect(self.setTableNames)
        self.setTableNames()

        self.ui.exchangeImportsExistingTableRadioBtn.toggled.connect(self.exchangeImportsExistingTableRadioBtnToggled)
        self.ui.exchangeImportsExistingTableRadioBtn.setChecked(True)

        self.ui.exchangeImportsImportToEdit.textChanged.connect(self.updateRealNameEdit)

        self.ui.exchangeImportsSelectFileEdit.textChanged.connect(self.updateCommandAndButtonState)
        self.ui.exchangeImportSwitches.textChanged.connect(self.updateCommandAndButtonState)
        self.ui.exchangeImportsExistingTableRadioBtn.toggled.connect(self.updateCommandAndButtonState)
        self.ui.exchangeImportsExistingTableCombo.currentTextChanged.connect(self.updateCommandAndButtonState)
        self.ui.exchangeImportsImportToEdit.textChanged.connect(self.updateCommandAndButtonState)
        self.ui.exchangeImportsUsePrefix.toggled.connect(self.updateCommandAndButtonState)
        self.updateCommandAndButtonState()

        self.ui.exchangeImportsgoButton.pressed.connect(self.doImport)
        self.ui.exchangeImportsSelectFileBrowse.pressed.connect(self.browseInputFile)

    def setTableNames(self):
        self.ui.exchangeImportsExistingTableCombo.clear()
        self.ui.exchangeImportsExistingTableCombo.addItems(
            self.m_database.localDatabase().localTableList(self.m_connId, False))

    def updateCommandAndButtonState(self):
        self.m_exportCmd = self.createCommand()
        if self.m_exportCmd is None:
            self.ui.exchangeImportCmdEdit.setPlainText("")
            self.ui.exchangeImportsgoButton.setDisabled(True)
        else:
            self.ui.exchangeImportCmdEdit.setPlainText("ogr2ogr " + self.m_exportCmd)
            self.ui.exchangeImportsgoButton.setEnabled(True)

    def currentTableName(self):
        tableName = ""
        if self.ui.exchangeImportsExistingTableRadioBtn.isChecked():
            tableName = self.ui.exchangeImportsExistingTableCombo.currentText()
        else:
            tableName = self.ui.exchangeImportsImportToEdit.text()
            if self.ui.exchangeImportsUsePrefix.isChecked() and tableName != "":
                tableName = self.m_prefix + tableName

        return tableName

    def createCommand(self):
        fileName = self.ui.exchangeImportsSelectFileEdit.text()

        if fileName == "":
            return None

        tableName = self.currentTableName()
        if tableName == "":
            return None

        self.m_currentTableName = tableName

        tableName = self.m_schema + "." + tableName

        switches = self.ui.exchangeImportSwitches.text()

        cmd = "-append -f \"PostgreSQL\" PG:\"dbname='%s' host='%s' port='%s' user='%s' password='%s'\" %s -nln %s %s" % \
              (self.m_currentSchemaDBName, self.m_currentSchemaHost, self.m_currentSchemaPort, \
               self.m_currentSchemaUserName, self.m_currentSchemaPassword, fileName, tableName, switches)

        self.m_currentFileName = fileName

        return cmd

    def exchangeImportsExistingTableRadioBtnToggled(self, checked):
        self.ui.exchangeImportsExistingTableCombo.setEnabled(checked)
        self.ui.exchangeImportsImportToEdit.setEnabled(not checked)
        self.ui.exchangeImportsUsePrefix.setEnabled(not checked)
        self.ui.exchangeImportsRealNameEdit.setEnabled(not checked)

    def usePrefixToggled(self, checked):
        self.ui.exchangeImportsRealNameEdit.setVisible(checked)
        self.updateRealNameEdit()

    def updateRealNameEdit(self):
        if self.ui.exchangeImportsUsePrefix.isChecked():
            self.ui.exchangeImportsRealNameEdit.setText(self.m_prefix + self.ui.exchangeImportsImportToEdit.text())

    def browseInputFile(self):
        path, _ = QFileDialog.getOpenFileName(None, "Import File")
        if path != "":
            self.ui.exchangeImportsSelectFileEdit.setText(path)

    def doImport(self):
        command = self.m_ogr2ogrExec + " " + self.m_exportCmd
        print("Running command '%s'" % command)
        try:
            subprocess.check_output(command, stderr=subprocess.STDOUT)
            QMessageBox.information(None, "Success",
                            "Table %s was successfully imported from '%s'" % \
                                (self.m_currentTableName, self.m_currentFileName))

            self.m_database.ensureTableAndColumnsAreCached(self.m_currentTableName, self.m_connId, self.m_schema)
            self.m_database.tableListChanged.emit()
        except OSError as e:
            QMessageBox.warning(None, "Error", "Failed to execute org2org:\n\t%s" % e)
        except subprocess.CalledProcessError as e:
            QMessageBox.warning(None, "Error", "Failed to execute %s:\n\t%s" % ("ogr2ogr", e.output.decode("utf-8")))

class ExchangeTabController(QObject):
    def __init__(self, ui, database, schema, connId, host, port, dbName, user, password):
        super(ExchangeTabController, self).__init__()
        self.m_exportsController = ExchangeTabExportsController(ui, database, schema, connId, host, port, dbName, user, password)
        self.m_validateController = ExchangeTabValidateController(ui, database, schema, connId, host, port, dbName, user,
                                                                password)
        self.m_importsController = ExchangeTabImportsController(ui, database, schema, connId, host, port, dbName, user,
                                                                password)