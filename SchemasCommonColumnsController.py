from PyQt5.QtCore import QObject
from PyQt5.QtCore import QAbstractTableModel
from PyQt5.QtWidgets import QMessageBox

from TableInfo import TableInfo
from ColumnsTableModel import ColumnsTableModelFactory
from ModelWithValidators import ModelWithValidatorsFactory

class CommonColumnsTableModel(QAbstractTableModel):
    def __init__(self, database, connId):
        super(CommonColumnsTableModel, self).__init__(None)

        self.m_data = []
        self.m_database = database
        self.m_modified = False
        self.m_connId = connId

    def fetchData(self):
        self.modelAboutToBeReset.emit()

        infos = self.m_database.commonColumnsInfo(self.m_connId)
        self.m_data = list(TableInfo(info[0], False, *info[1:]) for info in infos)

        self.m_modified = False
        self.modelReset.emit()
        self.modified.emit(self.m_modified)

    def save(self):
        error = False
        self.modelAboutToBeReset.emit()
        for row in range(self.rowCount()):
            if self.rowIsModified(row):
                try:
                    self.m_database.saveCommonColumnInfo(self.m_data[row], self.m_connId)
                except Exception as e:
                    QMessageBox.warning(None, "Failed", str(e))
                    error = True
        if not error:
            self.fetchData()
            self.m_modified = False
        self.modelReset.emit()
        if not error:
            self.modified.emit(self.m_modified)

class SchemasCommonColumnsController(QObject):
    def __init__(self, ui, database, connId):
        super(SchemasCommonColumnsController, self).__init__()
        self.ui = ui
        self.m_database = database
        self.m_connId = connId

        self.ui.commonColumnsTable.setModel(
            ColumnsTableModelFactory(ModelWithValidatorsFactory(CommonColumnsTableModel))(self.m_database, self.m_connId))
        self.ui.commonColumnsTable.model().fetchData()

        self.ui.commonColumnsTable.model().modified.connect(self.updateSaveResetBtnsState)
        self.ui.commonColumnsTable.model().dataChanged.connect(self.updateSaveResetBtnsState)
        self.ui.commonColumnsTable.model().initValidators(None)
        self.updateSaveResetBtnsState()

        self.ui.commonColumnsTable.init(None)

        self.ui.commonColumnsResetBtn.pressed.connect(self.resetPressed)
        self.ui.commonColumnsSaveBtn.pressed.connect(self.savePressed)

        self.ui.commonColumnsTable.table().selectionModel().selectionChanged.connect(
            self.updateAddDeleteBtnsState)
        self.updateAddDeleteBtnsState()

        self.ui.commonColumnsTable.addBtn().pressed.connect(self.addTableColumn)
        self.ui.commonColumnsTable.deleteBtn().pressed.connect(self.deleteTableColumn)

    def addTableColumn(self):
        selecteds = self.ui.commonColumnsTable.table().selectionModel().selectedIndexes()
        if len(selecteds) != 0:
            idx = selecteds[-1].row() + 1
        else:
            idx = self.ui.commonColumnsTable.model().rowCount()
        self.ui.commonColumnsTable.model().addRow(idx)
        self.ui.commonColumnsTable.table().scrollToBottom()

    def deleteTableColumn(self):
        selecteds = self.ui.commonColumnsTable.table().selectionModel().selectedIndexes()
        if len(selecteds) == 0:
            return
        self.ui.commonColumnsTable.model().deleteRows([sel.row() for sel in selecteds])

    def updateAddDeleteBtnsState(self):
        enableAdd = True
        enableDelete = enableAdd and (
        len(self.ui.commonColumnsTable.table().selectionModel().selectedIndexes()) != 0)

        self.ui.commonColumnsTable.addBtn().setEnabled(enableAdd)
        self.ui.commonColumnsTable.deleteBtn().setEnabled(enableDelete)

    def resetPressed(self):
        self.ui.commonColumnsTable.model().reset()

    def savePressed(self):
        self.ui.commonColumnsTable.model().save()

    def updateSaveResetBtnsState(self):
        modified = self.ui.commonColumnsTable.model().isModified()
        self.ui.commonColumnsSaveBtn.setEnabled(modified and self.ui.commonColumnsTable.model().isValid())
        self.ui.commonColumnsResetBtn.setEnabled(modified)