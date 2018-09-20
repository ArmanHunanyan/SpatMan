
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

class RelationshipNetworksController(QObject):
    def __init__(self, ui, database, schema, connId, host, port, dbName, user, password):
        super(RelationshipNetworksController, self).__init__()
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