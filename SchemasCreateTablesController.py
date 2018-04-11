
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QAbstractItemView
from PyQt5.QtCore import QAbstractTableModel
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QModelIndex
from PyQt5.QtCore import Qt

from TableInfo import TableInfo
from ColumnsTableModel import ColumnsTableModelFactory
from ModelWithValidators import ModelWithValidatorsFactory
from CommonColumnsSelector import CommonColumnsSelector

import fnmatch

class CreateTableColumnseModel(QAbstractTableModel):
    def __init__(self, database, connId):
        super(CreateTableColumnseModel, self).__init__(None)

        self.m_data = []
        self.m_database = database
        self.m_modified = False
        self.m_connId = connId

        self.m_database.commonColumnsChangedSignal.connect(self.populateCommonColumns)

        self.addKeyColumn()
        self.m_database.uidChangedSignal.connect(self.addKeyColumn)

        self.populateCommonColumns()

    def addGeometryColumn(self, add, type):
        if add:
            geomColumnIdx = 0
            if self.keyColumneExists():
                geomColumnIdx = 1

            if len(self.m_data) > geomColumnIdx and self.m_data[geomColumnIdx].frozen() and self.m_data[geomColumnIdx].id() == -1:
                self.rowsAboutToBeRemoved.emit(QModelIndex(), geomColumnIdx, geomColumnIdx)
                del self.m_data[geomColumnIdx]
                self.rowsRemoved.emit(QModelIndex(), geomColumnIdx, geomColumnIdx)

            newCol = self.m_database.geomColumn(type, self.m_connId)
            if newCol is None:
                return

            self.rowsAboutToBeInserted.emit(QModelIndex(), geomColumnIdx, geomColumnIdx)
            self.m_data.insert(geomColumnIdx, TableInfo(newCol[0], False, *newCol[1:]))
            self.m_data[geomColumnIdx].freez(True)
            self.rowsInserted.emit(QModelIndex(), geomColumnIdx, geomColumnIdx)

        else:
            geomColumnIdx = 0
            if self.keyColumneExists():
                geomColumnIdx = 1

            if len(self.m_data) > geomColumnIdx and self.m_data[geomColumnIdx].frozen() and \
                                                            self.m_data[geomColumnIdx].id() == -1:
                self.rowsAboutToBeRemoved.emit(QModelIndex(), geomColumnIdx, geomColumnIdx)
                del self.m_data[geomColumnIdx]
                self.rowsRemoved.emit(QModelIndex(), geomColumnIdx, geomColumnIdx)

    def keyColumneExists(self):
        if len(self.m_data) == 0:
            return False

        if not self.m_data[0].frozen():
            return False

        if self.m_data[0].id() != 0:
            return False

        return True

    def addKeyColumn(self):
        newCol = self.m_database.uidColumn()
        if newCol is None:
            if len(self.m_data) == 0:
                pass
            elif not self.m_data[0].frozen() or self.m_data[0].id() != 0:
                pass
            else: # UID column exists
                del self.m_data[0]
        else:
            if len(self.m_data) == 0:
                self.m_data.append(TableInfo(newCol[0], False, *newCol[1:]))
                self.m_data[0].freez(True)
            elif not self.m_data[0].frozen() or self.m_data[0].id() != 0:
                self.m_data.insert(0, TableInfo(newCol[0], False, *newCol[1:]))
                self.m_data[0].freez(True)
            else: # UID column exists
                self.m_data[0] = TableInfo(newCol[0], False, *newCol[1:])
                self.m_data[0].freez(True)

    def populateCommonColumns(self):
        columns = self.m_database.commonColumnsInfo(self.m_connId)

        tableIdx = 0
        while tableIdx < len(self.m_data):
            if not self.m_data[tableIdx].frozen() or self.m_data[tableIdx].id() <= 0: # Not a common column
                tableIdx += 1
                continue

            # Find id in new columns
            id = not self.m_data[tableIdx].id()
            newCol = [col for col in columns if col[0] == id]
            if len(newCol) == 0:
                # Common column deleted
                del self.m_data[tableIdx]
                continue

            newCol = newCol[0]
            self.m_data[tableIdx] = TableInfo(newCol[0], False, *newCol[1:])
            tableIdx += 1

    def updateCommonColumns(self, newData, pos):
        self.modelAboutToBeReset.emit()
        tableIdx = 0
        while tableIdx < len(self.m_data):
            if not self.m_data[tableIdx].frozen() or self.m_data[tableIdx].id() <= 0: # Not a common column
                tableIdx += 1
                continue

            # Find id in new columns
            id = self.m_data[tableIdx].id()
            newCol = [col for col in newData if col.id() == id]
            if len(newCol) == 0:
                # Common column deleted
                del self.m_data[tableIdx]
                continue

            tableIdx += 1

        for add in newData:
            if add.id() not in [row.id() for row in self.m_data if row.frozen()]:
                self.insertRow(pos, add)
                pos += 1

        self.modelReset.emit()


    def currentCommonColumns(self):
        return list([row for row in self.m_data if row.frozen() and row.id() > 0])

class SchemasCreateTablesController(QObject):
    def __init__(self, ui, database, schema, connId):
        super(SchemasCreateTablesController, self).__init__()
        self.ui = ui
        self.m_database = database
        self.m_schema = schema
        self.m_connId = connId

        self.ui.schemaCreateTablesColumnTable.table().setSelectionMode(QAbstractItemView.SingleSelection)

        self.ui.schemaCreateTablesColumnTable.setModel(ColumnsTableModelFactory(ModelWithValidatorsFactory(CreateTableColumnseModel))(self.m_database, self.m_connId))
        self.ui.schemaCreateTablesColumnTable.showClearAll(True)
        self.ui.schemaCreateTablesColumnTable.showBrowse(True)
        self.ui.schemaCreateTablesColumnTable.init(None)
        self.ui.schemaCreateTablesColumnTable.model().initValidators(None)
        self.ui.schemaCreateTablesColumnTable.model().setCommitAfterChange(True)
        self.ui.schemaCreateTablesColumnTable.model().rowsRemoved.connect(self.updateCreateButtonState)
        self.ui.schemaCreateTablesColumnTable.model().rowsInserted.connect(self.updateCreateButtonState)
        self.ui.schemaCreateTablesColumnTable.model().modelReset.connect(self.updateCreateButtonState)
        self.ui.schemaCreateTablesColumnTable.model().dataChanged.connect(self.updateCreateButtonState)
        self.ui.schemaCreateTablesTableNameEdit.textChanged.connect(self.updateCreateButtonState)
        self.ui.schemaCreateTablesTitleEdit.textChanged.connect(self.updateCreateButtonState)
        self.m_database.commonColumnsChangedSignal.connect(self.updateCreateButtonState)
        self.updateCreateButtonState()

        self.ui.schemaCreateTablesColumnTable.table().selectionModel().selectionChanged.connect(self.updateAddDeleteBtnsState)
        self.updateAddDeleteBtnsState()

        self.ui.schemaCreateTablesColumnTable.addBtn().pressed.connect(self.addColumn)
        self.ui.schemaCreateTablesColumnTable.deleteBtn().pressed.connect(self.deleteColumn)
        self.ui.schemaCreateTablesColumnTable.clearAllBtn().pressed.connect(self.clearAllColumns)
        self.ui.schemaCreateTablesColumnTable.browseBtn().pressed.connect(self.browseCommonColumns)

        self.updateGroups()
        self.m_database.schemaGroupListChangedSignal.connect(self.updateGroups)

        self.ui.schemaCreateTablesCreateButton.pressed.connect(self.createTable)

        self.ui.schemaCreateTablesIsSpatialYesBtn.toggled.connect(self.updateRealName)
        self.ui.schemaCreateTablesTableNameEdit.textChanged.connect(self.updateRealName)
        self.updateRealName()

        self.ui.schemaCreateTablesIsSpatialYesBtn.toggled.connect(self.addGeomColumn)
        self.ui.schemaCreateTablesSpatialTypeCombo.currentIndexChanged.connect(self.addGeomColumn)
        self.addGeomColumn()

    def addGeomColumn(self):
        try:
            if self.ui.schemaCreateTablesIsSpatialYesBtn.isChecked():
                self.ui.schemaCreateTablesColumnTable.model().addGeometryColumn(True, self.ui.schemaCreateTablesSpatialTypeCombo.currentText())
            else:
                self.ui.schemaCreateTablesColumnTable.model().addGeometryColumn(False, None)
        except Exception as e:
            print(e)

    def updateRealName(self):
        isSpatial = self.ui.schemaCreateTablesIsSpatialYesBtn.isChecked()
        if isSpatial:
            self.ui.schemaCreateTablesSpatialTypeCombo.setEnabled(True)
        else:
            self.ui.schemaCreateTablesSpatialTypeCombo.setEnabled(False)

        if isSpatial:
            self.m_prefix = self.m_database.globalNamingConv[0]
        else:
            self.m_prefix = self.m_database.globalNamingConv[1]
        self.ui.schemaCreateTablesTableRealNameEdit.setText(self.m_prefix + self.ui.schemaCreateTablesTableNameEdit.text())

    def browseCommonColumns(self):

        selecteds = self.ui.schemaCreateTablesColumnTable.table().selectionModel().selectedIndexes()
        if len(selecteds) != 0:
            idx = selecteds[-1].row() + 1
        else:
            idx = self.ui.schemaCreateTablesColumnTable.model().rowCount()

        selDialog = CommonColumnsSelector(self.ui.schemaCreateTablesColumnTable.model().currentCommonColumns(), self.m_database, self.m_connId)
        if selDialog.exec() == selDialog.Rejected:
            return

        newData = selDialog.result()

        self.ui.schemaCreateTablesColumnTable.model().updateCommonColumns(newData, idx)

    def createTable(self):
        name = self.ui.schemaCreateTablesTableRealNameEdit.text()
        group = self.ui.schemaCreateTablesGroupCombo.currentText()
        title = self.ui.schemaCreateTablesTitleEdit.text()
        description = self.ui.schemaCreateTablesDescriptionEdit.toPlainText()
        isSpatial = self.ui.schemaCreateTablesIsSpatialYesBtn.isChecked()
        spatialType = self.ui.schemaCreateTablesSpatialTypeCombo.currentText() if isSpatial else ""
        columns = self.ui.schemaCreateTablesColumnTable.model().m_data

        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.m_database.createTable(self.m_connId, self.m_schema, name, group, title, description, isSpatial, spatialType, columns)
            QApplication.restoreOverrideCursor()
            QMessageBox.information(None, "Table created", "Table '%s' successfully created in schema '%s'" % (name, self.m_schema))
            self.ui.schemaCreateTablesTableNameEdit.clear()
            self.ui.schemaCreateTablesGroupCombo.setCurrentIndex(0)
            self.ui.schemaCreateTablesTitleEdit.clear()
            self.ui.schemaCreateTablesDescriptionEdit.clear()
            self.ui.schemaCreateTablesIsSpatialYesBtn.setChecked(True)
            self.ui.schemaCreateTablesSpatialTypeCombo.setCurrentIndex(0)
            self.ui.schemaCreateTablesColumnTable.model().deleteAll()
            self.ui.schemaCreateTablesColumnTable.model().addKeyColumn()
            self.addGeomColumn()
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(None, "Failed", str(e))

    def updateGroups(self):
        self.ui.schemaCreateTablesGroupCombo.clear()
        groupList = ['FromDB'] + self.m_database.schemaGroupList(self.m_connId)
        self.ui.schemaCreateTablesGroupCombo.addItems(groupList)

    def updateCreateButtonState(self):
        rowCount = self.ui.schemaCreateTablesColumnTable.model().rowCount()
        enabled = rowCount != 0
        enabled = enabled and self.ui.schemaCreateTablesColumnTable.model().isValid()
        enabled = enabled and (self.ui.schemaCreateTablesTableNameEdit.text() != "")
        enabled = enabled and (self.ui.schemaCreateTablesTitleEdit.text() != "")
        self.ui.schemaCreateTablesCreateButton.setEnabled(enabled)

    def addColumn(self):
        selecteds = self.ui.schemaCreateTablesColumnTable.table().selectionModel().selectedIndexes()
        if len(selecteds) != 0:
            idx = selecteds[-1].row() + 1
        else:
            idx = self.ui.schemaCreateTablesColumnTable.model().rowCount()
        self.ui.schemaCreateTablesColumnTable.model().addRow(idx)
        self.ui.schemaCreateTablesColumnTable.table().scrollToBottom()

    def deleteColumn(self):
        selecteds = self.ui.schemaCreateTablesColumnTable.table().selectionModel().selectedIndexes()
        if len(selecteds) == 0:
            return
        self.ui.schemaCreateTablesColumnTable.model().deleteRows([sel.row() for sel in selecteds])

    def clearAllColumns(self):
        self.ui.schemaCreateTablesColumnTable.model().deleteUnfrozenColumns()

    def updateAddDeleteBtnsState(self):
        enableAdd = True
        enableClearAll = True
        enableDelete = enableAdd and (
        len(self.ui.schemaCreateTablesColumnTable.table().selectionModel().selectedIndexes()) != 0)

        if enableDelete:
            for idx in self.ui.schemaCreateTablesColumnTable.table().selectionModel().selectedIndexes():
                if not self.ui.schemaCreateTablesColumnTable.model().isNotFrozen(self.ui.schemaCreateTablesColumnTable.model(), idx.row()):
                    enableDelete = False
                    break

        self.ui.schemaCreateTablesColumnTable.addBtn().setEnabled(enableAdd)
        self.ui.schemaCreateTablesColumnTable.deleteBtn().setEnabled(enableDelete)
        self.ui.schemaCreateTablesColumnTable.clearAllBtn().setEnabled(enableClearAll)