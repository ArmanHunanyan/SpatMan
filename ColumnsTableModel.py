
from PyQt5.QtCore import QModelIndex
from PyQt5.QtCore import Qt
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QVariant
from PyQt5.QtGui import QPixmap
from PyQt5.QtGui import QColor

from TableInfo import TableInfo

def ColumnsTableModelFactory(baseClass):

    class ColumnsTableValidators(baseClass):
        columns = ("Name", "Description", "Type", "Size", "Scale", "Units", "Default Value", "Lookup Table", "Range Maximum", "Range Minimum", "Primary Key", "Allow Nulls")
        modified = pyqtSignal(bool)
        def __init__(self, *args):
            super(ColumnsTableValidators, self).__init__(*args)
            self.m_commitAfterChange = False
            self.m_keyEditable = False

        def setPrimaryKeyEditable(self, ed):
            self.m_keyEditable = ed

        def setCommitAfterChange(self, val):
            self.m_commitAfterChange = val

        def initValidators(self, visibleColIndices):
            self.m_visibleColIndices = visibleColIndices
            self.setColumnValidator(self.mapColumn(0), self.validateName)
            self.setColumnValidator(self.mapColumn(2), self.validateType)
            self.setColumnValidator(self.mapColumn(3), self.validateSize)
            self.setColumnValidator(self.mapColumn(6), self.validateDefault)
            self.setColumnValidator(self.mapColumn(10), self.validatePrimaryKey)
            self.setColumnEditableProc(self.mapColumn(3), self.isSizeEditable)
            self.setColumnEditableProc(self.mapColumn(4), self.isScaleEditable)
            self.setColumnEditableProc(self.mapColumn(10), self.isPrimaryKeyEditable)
            self.setColumnEditableProc(self.mapColumn(11), self.isAllowNullsEditable)
            self.setColumnCallback(self.mapColumn(2), self.typeCallback)
            self.setEditableProc(self.isNotFrozen)

        def isPrimaryKeyEditable(self, model, row, name):
            return self.m_keyEditable

        def isAllowNullsEditable(self, model, row, name):
            return True

        def isNotFrozen(self, model, row):
            return not self.m_data[row].frozen()

        def deleteAll(self):
            self.modelAboutToBeReset.emit()
            self.m_data = []
            self.m_modified = False
            self.modelReset.emit()
            self.modified.emit(self.m_modified)

        def deleteUnfrozenColumns(self):
            self.modelAboutToBeReset.emit()
            idx = 0
            while (idx < len(self.m_data)):
                if self.isNotFrozen(self, idx):
                    self.rowsAboutToBeRemoved.emit(QModelIndex(), idx, idx)
                    del self.m_data[idx]
                    self.rowsRemoved.emit(QModelIndex(), idx, idx)
                else:
                    idx += 1

            self.m_modified = False
            self.modelReset.emit()
            self.modified.emit(self.m_modified)

        def headerData(self, section, orientation, role):
            if role == Qt.DisplayRole and orientation == Qt.Horizontal:
                return self.columns[section]
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

            return super(ColumnsTableValidators, self).headerData(section, orientation, role)

        def isValid(self):
            for row in range(self.rowCount()):
                for col in range(self.columnCount()):
                    if not self.validate(row, col, self.data(self.createIndex(row, col), Qt.EditRole)):
                        return False
            return True

        def rowCount(self, parent=None):
            return len(self.m_data)

        def columnCount(self, parent=None):
            return len(self.columns)

        def commitChanges(self):
            idx = 0
            while (idx < len(self.m_data)):
                if self.isNotFrozen(self, idx):
                    if self.m_data[idx].added():
                        self.m_data[idx].commitChanges()
                        idx += 1
                    elif self.m_data[idx].deleted():
                        self.rowsAboutToBeRemoved.emit(QModelIndex(), idx, idx)
                        del self.m_data[idx]
                        self.rowsRemoved.emit(QModelIndex(), idx, idx)
                    else:
                        idx += 1
                else:
                    idx += 1
            self.m_modified = False
            self.modified.emit(self.m_modified)

        def addRow(self, idx):
            row = TableInfo(0, False)
            row.setAdded()
            row.resize(len(self.columns))
            row.value(10).modifiedValue = "No"
            row.value(10).originalValue = "No"
            row.value(11).modifiedValue = "Yes"
            row.value(11).originalValue = "Yes"
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

        def takeRow(self, idx):
            self.rowsAboutToBeRemoved.emit(QModelIndex(), idx, idx)
            res = self.m_data[idx]
            del self.m_data[idx]
            self.rowsRemoved.emit(QModelIndex(), idx, idx)
            return res

        def insertRow(self, idx, row):
            self.rowsAboutToBeInserted.emit(QModelIndex(), idx, idx)
            self.m_data.insert(idx, row)
            self.m_modified = True
            self.rowsInserted.emit(QModelIndex(), idx, idx)
            self.modified.emit(self.m_modified)
            if self.m_commitAfterChange:
                self.commitChanges()

        def rowIsModified(self, row):
            for col in range(self.columnCount()):
                if self.m_data[row].isModified(col):
                    return True
            return False

        def keyDropped(self, row):
            if self.m_data[row].value(10).originalValue == "Yes" and \
                self.m_data[row].value(10).modifiedValue == "No":
                    return True
            return False

        def cellIsMidified(self, row, col):
            return self.m_data[row].isModified(col)

        def cell(self, row, col):
            return self.m_data[row].value(col)

        def isModified(self):
            return self.m_modified

        def keyColumn(self):
            for row in self.m_data:
                if row.value(10).modifiedValue == "Yes":
                    return row

            return None

        def dropPrimaryKey(self):
            for row in self.m_data:
                if row.value(10).modifiedValue == "Yes":
                    row.setValue(10, "No")

        def data(self, index, role):
            if role == Qt.BackgroundColorRole:
                if self.m_data[index.row()].frozen():
                    return QColor(200, 200, 200)

            if role == Qt.DisplayRole or role == Qt.EditRole:
                return self.m_data[index.row()].displayValue(index.column())
            return super(ColumnsTableValidators, self).data(index, role)

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

            return super(ColumnsTableValidators, self).setData(index, value, role)

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

        def mapColumn(self, idx):
            if self.m_visibleColIndices is None:
                return idx
            else:
                return self.m_visibleColIndices[idx]

        def typeCallback(self, model, row, type):
            if type == "integer":
                self.setData(self.createIndex(row, self.mapColumn(3), QModelIndex()), "32", Qt.EditRole)
            elif type == "bigint":
                self.setData(self.createIndex(row, self.mapColumn(3), QModelIndex()), "64", Qt.EditRole)
            elif type == "smallint":
                self.setData(self.createIndex(row, self.mapColumn(3), QModelIndex()), "16", Qt.EditRole)
            elif type == "date":
                self.setData(self.createIndex(row, self.mapColumn(3), QModelIndex()), "", Qt.EditRole)
            elif type == "varchar":
                self.setData(self.createIndex(row, self.mapColumn(3), QModelIndex()), "", Qt.EditRole)
            elif type == "real":
                self.setData(self.createIndex(row, self.mapColumn(3), QModelIndex()), "24", Qt.EditRole)
            elif type == "double precision":
                self.setData(self.createIndex(row, self.mapColumn(3), QModelIndex()), "53", Qt.EditRole)
            elif type == "numeric" or type == "decimal":
                self.setData(self.createIndex(row, self.mapColumn(3), QModelIndex()), "", Qt.EditRole)
                self.setData(self.createIndex(row, self.mapColumn(4), QModelIndex()), "", Qt.EditRole)

        def validateName(self, model, row, name):
            if name is None:
                return False
            if len(name) == 0:
                return False

            if self.m_data[row].deleted():
                return True

            for idx in range(model.rowCount()):
                if idx != row and not self.m_data[idx].deleted() and model.value(idx, self.mapColumn(0)).lower() == name.lower():
                    return False

            return True

        def validatePrimaryKey(self, model, row, name):
            if self.m_data[row].deleted():
                return True

            if model.value(row, self.mapColumn(10)) == "No":
                return True

            for idx in range(model.rowCount()):
                if idx != row and not self.m_data[idx].deleted() and model.value(idx, self.mapColumn(10)) == "Yes":
                    return False

            return True

        def validateType(self, model, row, name):
            if name is None:
                return False
            if len(name) == 0:
                return False

            return True

        def validateSize(self, model, row, val):
            return True

        def validateDefault(self, model, row, val):
            if val is None or val == "":
                return True
            if str(val).startswith("nextval"):
                return True
            type = model.value(row, self.mapColumn(2))
            if type in ["smallint", "integer", "bigint"]:
                try:
                    int(val)
                    return True
                except:
                    return False
            elif type in ["real", "double precision", "numeric", "decimal"]:
                try:
                    float(val)
                    return True
                except:
                    return False
            return True

        def isSizeEditable(self, model, row, name):
            return model.value(row, self.mapColumn(2)) in ["varchar", "char", "character varying", "character", "numeric", "decimal"]

        def isScaleEditable(self, model, row, name):
            return model.value(row, self.mapColumn(2)) in ["numeric", "decimal"]

    return ColumnsTableValidators
