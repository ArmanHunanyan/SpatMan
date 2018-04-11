
from PyQt5.QtCore import QObject
from PyQt5.QtCore import QItemSelectionModel
from PyQt5.QtWidgets import QAbstractItemView
from PyQt5.QtWidgets import QMenu
from PyQt5.QtCore import QAbstractTableModel
from PyQt5.QtCore import QModelIndex
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QVariant
from PyQt5.QtGui import QPixmap

from ComboboxDelegate import ComboDelegate
from TableListWithFiltersController import TableListWithFiltersController
from TableInfo import TableInfo

class TableTableModel(QAbstractTableModel):

    columns = ("Table Name", "Group", "Title", "Description", "Is Spatial", "Spatial Type", "Schema")
    modified = pyqtSignal(bool)

    def __init__(self, database, connId):
        super(TableTableModel, self).__init__()

        self.m_data = []
        self.m_database = database
        self.m_modified = False
        self.m_connId = connId

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return TableTableModel.columns[section]
        if role == Qt.DecorationRole and orientation == Qt.Vertical:
            if self.m_data[section].local():
                return QVariant(QPixmap(":/icons/local.png").scaled(16, 16))

    def rowCount(self, parent=None):
        return len(self.m_data)

    def columnCount(self, parent=None):
        return len(TableTableModel.columns)

    def insertInfo(self, row, tableName, schema):
        self.rowsAboutToBeInserted.emit(QModelIndex(), row, row)

        local, tableName, group, title, description, isSpatial, spatialType, schema = self.m_database.tableInfo(schema, self.m_connId, tableName)
        info = TableInfo(0, local, tableName, group, title,
                         description, "Yes" if isSpatial else 'No',
                         spatialType if isSpatial else "", schema)

        self.m_data.insert(row, info)

        self.rowsInserted.emit(QModelIndex(), row, row)

    def rowIsModified(self, row):
        for col in range(self.columnCount()):
            if self.m_data[row].isModified(col):
                return True
        return False

    def cellIsMidified(self, row, col):
        return self.m_data[row].isModified(col)

    def cell(self, row, col):
        return self.m_data[row].value(col)

    def isModified(self):
        return self.m_modified

    def data(self, index, role):
        if role == Qt.BackgroundRole and self.m_data[index.row()].isModified(index.column()):
            return QColor(255, 165, 0)
        if role == Qt.DisplayRole or role == Qt.EditRole:
            return self.m_data[index.row()].displayValue(index.column())

        return None

    def setData(self, index, value, role):
        if role == Qt.DisplayRole or role == Qt.EditRole:
            if self.m_data[index.row()].setValue(index.column(), value):
                self.dataChanged.emit(index, index)
                if not self.m_modified and self.m_data[index.row()].isModified(index.column()):
                    self.m_modified = True
                    self.modified.emit(self.m_modified)
                elif self.m_modified:
                    isMod = False
                    for idx in range(self.rowCount()):
                        if self.rowIsModified(idx):
                            isMod = True
                            break
                    if not isMod:
                        self.m_modified = False
                        self.modified.emit(self.m_modified)

        return True

    def flags(self, index):
        if index.column() in (0, 1, 2, 3):
            return super(QAbstractTableModel, self).flags(index) | Qt.ItemIsEditable
        return super(QAbstractTableModel, self).flags(index)


    def deleteInfo(self, row):
        self.rowsAboutToBeRemoved.emit(QModelIndex(), row, row)
        del self.m_data[row]
        self.rowsRemoved.emit(QModelIndex(), row, row)

        # Update modified
        if self.m_modified:
            isMod = False
            for idx in range(self.rowCount()):
                if self.rowIsModified(idx):
                    isMod = True
                    break
            if not isMod:
                self.m_modified = False
                self.modified.emit(self.m_modified)

    def reset(self):
        self.modelAboutToBeReset.emit()
        for row in range(self.rowCount()):
            self.m_data[row].reset()
        self.m_modified = False
        self.modelReset.emit()
        self.modified.emit(self.m_modified)


    def insertInfo(self, row, tableName, schema):
        self.rowsAboutToBeInserted.emit(QModelIndex(), row, row)

        local, tableName, group, title, description, isSpatial, spatialType, schema = self.m_database.tableInfo(schema, self.m_connId, tableName)
        info = TableInfo(0, local, tableName, group, title,
                         description, "Yes" if isSpatial else 'No',
                         spatialType if isSpatial else "", schema)

        self.m_data.insert(row, info)

        self.rowsInserted.emit(QModelIndex(), row, row)

    def save(self):
        try:
            self.modelAboutToBeReset.emit()
            for row in range(self.rowCount()):
                if self.rowIsModified(row):
                    self.m_database.saveTable(tableName=self.m_data[row].value(0),
                                          group=self.m_data[row].value(1),
                                          title=self.m_data[row].value(2),
                                          description=self.m_data[row].value(3),
                                          isSpatial=self.m_data[row].value(4),
                                          spatialType=self.m_data[row].value(5),
                                          schema=self.m_data[row].value(6),
                                          connId=self.m_connId)
                    self.m_data[row].commitChanges()
                    local, tableName, group, title, description, isSpatial, spatialType, schema = \
                        self.m_database.tableInfo(schema=self.m_data[row].value(6).originalValue,
                                                  connId=self.m_connId,
                                                  tableName=self.m_data[row].value(0).originalValue)
                    self.m_data[row] = TableInfo(0, local, tableName, group, title,
                         description, "Yes" if isSpatial else 'No',
                         spatialType if isSpatial else "", schema)
            self.m_modified = False
            self.modelReset.emit()
            self.modified.emit(self.m_modified)
        except Exception as e:
            print(e)

class SchemasManageTablesController(QObject):
    def __init__(self, ui, database, schema, connId):
        super(SchemasManageTablesController, self).__init__()
        self.ui = ui
        self.m_database = database
        self.m_schema = schema
        self.m_connId = connId
        self.m_visibleIndices = []

        self.ui.manageTablesListWidget.setSelectionMode(QAbstractItemView.MultiSelection)

        self.m_tableListWithFilterController = TableListWithFiltersController(self.m_database, self.m_schema, self.m_connId,
                        self.ui.manageTablesListWidget, self.ui.manageTablesFilterEdit, self.ui.manageTablesFilterBtn,
                                        lambda idx : self.ui.manageTablesTableView.model().rowIsModified(idx),
                                        lambda db, schema, connId : db.schemaTableList(schema))
        self.m_tableListWithFilterController.selectTableNameSignal.connect(self.tableSelected)
        self.m_tableListWithFilterController.deselectTableNameSignal.connect(self.tableDeselected)

        self.ui.manageTablesTableView.setModel(TableTableModel(self.m_database, self.m_connId))
        self.ui.manageTablesTableView.model().modified.connect(self.updateSaveResetBtnsState)
        self.updateGroups()
        self.m_database.schemaGroupListChangedSignal.connect(self.updateGroups)
        self.updateSaveResetBtnsState()

        self.ui.manageTablesResetBtn.pressed.connect(self.resetPressed)
        self.ui.manageTablesSaveBtn.pressed.connect(self.savePressed)

        self.ui.manageTablesListWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.manageTablesListWidget.customContextMenuRequested.connect(self.tableListContextMenu)


    def tableListContextMenu(self, point):
        globalPos = self.ui.manageTablesListWidget.mapToGlobal(point)
        self.m_contextMenuItem = self.ui.manageTablesListWidget.itemAt(point)
        menu = QMenu()
        menu.addAction("Delete", self.deleteCurrentTable)
        menu.exec(globalPos)

    def deleteCurrentTable(self):
        tableName = self.m_contextMenuItem.text()

        res = QMessageBox.question(None, 'Delete Table?',
                                   "Delete table '%s.%s' and all associated information? \n" % (self.m_schema, tableName),
                                   QMessageBox.Yes, QMessageBox.No)
        if res == QMessageBox.No:
            return

        try:
            idx = self.m_tableListWithFilterController.tables().index(tableName)
        except Exception as e:
            return

        self.m_database.deleteTableAndInfo(self.m_schema, self.m_connId, tableName)

    def updateGroups(self):
        self.ui.schemaCreateTablesGroupCombo.clear()
        delegate = ComboDelegate(['FromDB'] + self.m_database.schemaGroupList(self.m_connId),
                                 self.ui.manageTablesTableView)
        self.ui.manageTablesTableView.setItemDelegateForColumn(1, delegate)

        sel = self.ui.manageTablesListWidget.selectionModel().selection()
        self.ui.manageTablesListWidget.selectionModel().clearSelection()
        self.ui.manageTablesListWidget.selectionModel().select(sel, QItemSelectionModel.Select)

    def resetPressed(self):
        self.ui.manageTablesTableView.model().reset()

    def savePressed(self):
        msg = ""
        for row in range(self.ui.manageTablesTableView.model().rowCount()):
            if self.ui.manageTablesTableView.model().cellIsMidified(row, 0):
                msg += self.ui.manageTablesTableView.model().cell(row, 0).originalValue + " to " + \
                        self.ui.manageTablesTableView.model().cell(row, 0).modifiedValue + "\n"

        if len(msg) != 0:
            res = QMessageBox.question(None, 'Rename Tables?',
                                       "Are you sure to rename following tables?\n" + msg,
                                       QMessageBox.Yes, QMessageBox.No)
            if res == QMessageBox.No:
                return

        self.ui.manageTablesTableView.model().save()
        self.m_tableListWithFilterController.filterRenamedTables()

    def updateSaveResetBtnsState(self):
        modified = self.ui.manageTablesTableView.model().isModified()
        self.ui.manageTablesResetBtn.setEnabled(modified)
        self.ui.manageTablesSaveBtn.setEnabled(modified)

    def tableSelected(self, row, tableName):
        self.ui.manageTablesTableView.model().insertInfo(row, tableName, self.m_schema)

    def tableDeselected(self, row, tableName):
        self.ui.manageTablesTableView.model().deleteInfo(row)