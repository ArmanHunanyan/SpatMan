
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QAbstractItemView
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QDoubleValidator

from TableMetadata import TableMetadata
from ControlBinder import ControlBinder
from Value import Value

class SchemasMetadataController(ControlBinder):
    def __init__(self, ui, database, schema, connId):
        super(SchemasMetadataController, self).__init__()
        self.ui = ui
        self.m_database = database
        self.m_schema = schema
        self.m_connId = connId

        self.ui.schemasMetadataOrphansState.stateChanged.connect(self.setTableNames)
        self.m_database.tableListChanged.connect(self.setTableNames)
        self.setTableNames()

        self.fillContacts()
        self.fillHierarchy()

        self.ui.schemasMetadataTableList.setSelectionMode(QAbstractItemView.SingleSelection)
        self.ui.schemasMetadataTableList.selectionModel().selectionChanged.connect(self.tablesListSelectionChanged)
        self.tablesListSelectionChanged()

        self.ui.schemasMetadataSaveBtn.pressed.connect(self.saveMetadataPressed)
        self.ui.schemasMetadataDeleteBtn.pressed.connect(self.deleteMetadataPressed)
        self.ui.schemasMetadataReassignBtn.pressed.connect(self.reassignMetadataPressed)
        self.ui.schemasMetadataResetBtn.pressed.connect(self.resetMetadataPressed)

        self.ui.schemasMetadataCalculateExtentsButton.pressed.connect(self.calculateExtents)
        self.ui.schemasMetadataFromSchemaPropertiesButton.pressed.connect(self.extentsFromSchemaProps)

        self.ui.schemasMetadataPrecisionResolutionEdit.setValidator(QDoubleValidator())

        # TODO temporary
        self.ui.schemasMetadataXMLOutBtn.setDisabled(True)

    def document(self):
        return self.m_metadata

    def calculateExtents(self):
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.m_database.spatialExtents(self.m_metadata, self.m_schema)
            QApplication.restoreOverrideCursor()
        except Exception as e:
            QApplication.restoreOverrideCursor()
            raise e
        self.roundSpatialExtents()

    def roundSpatialExtent(self, ext):
        if int(float(ext)) > 999:
            ext = "{0:.3f}".format(float(ext)).rstrip('0').rstrip('.')
        else:
            ext = "{0:.8f}".format(float(ext)).rstrip('0').rstrip('.')
        return ext

    def roundSpatialExtents(self):
        westLong = self.m_metadata.westLong.modifiedValue
        eastLong = self.m_metadata.eastLong.modifiedValue
        southLat = self.m_metadata.southLat.modifiedValue
        northLat = self.m_metadata.northLat.modifiedValue
        westLong = self.roundSpatialExtent(westLong)
        eastLong = self.roundSpatialExtent(eastLong)
        southLat = self.roundSpatialExtent(southLat)
        northLat = self.roundSpatialExtent(northLat)
        self.m_metadata.setModified("westLong", westLong)
        self.m_metadata.setModified("eastLong", eastLong)
        self.m_metadata.setModified("southLat", southLat)
        self.m_metadata.setModified("northLat", northLat)

    def extentsFromSchemaProps(self):
        props = self.m_database.localDatabase().schemaProperties(self.m_connId)
        self.m_metadata.setModified("westLong", props.properties[6])
        self.m_metadata.setModified("eastLong", props.properties[8])
        self.m_metadata.setModified("southLat", props.properties[9])
        self.m_metadata.setModified("northLat", props.properties[7])
        self.roundSpatialExtents()

    def saveMetadataPressed(self):
        self.m_database.saveMetadata(self.m_connId, self.m_metadata)
        self.m_metadata.commit()
        QMessageBox.information(None, "Metadata saved",
                                "Metadata successfully saved for table '%s'" % (self.m_currTableName))

    def deleteMetadataPressed(self):
        res = QMessageBox.question(None, 'Delete Metadata?',
                                   "Delete metadata for table '%s'? \n" % self.m_currTableName,
                                   QMessageBox.Yes, QMessageBox.No)
        if res == QMessageBox.No:
            return
        self.m_database.deleteMetadata(self.m_connId, self.m_metadata)
        self.tablesListSelectionChanged() # Call this to get non-meta indformation from DB
        QMessageBox.information(None, "Metadata deleted",
                                "Metadata of table '%s' is deleted.\n Note: Table itself still exists" % (self.m_currTableName))

    def reassignMetadataPressed(self):
        tableNames = []
        for idx in range(self.ui.schemasMetadataTableList.count()):
            tableNames.append(self.ui.schemasMetadataTableList.item(idx).text())
        res = QMessageBox.question(None, 'Reassign Metadata?',
                                   "Do you want to assign metadata for following tables\n%s? \n" % "\n".join(
                                       '\t' + tableName for tableName in tableNames),
                                   QMessageBox.Yes, QMessageBox.No)
        if res == QMessageBox.No:
            return

        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            for tableName in tableNames:
                meta = self.m_database.metadata(self.m_connId, tableName, self.m_schema)
                meta.copyFrom(self.m_metadata)
                self.m_database.saveMetadata(self.m_connId, meta)

            self.setTableNames()
            QApplication.restoreOverrideCursor()
        except Exception as e:
            QApplication.restoreOverrideCursor()
            raise e


    def resetMetadataPressed(self):
        self.m_metadata.reset()

    def disableAll(self, disable):
        enableButtons = False
        if not disable and self.m_metadata is not None and self.m_metadata.geometryColumn != "":
            enableButtons = True
        self.ui.schemasMetadataTableNameEdit.setDisabled(disable)
        self.ui.schemasMetadataTitleEdit.setDisabled(disable)
        self.ui.schemasMetadataAlternativeTitleEdit.setDisabled(disable)
        self.ui.schemasMetadataDescriptionEdit.setDisabled(disable)
        self.ui.schemasMetadataAbstractEdit.setDisabled(disable)
        self.ui.schemasMetadataThemeCombo.setDisabled(disable)
        self.ui.schemasMetadataHierarchyCombo.setDisabled(disable)
        self.ui.schemasMetadataStartDateEdit.setDisabled(disable)
        self.ui.schemasMetadataEndDateEdit.setDisabled(disable)
        self.ui.schemasMetadataUpdatesCombo.setDisabled(disable)
        self.ui.schemasMetadataStatusCombo.setDisabled(disable)
        self.ui.schemasMetadataSelectContactCombo.setDisabled(disable)
        self.ui.schemasMetadataWestEdit.setDisabled(disable)
        self.ui.schemasMetadataNorthEdit.setDisabled(disable)
        self.ui.schemasMetadataEastEdit.setDisabled(disable)
        self.ui.schemasMetadataSouthEdit.setDisabled(disable)
        self.ui.schemasMetadataCalculateExtentsButton.setDisabled(not enableButtons)
        self.ui.schemasMetadataFromSchemaPropertiesButton.setDisabled(not enableButtons)
        self.ui.schemasMetadataDataTypeCombo.setDisabled(disable)
        self.ui.schemasMetadataPrecisionResolutionEdit.setDisabled(disable)
        self.ui.schemasMetadataStatementEdit.setDisabled(disable)
        self.ui.schemasMetadataAllRadio.setDisabled(disable)
        self.ui.schemasMetadataGeomRadio.setDisabled(disable)
        self.ui.schemasMetadataAttrRadio.setDisabled(disable)
        self.ui.schemasMetadataUdpateDateStampEdit.setDisabled(disable)
        self.ui.schemasMetadataKeywordsEdit.setDisabled(disable)
        self.ui.schemasMetadataURLEdit.setDisabled(disable)

    def bindControls(self):
        self.bindEdit("schemasMetadataTableNameEdit", "tableName")
        self.bindEdit("schemasMetadataTitleEdit", "title")
        self.bindEdit("schemasMetadataAlternativeTitleEdit", "alternativeTitle")
        self.bindEdit("schemasMetadataDescriptionEdit", "description")

        self.bindTextEdit("schemasMetadataAbstractEdit", "abstract")

        self.bindCombo("schemasMetadataThemeCombo", "theme")
        self.bindMCombo("schemasMetadataHierarchyCombo", "hierarchy")

        self.bindDateEdit("schemasMetadataStartDateEdit", "temporalRangeStartDate")
        self.bindDateEdit("schemasMetadataEndDateEdit", "temporalRangeEndDate")

        self.bindCombo("schemasMetadataUpdatesCombo", "temporalRangeUpdates")
        self.bindCombo("schemasMetadataStatusCombo", "temporalRangeStatus")

        self.m_metadata.language = Value(self.m_database.localDatabase().schemaProperties(self.m_connId).properties[1])

        self.bindMCombo("schemasMetadataSelectContactCombo", "contactId")

        self.bindEdit("schemasMetadataWestEdit", "westLong")
        self.bindEdit("schemasMetadataNorthEdit", "northLat")
        self.bindEdit("schemasMetadataEastEdit", "eastLong")
        self.bindEdit("schemasMetadataSouthEdit", "southLat")

        self.bindCombo("schemasMetadataDataTypeCombo", "dataType")
        self.bindEdit("schemasMetadataPrecisionResolutionEdit", "precisionResolution")
        self.bindTextEdit("schemasMetadataStatementEdit", "lineageStatement")
        self.bindRadioButtonGroup([("schemasMetadataAllRadio", "All"),
                                   ("schemasMetadataGeomRadio", "Geom"),
                                   ("schemasMetadataAttrRadio", "Attr")], "lineageMaintain")
        self.bindDateEdit("schemasMetadataUdpateDateStampEdit", "updateDateStamp")
        self.bindEdit("schemasMetadataKeywordsEdit", "keywords")
        self.bindEdit("schemasMetadataURLEdit", "onlineURL")

    def updateButtonStates(self):
        sel = self.ui.schemasMetadataTableList.selectionModel().selectedIndexes()
        disable = len(sel) == 0
        disable2 = disable
        if not disable2 and self.m_metadata is not None:
            disable2 = not self.m_metadata.isModified()
        self.ui.schemasMetadataDeleteBtn.setDisabled(disable)
        self.ui.schemasMetadataSaveBtn.setDisabled(disable2)
     #   self.ui.schemasMetadataXMLOutBtn.setDisabled(disable)
        self.ui.schemasMetadataResetBtn.setDisabled(disable2)

    def fillContacts(self):
        self.ui.schemasMetadataSelectContactCombo.addItems(
            [(x[0] + " " + x[1], x[2],) for x in self.m_database.localDatabase().contactList()])

    def fillHierarchy(self):
        self.ui.schemasMetadataHierarchyCombo.addItems(
            [(x[0], x[1],) for x in self.m_database.localDatabase().hierList()])

    def newMetadata(self):
        self.setMetadata(TableMetadata())

    def setMetadata(self, metadata):
        self.m_metadata = metadata
        self.m_metadata.changedSignal.connect(self.updateButtonStates)
        self.updateButtonStates()

    def tablesListSelectionChanged(self):
        sel = self.ui.schemasMetadataTableList.selectionModel().selectedIndexes()
        if len(sel) == 0:
            self.newMetadata()
            self.bindControls()
            self.disableAll(True)
            return
        if len(sel) != 1:
            return

        idx = sel[0].row()
        self.m_currTableName = self.ui.schemasMetadataTableList.item(idx).text()
        self.setMetadata(self.m_database.metadata(self.m_connId, self.m_currTableName, self.m_schema))
        self.bindControls()
        self.disableAll(False)
        self.updateButtonStates()

    def setTableNames(self):
        sel = self.ui.schemasMetadataTableList.selectionModel().selectedIndexes()

        selTableName = None
        selMeta = None
        if len(sel) == 1:
            idx = sel[0].row()
            selTableName = self.ui.schemasMetadataTableList.item(idx).text()
            selMeta = self.m_metadata

        self.ui.schemasMetadataTableList.clearSelection()
        self.ui.schemasMetadataTableList.clear()

        orphans = self.ui.schemasMetadataOrphansState.isChecked()
        tables = self.m_database.localDatabase().localTableList(self.m_connId, orphans)
        self.ui.schemasMetadataReassignBtn.setEnabled(orphans)

        for table in tables:
            self.ui.schemasMetadataTableList.addItem(table)

        for idx in range(self.ui.schemasMetadataTableList.count()):
            if self.ui.schemasMetadataTableList.item(idx).text() == selTableName:
                self.ui.schemasMetadataTableList.item(idx).setSelected(True)
                self.m_metadata = selMeta
                self.bindControls()
                break
