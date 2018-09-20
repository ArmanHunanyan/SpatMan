
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QLayout
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QPlainTextEdit
from PyQt5.QtWidgets import QComboBox
from PyQt5.QtWidgets import QGridLayout
from PyQt5.QtWidgets import QSpacerItem
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtCore import QObject
from PyQt5.QtCore import QSize
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
from PyQt5.QtGui import QIcon
import tempfile
import uuid
import shutil
import xml.etree.ElementTree as et
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebEngineWidgets import QWebEngineSettings
from PyQt5.QtCore import QUrl
from PyQt5.QtCore import QTimer
import bs4
from ModelWithValidators import ModelWithValidatorsFactory
from DBTableModel import DataChangeMarkerModelFactory
from DBTableModel import AddDeleteMarkerModelFactory

from Configuration import Configuration
from GeoJSONParser import parseGeoJSON, GeoJSONVisitor

class JoinItem:
    def __init__(self, joinType, tableFrom, columnFrom, tableTo, columnTo, where):
        self.joinType = joinType
        self.tableFrom = tableFrom
        self.columnFrom = columnFrom
        self.tableTo = tableTo
        self.columnTo = columnTo
        self.where = where

    def __eq__(self, other):
        return self.joinType == other.joinType and \
               self.tableFrom == other.tableFrom and \
               self.columnFrom == other.columnFrom and \
               self.tableTo == other.tableTo and \
               self.columnTo == other.columnTo and \
               self.where == other.where

    def noneToStr(str):
        if str is None:
            return "none"
        else:
            return str

    def __hash__(self):
        return hash(self.joinType + self.tableFrom + __class__.noneToStr(self.columnFrom) \
                    + self.tableTo + __class__.noneToStr(self.columnTo) + __class__.noneToStr(self.where))

class RuntimeJoinItem:
    def __init__(self, joinItem):
        self.original = joinItem
        self.modified = joinItem
        self.validity = None
        self.added = False
        self.deleted = False

class JoinsModel(QAbstractTableModel):

    _columns = ("From Table", "From Column", "To Table", "To Column", "Custom Join")
    rowCountChanged = pyqtSignal()

    def __init__(self, connId, schema, database):
        super(JoinsModel, self).__init__()

        self.m_joins = []
        self.m_connId = connId
        self.m_schema = schema
        self.m_database = database

    def loadData(self):
        # TODO loadData and save need to be implemented here to make this tab working
        self.m_database.joinList(JoinItem, self.m_connId)

    # Methods for derived classes
    def columns(self):
        return __class__._columns

    def rows(self):
        return self.m_joins

    def rowIsAdded(self, idx):
        return self.m_joins[idx].added

    def rowIsDeleted(self, idx):
        return self.m_joins[idx].deleted

    def cellIsValid(self, index):
        return True

    def cellIsModified(self, index):
        if self.m_joins[index.row()].added:
            return False
        if index.column() == 0:
            return self.m_joins[index.row()].modified.tableFrom != self.m_joins[index.row()].original.tableFrom
        elif index.column() == 1:
            return self.m_joins[index.row()].modified.columnFrom != self.m_joins[index.row()].original.columnFrom
        elif index.column() == 2:
            return self.m_joins[index.row()].modified.tableTo != self.m_joins[index.row()].original.tableTo
        elif index.column() == 3:
            return self.m_joins[index.row()].modified.columnTo != self.m_joins[index.row()].original.columnTo
        elif index.column() == 4:
            return self.m_joins[index.row()].modified.joinType != self.m_joins[index.row()].original.joinType

    # Implementation
    def insertJoin(self, row, join):
        self.rowsAboutToBeInserted.emit(QModelIndex(), row, row)
        self.m_joins.insert(row, join)
        self.rowsInserted.emit(QModelIndex(), row, row)
        self.rowCountChanged.emit()

    def setJoin(self, row, join):
        self.m_joins[row] = join
        self.dataChanged.emit(self.createIndex(row, 0),
                              self.createIndex(row, len(self.columns()) - 1))

    def join(self, idx):
        return self.m_joins[idx]

    def data(self, index, role):
        if role == Qt.DisplayRole:
            if index.column() == 0:
                return self.m_joins[index.row()].modified.tableFrom
            elif index.column() == 1:
                return self.m_joins[index.row()].modified.columnFrom
            elif index.column() == 2:
                return self.m_joins[index.row()].modified.tableTo
            elif index.column() == 3:
                return self.m_joins[index.row()].modified.columnTo
            elif index.column() == 4:
                return self.m_joins[index.row()].modified.joinType
        return None

    def deleteJoin(self, row):
        self.rowsAboutToBeRemoved.emit(QModelIndex(), row, row)
        del self.m_joins[row]
        self.rowsRemoved.emit(QModelIndex(), row, row)
        self.rowCountChanged.emit()

    def reset(self):
        self.modelAboutToBeReset.emit()
        for join in self.m_joins:
            join.modified = join.original
        self.modelReset.emit()

    def save(self):
        self.modelAboutToBeReset.emit()
        for join in self.m_joins:
            join.modified = join.original
        self.modelReset.emit()

class EditJoinWidget(QDialog):

    def __init__(self, parent, database, connId, schema, join):
        super(EditJoinWidget, self).__init__(parent)

        self.m_database = database
        self.m_connId = connId
        self.m_schema = schema
        self.m_join = join

        self.resize(499, 351)
        self.m_verticalLayout = QVBoxLayout(self)
        self.m_gridLayout = QGridLayout()
        self.m_gridLayout.setSizeConstraint(QLayout.SetMinimumSize)
        self.m_toTableLabel = QLabel(self)
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.m_toTableLabel.sizePolicy().hasHeightForWidth())
        self.m_toTableLabel.setSizePolicy(sizePolicy)
        self.m_gridLayout.addWidget(self.m_toTableLabel, 4, 0, 1, 1)
        self.m_fromColumnLabel = QLabel(self)
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.m_fromColumnLabel.sizePolicy().hasHeightForWidth())
        self.m_fromColumnLabel.setSizePolicy(sizePolicy)
        self.m_gridLayout.addWidget(self.m_fromColumnLabel, 3, 0, 1, 1)
        self.m_typeLabel = QLabel(self)
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.m_typeLabel.sizePolicy().hasHeightForWidth())
        self.m_typeLabel.setSizePolicy(sizePolicy)
        self.m_gridLayout.addWidget(self.m_typeLabel, 0, 0, 1, 1)
        self.m_fromTableLabel = QLabel()
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.m_fromTableLabel.sizePolicy().hasHeightForWidth())
        self.m_fromTableLabel.setSizePolicy(sizePolicy)
        self.m_gridLayout.addWidget(self.m_fromTableLabel, 2, 0, 1, 1)
        self.m_toColumnLabel = QLabel(self)
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.m_toColumnLabel.sizePolicy().hasHeightForWidth())
        self.m_toColumnLabel.setSizePolicy(sizePolicy)
        self.m_gridLayout.addWidget(self.m_toColumnLabel, 5, 0, 1, 1)
        self.m_whereLabel = QLabel(self)
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.m_whereLabel.sizePolicy().hasHeightForWidth())
        self.m_whereLabel.setSizePolicy(sizePolicy)
        self.m_whereLabel.setAlignment(Qt.AlignLeading | Qt.AlignLeft | Qt.AlignTop)
        self.m_gridLayout.addWidget(self.m_whereLabel, 1, 0, 1, 1)
        self.m_whereEdit = QPlainTextEdit(self)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.m_whereEdit.sizePolicy().hasHeightForWidth())
        self.m_whereEdit.setSizePolicy(sizePolicy)
        self.m_whereEdit.setMinimumSize(QSize(0, 100))
        self.m_whereEdit.setMaximumSize(QSize(16777215, 100))
        self.m_gridLayout.addWidget(self.m_whereEdit, 1, 1, 1, 2)
        self.m_typeCombo = QComboBox(self)
        self.m_typeCombo.addItem("Inner Join")
        self.m_typeCombo.addItem("Outer Join")
        self.m_typeCombo.addItem("Left Join")
        self.m_typeCombo.addItem("Right Join")
        self.m_typeCombo.addItem("Custom Join")
        self.m_gridLayout.addWidget(self.m_typeCombo, 0, 1, 1, 1)
        self.m_fromTableCombo = QComboBox()
        self.m_fromTableCombo.setMinimumSize(QSize(150, 0))
        self.m_gridLayout.addWidget(self.m_fromTableCombo, 2, 1, 1, 1)
        self.m_fromColumnCombo = QComboBox(self)
        self.m_gridLayout.addWidget(self.m_fromColumnCombo, 3, 1, 1, 1)
        self.m_toTableCombo = QComboBox(self)
        self.m_gridLayout.addWidget(self.m_toTableCombo, 4, 1, 1, 1)
        self.m_toColumnCombo = QComboBox(self)
        self.m_toColumnCombo.setObjectName("m_toColumnCombo")
        self.m_gridLayout.addWidget(self.m_toColumnCombo, 5, 1, 1, 1)
        self.m_gridLayout.setColumnStretch(0, 1)
        self.m_gridLayout.setColumnStretch(1, 2)
        self.m_gridLayout.setColumnStretch(2, 6)
        self.m_verticalLayout.addLayout(self.m_gridLayout)
        spacerItem = QSpacerItem(20, 61, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.m_verticalLayout.addItem(spacerItem)
        self.m_buttonLayout = QHBoxLayout()
        spacerItem1 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.m_buttonLayout.addItem(spacerItem1)
        self.m_validateButton = QPushButton(self)
        self.m_buttonLayout.addWidget(self.m_validateButton)
        self.m_OKButton = QPushButton(self)
        self.m_buttonLayout.addWidget(self.m_OKButton)
        self.m_cancelButton = QPushButton(self)
        self.m_buttonLayout.addWidget(self.m_cancelButton)
        self.m_verticalLayout.addLayout(self.m_buttonLayout)

        self.setWindowTitle("Edit Join")
        self.m_toTableLabel.setText("To Table")
        self.m_fromColumnLabel.setText("From Column")
        self.m_typeLabel.setText("Type")
        self.m_fromTableLabel.setText("From Table")
        self.m_toColumnLabel.setText("To Column")
        self.m_whereLabel.setText("Where")
        self.m_validateButton.setText("Validate")
        self.m_OKButton.setText("OK")
        self.m_cancelButton.setText("Cancel")
        self.setWindowTitle("Edit Join")

        self.m_fromTableCombo.currentIndexChanged.connect(self.fromTableChanged)
        self.m_toTableCombo.currentIndexChanged.connect(self.toTableChanged)
        self.fillTables()
        self.fromTableChanged()
        self.toTableChanged()

        self.m_validity = None
        if join is not None:
            self.m_typeCombo.setCurrentText(join.modified.joinType)
            self.m_fromTableCombo.setCurrentText(join.modified.tableFrom)
            self.m_toTableCombo.setCurrentText(join.modified.tableTo)
            if join.modified.joinType == "Custom Join":
                self.m_whereEdit.setPlainText(join.modified.where)
            else:
                self.m_fromColumnCombo.setCurrentText(join.modified.columnFrom)
                self.m_toColumnCombo.setCurrentText(join.modified.columnTo)
            self.m_validity = join.validity

        self.m_typeCombo.currentTextChanged.connect(self.typeChanged)
        self.typeChanged()

        self.m_validSets = set()
        self.m_invalidSets = set()
        self.updateValiditySet()
        self.updateValidity()

        self.m_validateButton.pressed.connect(self.validatePressed)

        self.m_typeCombo.currentIndexChanged.connect(self.updateValidity)
        self.m_fromTableCombo.currentIndexChanged.connect(self.updateValidity)
        self.m_fromColumnCombo.currentIndexChanged.connect(self.updateValidity)
        self.m_toTableCombo.currentIndexChanged.connect(self.updateValidity)
        self.m_toColumnCombo.currentIndexChanged.connect(self.updateValidity)
        self.m_whereEdit.textChanged.connect(self.updateValidity)

        self.m_OKButton.pressed.connect(self.accept)
        self.m_cancelButton.pressed.connect(self.reject)

    def fillTables(self):
        tables = self.m_database.localDatabase().localTableList(self.m_connId, False)
        self.m_fromTableCombo.addItems(tables)
        self.m_toTableCombo.addItems(tables)

    def fromTableChanged(self):
        if self.m_fromTableCombo.currentText() == "":
            self.m_fromColumnCombo.setDisabled(True)
        else:
            self.m_fromColumnCombo.setDisabled(False)

        columnInfo = self.m_database.localDatabase().columnInfoByTable(self.m_fromTableCombo.currentText())
        self.m_fromColumnCombo.clear()
        self.m_fromColumnCombo.addItems(list([col_name for col_name, col_desc, col_type, col_size, col_scale, \
            col_units, default_value, lu_table, column_maxval, \
            column_minval, is_primary_key, nullok in columnInfo]))

    def toTableChanged(self):
        if self.m_toTableCombo.currentText() == "":
            self.m_toColumnCombo.setDisabled(True)
        else:
            self.m_toColumnCombo.setDisabled(False)

        columnInfo = self.m_database.localDatabase().columnInfoByTable(self.m_toTableCombo.currentText())
        self.m_toColumnCombo.clear()
        self.m_toColumnCombo.addItems(list([col_name for col_name, col_desc, col_type, col_size, col_scale, \
            col_units, default_value, lu_table, column_maxval, \
            column_minval, is_primary_key, nullok in columnInfo]))

    def validatePressed(self):
        try:
            valid = self.m_database.validateJoin(self.currentJoinItem(), self.m_schema)
        except Exception as e:
            QMessageBox.warning(None, "Failed", str(e))
            return

        if valid:
            self.m_validity = "valid"
        else:
            self.m_validity = "invalid"
        self.updateValiditySet()
        self.updateValidity()

    def updateValidity(self):
        join = self.currentJoinItem()
        if join in self.m_validSets:
            self.m_OKButton.setEnabled(True)
            self.m_validateButton.setIcon(QIcon(":/icons/correct.png"))
        else:
            self.m_OKButton.setEnabled(False)
            if join not in self.m_invalidSets:
                self.m_validateButton.setIcon(QIcon())
            else:
                self.m_validateButton.setIcon(QIcon(":/icons/incorrect.png"))

    def updateValiditySet(self):
        if self.m_validity is None:
            return

        if self.m_validity == "valid":
            self.m_validSets.add(self.currentJoinItem())
        elif self.m_validity == "invalid":
            self.m_invalidSets.add(self.currentJoinItem())
        else:
            assert False

    def typeChanged(self):
        if self.m_typeCombo.currentText() == "Custom Join":
            showCustom = True
        else:
            showCustom = False

        self.m_whereEdit.setVisible(showCustom)
        self.m_whereLabel.setVisible(showCustom)
        self.m_fromColumnCombo.setVisible(not showCustom)
        self.m_fromColumnLabel.setVisible(not showCustom)
        self.m_toColumnCombo.setVisible(not showCustom)
        self.m_toColumnLabel.setVisible(not showCustom)

    def currentJoinItem(self):
        res = JoinItem(None, None, None, None, None, None)
        res.joinType = self.m_typeCombo.currentText()
        res.tableFrom = self.m_fromTableCombo.currentText()
        res.tableTo = self.m_toTableCombo.currentText()
        if res.joinType == "Custom Join":
            res.where = self.m_whereEdit.toPlainText()
        else:
            res.columnFrom = self.m_fromColumnCombo.currentText()
            res.columnTo = self.m_toColumnCombo.currentText()

        return res

    def currentRuntimeJoinItem(self):
        res = self.m_join
        if res is None:
            res = RuntimeJoinItem(self.currentJoinItem())
            res.added = True
            res.deleted = False
        else:
            res.modified = self.currentJoinItem()

        res.validity = "valid" if res.modified in self.m_validSets else "invalid"

        return res

class RelationshipAttributeJoinsController(QObject):
    def __init__(self, ui, database, schema, connId, host, port, dbName, user, password):
        super(RelationshipAttributeJoinsController, self).__init__()
        self.ui = ui
        self.m_database = database
        self.m_schema = schema
        self.m_connId = connId
        self.m_currentSchemaHost = host
        self.m_currentSchemaPort = port
        self.m_currentSchemaDBName = dbName
        self.m_currentSchemaUserName = user
        self.m_currentSchemaPassword = password

        self.m_model = DataChangeMarkerModelFactory(AddDeleteMarkerModelFactory(JoinsModel))(self.m_connId, self.m_schema, self.m_database)
        self.ui.relAttributeJoinsTable.setModel(self.m_model)
#        self.ui.relAttributeJoinsTable.table().horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

        self.ui.relAttributeJoinsTable.showEdit(True)
        # TODO add and implement validate icon

        self.ui.relAttributeJoinsTable.addBtn().pressed.connect(self.addJoin)
        self.ui.relAttributeJoinsTable.editBtn().pressed.connect(self.editJoin)
        self.ui.relAttributeJoinsTable.deleteBtn().pressed.connect(self.deleteJoin)

        self.ui.relAttributeJoinsResetButton.pressed.connect(self.reset)
        self.ui.relAttributeJoinsSaveButton.pressed.connect(self.save)

    def reset(self):
        self.ui.relAttributeJoinsTable.model().reset()

    def save(self):
        self.ui.relAttributeJoinsTable.model().save()

    def newRowIndex(self):
        selecteds = self.ui.relAttributeJoinsTable.table().selectionModel().selectedIndexes()
        if len(selecteds) != 0:
            idx = selecteds[-1].row() + 1
        else:
            idx = self.ui.relAttributeJoinsTable.model().rowCount()

        return idx

    def addJoin(self):
        dlg = EditJoinWidget(None, self.m_database, self.m_connId, self.m_schema, None)
        res = dlg.exec()
        if res == QDialog.Rejected:
            return
        idx = self.newRowIndex()
        self.m_model.insertJoin(idx, dlg.currentRuntimeJoinItem())

    def editJoin(self):
        selecteds = self.ui.relAttributeJoinsTable.table().selectionModel().selectedIndexes()
        if len(selecteds) == 0:
            return
        idx = selecteds[-1].row()
        dlg = EditJoinWidget(None, self.m_database, self.m_connId, self.m_schema, self.m_model.join(idx))
        res = dlg.exec()
        if res == QDialog.Rejected:
            return
        join = dlg.currentRuntimeJoinItem()
        self.m_model.setJoin(idx, join)

    def deleteJoin(self):
        selecteds = self.ui.relAttributeJoinsTable.table().selectionModel().selectedIndexes()
        if len(selecteds) == 0:
            return
        idx = selecteds[-1].row()
        join = self.m_model.join(idx)
        if join.added:
            self.m_model.deleteJoin(idx)
        else:
            join.deleted = True
            self.m_model.setJoin(idx, join)