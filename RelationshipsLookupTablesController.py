
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

class RelationshipsLookupTablesController(QObject):
    def __init__(self, ui, database, schema, connId, host, port, dbName, user, password):
        super(RelationshipsLookupTablesController, self).__init__()
        self.ui = ui
        self.m_database = database
        self.m_schema = schema
        self.m_connId = connId
        self.m_currentSchemaHost = host
        self.m_currentSchemaPort = port
        self.m_currentSchemaDBName = dbName
        self.m_currentSchemaUserName = user
        self.m_currentSchemaPassword = password

        self.ui.relLookupTablesTableListWidget.setSelectionMode(QAbstractItemView.SingleSelection)

        self.m_tableListWithFilterController = TableListWithFiltersController(self.m_database, self.m_schema, self.m_connId,
                        self.ui.relLookupTablesTableListWidget, self.ui.relLookupTablesFilterEdit, self.ui.relLookupTablesFilterBtn,
                                        lambda idx: self.isModified(),
                                        lambda db, schema, connId : db.localDatabase().localTableList(connId, False))

        self.ui.relLookupTablesTableListWidget.selectionModel().selectionChanged.connect(self.selectionChanged)
        self.selectionChanged()

    def isModified(self):
        return False

    def updateControlState(self, disable):
        self.ui.relLookupTablesLookupNameEdit.setDisabled(disable)
        self.ui.relLookupTablesApplicationCombo.setDisabled(disable)
        self.ui.relLookupTablesSourceTableEdit.setDisabled(disable)
        self.ui.relLookupTablesLookupDescriptionEdit.setDisabled(disable)
        self.ui.relLookupTablesFilterPropEdit.setDisabled(disable)
        self.ui.relLookupTablesColumnForCodeCombo.setDisabled(disable)
        self.ui.relLookupTablesColumnForDescriptionCombo.setDisabled(disable)
        self.ui.relLookupTablesFilterPropTestBtn.setDisabled(disable)
        self.ui.relLookupTablesUseDistinctChk.setDisabled(disable)
        self.ui.relLookupTablesResetButton.setDisabled(disable)
        self.ui.relLookupTablesSaveButton.setDisabled(disable)

        if disable:
            self.ui.relLookupTablesLookupNameEdit.setText("")
            self.ui.relLookupTablesApplicationCombo.setCurrentText("")
            return
            self.ui.relLookupTablesSourceTableEdit.setDisabled(disable)
            self.ui.relLookupTablesLookupDescriptionEdit.setDisabled(disable)
            self.ui.relLookupTablesFilterPropEdit.setDisabled(disable)
            self.ui.relLookupTablesColumnForCodeCombo.setDisabled(disable)
            self.ui.relLookupTablesColumnForDescriptionCombo.setDisabled(disable)
            self.ui.relLookupTablesFilterPropTestBtn.setDisabled(disable)
            self.ui.relLookupTablesUseDistinctChk.setDisabled(disable)
            self.ui.relLookupTablesResetButton.setDisabled(disable)
            self.ui.relLookupTablesSaveButton.setDisabled(disable)

    def selectionChanged(self):
        sel = self.ui.relLookupTablesTableListWidget.selectionModel().selectedIndexes()
        self.updateControlState(len(sel) != 1)
        if len(sel) != 1:
            return
