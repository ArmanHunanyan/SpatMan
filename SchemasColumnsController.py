
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QAbstractItemView
from PyQt5.QtCore import QAbstractTableModel
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QAction
from PyQt5.QtCore import Qt

from TableInfo import TableInfo
from ColumnsTableModel import ColumnsTableModelFactory
from ModelWithValidators import ModelWithValidatorsFactory
from CommonColumnsSelector import CommonColumnsSelector2

import fnmatch

class ColumnsTableModel(QAbstractTableModel):
    def __init__(self, database, connId):
        super(ColumnsTableModel, self).__init__(None)

        self.m_data = []
        self.m_database = database
        self.m_modified = False
        self.m_connId = connId

    def setTableName(self, schema, tableName):
        self.modelAboutToBeReset.emit()

        self.m_tableName = tableName
        self.m_schema = schema

        if tableName == "":
            self.m_data = []
        else:
            infos = self.m_database.columnsInfo(schema, tableName, self.m_connId)
            self.m_data = list(TableInfo(0, False, *info) for info in infos)

        self.m_modified = False
        self.modelReset.emit()
        self.modified.emit(self.m_modified)

    def save(self):
        error = False
        self.modelAboutToBeReset.emit()

        for row in range(self.rowCount()):
            if self.keyDropped(row):
                try:
                    self.m_database.saveColumn(self.m_data[row], self.m_tableName, self.m_schema,
                                           self.m_connId)
                    self.m_data[row].commitChanges()
                except Exception as e:
                    QMessageBox.warning(None, "Failed", str(e))
                    error = True


        for row in range(self.rowCount()):
            if self.rowIsModified(row):
                try:
                    self.m_database.saveColumn(self.m_data[row], self.m_tableName, self.m_schema,
                                           self.m_connId)
                except Exception as e:
                    QMessageBox.warning(None, "Failed", str(e))
                    error = True
        if not error:
            self.setTableName(self.m_schema, self.m_tableName)
            self.m_modified = False
        self.modelReset.emit()
        if not error:
            self.modified.emit(self.m_modified)

class SchemasColumnsController(QObject):
    def __init__(self, ui, database, schema, connId):
        super(SchemasColumnsController, self).__init__()
        self.ui = ui
        self.m_database = database
        self.m_schema = schema
        self.m_connId = connId

        self.ui.schemaColumnsTableListWidget.setSelectionMode(QAbstractItemView.SingleSelection)

        # Modify these members together
        self.setTableNames()
        self.ui.schemaColumnsTableListFilterBtn.pressed.connect(self.doFilter)
        self.ui.schemaColumnsTableListFilterEdit.returnPressed.connect(self.doFilter)
        self.m_database.tableNameChanged.connect(self.renameTable)
        self.m_database.tableListChanged.connect(self.setTableNames)

        self.ui.schemaColumnsTableListWidget.selectionModel().selectionChanged.connect(self.tablesListSelectionChanged)

        self.ui.schemaColumnsColumnTable.setModel(ColumnsTableModelFactory(ModelWithValidatorsFactory(ColumnsTableModel))(self.m_database, self.m_connId))

        self.ui.schemaColumnsColumnTable.model().modified.connect(self.updateSaveResetBtnsState)
        self.ui.schemaColumnsColumnTable.model().dataChanged.connect(self.updateSaveResetBtnsState)
        self.ui.schemaColumnsColumnTable.model().initValidators(None)
        self.updateSaveResetBtnsState()

        self.ui.schemaColumnsColumnTable.init(None)

        self.ui.schemaColumnsResetButton.pressed.connect(self.resetPressed)
        self.ui.schemaColumnsSaveButton.pressed.connect(self.savePressed)

        self.ui.schemaColumnsTableListWidget.selectionModel().selectionChanged.connect(self.updateAddDeleteBtnsState)
        self.ui.schemaColumnsColumnTable.table().selectionModel().selectionChanged.connect(self.updateAddDeleteBtnsState)
        self.updateAddDeleteBtnsState()

        self.ui.schemaColumnsColumnTable.addBtn().pressed.connect(self.addTableColumn)
        self.ui.schemaColumnsColumnTable.deleteBtn().pressed.connect(self.deleteTableColumn)

        addKeyAction = QAction("Add Key", self)
        addKeyAction.triggered.connect(self.addKeyColumn)
        addCommonAction = QAction("Add Common...", self)
        addCommonAction.triggered.connect(self.addCommonColumns)
        self.ui.schemaColumnsColumnTable.addActionToAddBtn(addKeyAction)
        self.ui.schemaColumnsColumnTable.addActionToAddBtn(addCommonAction)

        self.ui.schemaColumnsColumnTable.model().setPrimaryKeyEditable(True)

    def addKeyColumn(self):
        key = self.ui.schemaColumnsColumnTable.model().keyColumn()
        if key is not None:
            res = QMessageBox.question(None, 'Key Exists',
                                       "Table already have Primary key '%s'. \n"
                                       "Do you want to drop it before adding new one?" % key.value(0).modifiedValue,
                                       QMessageBox.Yes, QMessageBox.No)
            if res == QMessageBox.Yes:
                self.ui.schemaColumnsColumnTable.model().dropPrimaryKey()

        idx = self.newRowIndex()
        newCol = self.m_database.uidColumn()
        newCol = TableInfo(0, True, *newCol[1:])
        newCol.setAdded()
        self.ui.schemaColumnsColumnTable.model().insertRow(idx, newCol)
        self.scrolltoIndex(idx)

    def addCommonColumns(self):
        idx = self.newRowIndex()

        selDialog = CommonColumnsSelector2(self.m_database, self.m_connId)
        if selDialog.exec() == selDialog.Rejected:
            return

        newData = selDialog.result()
        for newCol in newData:
            newCol.setLocal(False)
            newCol.setAdded()
            newCol.freez(False)
            self.ui.schemaColumnsColumnTable.model().insertRow(idx, newCol)
            idx += 1

        self.scrolltoIndex(idx)

    def newRowIndex(self):
        selecteds = self.ui.schemaColumnsColumnTable.table().selectionModel().selectedIndexes()
        if len(selecteds) != 0:
            idx = selecteds[-1].row() + 1
        else:
            idx = self.ui.schemaColumnsColumnTable.model().rowCount()

        return idx

    def addTableColumn(self):
        idx = self.newRowIndex()
        self.ui.schemaColumnsColumnTable.model().addRow(idx)
        self.scrolltoIndex(idx)

    def scrolltoIndex(self, idx):
        if idx >= (self.ui.schemaColumnsColumnTable.model().rowCount() - 1):
            self.ui.schemaColumnsColumnTable.table().scrollToBottom()
        else:
            self.ui.schemaColumnsColumnTable.table().scrollTo(self.ui.schemaColumnsColumnTable.model().createIndex(idx, 0))

    def deleteTableColumn(self):
        selecteds = self.ui.schemaColumnsColumnTable.table().selectionModel().selectedIndexes()
        if len(selecteds) == 0:
            return
        self.ui.schemaColumnsColumnTable.model().deleteRows([sel.row() for sel in selecteds])

    def updateAddDeleteBtnsState(self):
        sel = self.ui.schemaColumnsTableListWidget.selectionModel().selectedIndexes()
        enableAdd = (len(sel) != 0)

        enableDelete = enableAdd and (len(self.ui.schemaColumnsColumnTable.table().selectionModel().selectedIndexes()) != 0)
        enableBrowse = enableAdd

        self.ui.schemaColumnsColumnTable.addBtn().setEnabled(enableAdd)
        self.ui.schemaColumnsColumnTable.deleteBtn().setEnabled(enableDelete)
        self.ui.schemaColumnsColumnTable.browseBtn().setEnabled(enableBrowse)

    def renameTable(self, orig, modified):
        for idx in range(self.ui.schemaColumnsTableListWidget.count()):
            if self.ui.schemaColumnsTableListWidget.item(idx).text() == orig:
                self.ui.schemaColumnsTableListWidget.item(idx).setText(modified)
                break

    def setTableNames(self):
        self.ui.schemaColumnsTableListWidget.clear()
        self.m_tables = self.m_database.schemaTableList(self.m_schema)
        self.doFilter()

    def resetPressed(self):
        self.ui.schemaColumnsColumnTable.model().reset()

    def savePressed(self):
        self.ui.schemaColumnsColumnTable.model().save()

    def updateSaveResetBtnsState(self):
        modified = self.ui.schemaColumnsColumnTable.model().isModified()
        self.ui.schemaColumnsResetButton.setEnabled(modified)
        self.ui.schemaColumnsSaveButton.setEnabled(modified and self.ui.schemaColumnsColumnTable.model().isValid())

    def doFilter(self):
        # disconnect deselected signal to not loose information in table
        filter = self.ui.schemaColumnsTableListFilterEdit.text()
        filteredItems = self.m_tables if len(filter) == 0 else fnmatch.filter(self.m_tables, filter)

        # Deselect items that are going to be lost
        for idx in range(self.ui.schemaColumnsTableListWidget.count()):
            if self.ui.schemaColumnsTableListWidget.item(idx).text() not in filteredItems:
                self.ui.schemaColumnsTableListWidget.item(idx).setSelected(False)

        # Update items
        knownIndx = 0
        for table in self.m_tables:
            if table not in filteredItems:
                idx = 0
                while idx < self.ui.schemaColumnsTableListWidget.count():
                    if self.ui.schemaColumnsTableListWidget.item(idx).text() == table:
                        self.ui.schemaColumnsTableListWidget.takeItem(idx)
                        knownIndx = idx
                        break
                    else:
                        idx += 1

            else:
                found = False
                for idx in range(self.ui.schemaColumnsTableListWidget.count()):
                    if self.ui.schemaColumnsTableListWidget.item(idx).text() == table:
                        found = True
                        break
                if not found:
                    self.ui.schemaColumnsTableListWidget.insertItem(knownIndx, table)
                    knownIndx += 1

    def tablesListSelectionChanged(self, selected, deselected):
        sel = self.ui.schemaColumnsTableListWidget.selectionModel().selectedIndexes()
        if len(sel) == 0:
            self.ui.schemaColumnsColumnTable.model().setTableName(self.m_schema, "")
            return
        if len(sel) != 1:
            return

        idx = sel[0].row()
        tableName = self.ui.schemaColumnsTableListWidget.item(idx).text()
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.ui.schemaColumnsColumnTable.model().setTableName(self.m_schema, tableName)
        except Exception as e:
            QMessageBox.warning(None, "Failed", str(e))
        finally:
            QApplication.restoreOverrideCursor()
