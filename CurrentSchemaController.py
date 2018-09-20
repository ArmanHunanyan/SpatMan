
from PyQt5.QtCore import QObject

from Database import ClientDatabase
from SchemasManageTablesController import SchemasManageTablesController
from SchemasGroupsController import SchemasGroupsController
from SchemasPropertiesController import SchemasPropertiesController
from SchemasCommonColumnsController import SchemasCommonColumnsController
from SchemasColumnsController import SchemasColumnsController
from SchemasCreateTablesController import SchemasCreateTablesController
from SchemasMetadataController import SchemasMetadataController
from SchemasDataPolicyController import SchemasDataPolicyController
from ExchangeTabController import ExchangeTabController
from ReportsTabController import ReportsTabController
from RelationshipsTabController import RelationshipsTabController
from Configuration import Configuration

class CurrentSchemaController(QObject):
    def __init__(self, mainWindow, ui, database):
        super(CurrentSchemaController, self).__init__()
        self.m_database = database
        self.ui = ui
        self.m_currentSchemaId = None
        self.m_schemasManageTabController = None
        self.m_schemasGroupsController = None
        self.m_mainWindow = mainWindow
        self.m_initialWindowTitle = self.m_mainWindow.windowTitle()
        self.ui.schemasWidget.setEnabled(False)

    def setCurrent(self, id, schema, active, dbType, host, port, dbName, user, password):
        self.m_currentSchemaId = id
        self.m_currentSchemaName = schema
        self.m_currentSchemaActive = active
        self.m_currentSchemaDBType = dbType
        self.m_currentSchemaHost = host
        self.m_currentSchemaPort = port
        self.m_currentSchemaDBName = dbName
        self.m_currentSchemaUserName = user
        self.m_currentSchemaPassword = password

        self.ui.schemasWidget.setEnabled(True)

        config = Configuration()
        ogr2ogrDir = config.ogr2ogrDir()

        if ogr2ogrDir is not None and ogr2ogrDir != "":
            self.ui.exchangeWidget.setEnabled(True)

        self.ui.schemaPropertiesCurrentSchemaEdit.setText(self.m_currentSchemaName)
        self.ui.schemasGroupsCurrentSchemaEdit.setText(self.m_currentSchemaName)

        self.m_clientDatabase = ClientDatabase(self.m_database, self.m_currentSchemaDBName, self.m_currentSchemaDBType,
                                self.m_currentSchemaHost, self.m_currentSchemaPort, self.m_currentSchemaUserName, self.m_currentSchemaPassword)

        self.m_mainWindow.setWindowTitle(self.m_initialWindowTitle + " (" + self.m_currentSchemaName + ")")

        self.m_schemasManageTabController = SchemasManageTablesController(self.ui, self.m_clientDatabase, self.m_currentSchemaName, self.m_currentSchemaId)
        self.m_schemasGroupsController = SchemasGroupsController(self.ui, self.m_database, self.m_currentSchemaId)
        self.m_schemasPropertiesController = SchemasPropertiesController(self.ui, self.m_database, self.m_currentSchemaId, self)
        self.m_schemasCommonColumnsController = SchemasCommonColumnsController(self.ui, self.m_clientDatabase, self.m_currentSchemaId)
        self.m_schemasColumnsController = SchemasColumnsController(self.ui, self.m_clientDatabase,
                                                                          self.m_currentSchemaName,
                                                                          self.m_currentSchemaId)
        self.m_schemasMetadataController = SchemasMetadataController(self.ui, self.m_clientDatabase,
                                                                          self.m_currentSchemaName,
                                                                          self.m_currentSchemaId)
        self.m_schemasDataPolicyController = SchemasDataPolicyController(self.ui, self.m_clientDatabase,
                                                                          self.m_currentSchemaName,
                                                                          self.m_currentSchemaId)
        self.constructCreateTableTab()

        if ogr2ogrDir is not None and ogr2ogrDir != "":
            self.m_exchangeTabController = ExchangeTabController(self.ui, self.m_clientDatabase,
                                                                          self.m_currentSchemaName,
                                                                          self.m_currentSchemaId,
                                                                          host, port, dbName, user, password)
        self.m_reportsTabController = ReportsTabController(self.ui, self.m_clientDatabase,
                                                                          self.m_currentSchemaName,
                                                                          self.m_currentSchemaId,
                                                                          host, port, dbName, user, password)

        self.m_relationshipsTabController = RelationshipsTabController(self.ui, self.m_clientDatabase,
                                                         self.m_currentSchemaName,
                                                         self.m_currentSchemaId,
                                                         host, port, dbName, user, password)

    def constructCreateTableTab(self):
        self.m_schemasCreateTablesController = None
        self.m_schemasCreateTablesController = SchemasCreateTablesController(self.ui, self.m_clientDatabase,
                                                                          self.m_currentSchemaName,
                                                                          self.m_currentSchemaId)

    def currentSchemaName(self):
        return self.m_currentSchemaName

    def currentSchemaId(self):
        return self.m_currentSchemaId