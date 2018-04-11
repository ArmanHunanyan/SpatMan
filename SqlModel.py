
from PyQt5.QtCore import QModelIndex
from PyQt5.QtCore import Qt
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QVariant
from PyQt5.QtGui import QPixmap
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QMessageBox

from TableInfo import TableInfo

def SqlModelFactory(baseClass):
    class SqlModel(baseClass):
        modified = pyqtSignal(bool)

        def __init__(self, *args):
            super(SqlModel, self).__init__(*args)
            self.m_commitAfterChange = False

        def fetchData(self):
            self.modelAboutToBeReset.emit()

            self.fetchDataImpl()

            self.m_modified = False
            self.modelReset.emit()
            self.modified.emit(self.m_modified)

        def save(self):
            error = False
            self.modelAboutToBeReset.emit()
            for row in range(self.rowCount()):
                if self.rowIsModified(row):
                    try:
                        self.saveRowImpl(self.m_data[row])
                    except Exception as e:
                        QMessageBox.warning(None, "Failed", str(e))
                        error = True
            if not error:
                self.fetchData()
                self.m_modified = False
            self.modelReset.emit()
            if not error:
                self.modified.emit(self.m_modified)

        def setCommitAfterChange(self, val):
            self.m_commitAfterChange = val

        def initValidators(self, visibleColIndices):
             self.m_visibleColIndices = visibleColIndices
             self.setEditableProc(self.isNotFrozen)

        def isNotFrozen(self, model, row):
             return not self.m_data[row].frozen()
        #
        # def deleteAll(self):
        #     self.modelAboutToBeReset.emit()
        #     self.m_data = []
        #     self.m_modified = False
        #     self.modelReset.emit()
        #     self.modified.emit(self.m_modified)
        #
        # def deleteUnfrozenColumns(self):
        #     self.modelAboutToBeReset.emit()
        #     idx = 0
        #     while (idx < len(self.m_data)):
        #         if self.isNotFrozen(self, idx):
        #             self.rowsAboutToBeRemoved.emit(QModelIndex(), idx, idx)
        #             del self.m_data[idx]
        #             self.rowsRemoved.emit(QModelIndex(), idx, idx)
        #         else:
        #             idx += 1
        #
        #     self.m_modified = False
        #     self.modelReset.emit()
        #     self.modified.emit(self.m_modified)

        def headerData(self, section, orientation, role):
            if role == Qt.DisplayRole and orientation == Qt.Horizontal:
                return self.m_columns[section]
            elif role == Qt.DisplayRole and orientation == Qt.Vertical:
                if self.m_data[section].added():
                    return "*"
                elif self.m_data[section].deleted():
                    return "!"
                else:
                    return str(section)

            if role == Qt.DecorationRole and orientation == Qt.Vertical:
                if section < len(self.m_data) and self.m_data[section].frozen():
                    return QVariant(QPixmap(":/icons/lock.png").scaled(13, 13))

            return super(SqlModel, self).headerData(section, orientation, role)
        #
        # def isValid(self):
        #     for row in range(self.rowCount()):
        #         for col in range(self.columnCount()):
        #             if not self.validate(row, col, self.data(self.createIndex(row, col), Qt.EditRole)):
        #                 return False
        #     return True
        #
        def rowCount(self, parent=None):
            return len(self.m_data)

        def columnCount(self, parent=None):
            return len(self.m_columns)
        #
        # def commitChanges(self):
        #     idx = 0
        #     while (idx < len(self.m_data)):
        #         if self.isNotFrozen(self, idx):
        #             if self.m_data[idx].added():
        #                 self.m_data[idx].commitChanges()
        #                 idx += 1
        #             elif self.m_data[idx].deleted():
        #                 self.rowsAboutToBeRemoved.emit(QModelIndex(), idx, idx)
        #                 del self.m_data[idx]
        #                 self.rowsRemoved.emit(QModelIndex(), idx, idx)
        #             else:
        #                 idx += 1
        #         else:
        #             idx += 1
        #     self.m_modified = False
        #     self.modified.emit(self.m_modified)
        #
        def addRow(self, idx):
            row = TableInfo(0, False)
            row.setAdded()
            row.resize(len(self.m_columns))
            self.rowsAboutToBeInserted.emit(QModelIndex(), idx, idx)
            self.m_data.insert(idx, row)
            self.rowsInserted.emit(QModelIndex(), idx, idx)
            self.m_modified = True
            self.modified.emit(self.m_modified)
            if self.m_commitAfterChange:
                self.commitChanges()


        def deleteRows(self, ids):
            self.modelAboutToBeReset.emit()
            for row in ids:
                self.m_data[row].setDeleted()
            self.m_modified = True
            self.modelReset.emit()
            self.modified.emit(self.m_modified)
            if self.m_commitAfterChange:
                self.commitChanges()
        #
        # def takeRow(self, idx):
        #     self.rowsAboutToBeRemoved.emit(QModelIndex(), idx, idx)
        #     res = self.m_data[idx]
        #     del self.m_data[idx]
        #     self.rowsRemoved.emit(QModelIndex(), idx, idx)
        #     return res
        #
        # def insertRow(self, idx, row):
        #     self.rowsAboutToBeInserted.emit(QModelIndex(), idx, idx)
        #     self.m_data.insert(idx, row)
        #     self.m_modified = True
        #     self.rowsInserted.emit(QModelIndex(), idx, idx)
        #     self.modified.emit(self.m_modified)
        #     if self.m_commitAfterChange:
        #         self.commitChanges()
        #
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
            if role == Qt.BackgroundColorRole:
                if self.m_data[index.row()].frozen():
                    return QColor(200, 200, 200)

            if role == Qt.DisplayRole or role == Qt.EditRole:
                return self.m_data[index.row()].displayValue(index.column())
            return super(SqlModel, self).data(index, role)

        def isDirty(self, index):
             return self.m_data[index.row()].isModified(index.column())

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
                if self.m_commitAfterChange:
                    self.m_data[index.row()].commitChanges()
            return super(SqlModel, self).setData(index, value, role)

        def reset(self):
            self.modelAboutToBeReset.emit()
            row = 0
            while row < self.rowCount():
                if self.m_data[row].added():
                    del self.m_data[row]
                else:
                    self.m_data[row].reset()
                    row += 1
            self.m_modified = False
            self.modelReset.emit()
            self.modified.emit(self.m_modified)

    return SqlModel
