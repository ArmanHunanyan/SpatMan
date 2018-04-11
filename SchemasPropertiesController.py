
from PyQt5.QtCore import QObject
from Configuration import Configuration
from VariableGroupController import VariableGroupController

class SchemasPropertiesController(QObject):

    def __init__(self, ui, database, schemaId, currentSchemaController):
        super(SchemasPropertiesController, self).__init__()
        self.ui = ui
        self.m_database = database
        self.m_schemaId = schemaId

        config = Configuration()
        self.ui.schemaPropertiesLanguageComboBox.clear()
        self.ui.schemaPropertiesLanguageComboBox.addItems(config.languages())
        self.ui.schemaPropertiesCharsetsComboBox.clear()
        self.ui.schemaPropertiesCharsetsComboBox.addItems(config.charsets())
        self.ui.schemaPropertiesMainContactCombo.clear()
        self.ui.schemaPropertiesMainContactCombo.addItems([(x[0] + " " + x[1], x[2],) for x in self.m_database.contactList()])
        self.m_schemaPropertiesDB = self.m_database.schemaProperties(self.m_schemaId)
        self.m_schemaPropertiesGeneralController = VariableGroupController(
            self.ui.schemaPropertiesSaveButton, self.ui.schemaPropertiesResetButton,
            "properties", self.m_schemaPropertiesDB,
            self.ui.schemaPropertiesSchemaDescriptionPlainTextEdit, self.ui.schemaPropertiesLanguageComboBox, self.ui.schemaPropertiesCharsetsComboBox,
            self.ui.schemaPropertiesSRIDEdit, self.ui.schemaPropertiesUnitsEdit, self.ui.schemaPropertiesPrecisionEdit,
            self.ui.schemaPropertiesWestEdit, self.ui.schemaPropertiesNorthEdit, self.ui.schemaPropertiesEastEdit, self.ui.schemaPropertiesSouthEdit,
            self.ui.schemaPropertiesDataAccessEdit, self.ui.schemaPropertiesCopyrightEdit, self.ui.schemaPropertiesUserrightEdit,
            self.ui.schemaPropertiesOrganizationEdit, self.ui.schemaPropertiesMainContactCombo)

        self.m_schemaPropertiesGeneralController.saved.connect(currentSchemaController.constructCreateTableTab)