
from PyQt5.QtCore import QObject
from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QAbstractItemView
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QDoubleValidator

import re

from TableMetadata import TableDataPolicy
from Value import Value
from ControlBinder import ControlBinder

class SchemasDataPolicyController(ControlBinder):
    def __init__(self, ui, database, schema, connId):
        super(SchemasDataPolicyController, self).__init__()
        self.ui = ui
        self.m_database = database
        self.m_schema = schema
        self.m_connId = connId

        self.ui.schemasDataPolicyOrphansState.stateChanged.connect(self.setTableNames)
        self.m_database.tableListChanged.connect(self.setTableNames)
        self.setTableNames()

        self.ui.schemasDataPolicyTableList.setSelectionMode(QAbstractItemView.SingleSelection)
        self.ui.schemasDataPolicyTableList.selectionModel().selectionChanged.connect(self.tablesListSelectionChanged)
        self.tablesListSelectionChanged()

        self.ui.schemasDataPolicySaveButton.pressed.connect(self.saveDataPolicyPressed)
        self.ui.schemasDataPolicyDeleteButton.pressed.connect(self.deleteDataPolicyPressed)
        self.ui.schemasDataPolicyReassignButton.pressed.connect(self.reassignDataPolicyPressed)
        self.ui.schemasDataPolicyResetButton.pressed.connect(self.resetDataPolicyPressed)

        self.ui.schemasDataPolicyCopyFromGlobalButton.pressed.connect(self.copyFromGlobalPressed)

        # TODO temporary
        self.ui.schemasDataPolicyXMLOutButton.setDisabled(True)

    def document(self):
        return self.m_dataPolicy

    def copyFromGlobalPressed(self):
        props = self.m_database.localDatabase().schemaProperties(self.m_connId)
        self.m_dataPolicy.setModified("dataAccess", props.properties[10])
        self.m_dataPolicy.setModified("copyright", props.properties[11])
        self.m_dataPolicy.setModified("useRight", props.properties[12])

    def saveDataPolicyPressed(self):
        self.m_database.saveDataPolicy(self.m_connId, self.m_dataPolicy)
        self.m_dataPolicy.commit()
        QMessageBox.information(None, "DataPolicy saved",
                                "Data Policy successfully saved for table '%s'" % (self.m_currTableNameAndTitle))

    def deleteDataPolicyPressed(self):
        res = QMessageBox.question(None, 'Delete DataPolicy?',
                                   "Delete Data Policy for table '%s'? \n" % self.m_currTableNameAndTitle,
                                   QMessageBox.Yes, QMessageBox.No)
        if res == QMessageBox.No:
            return
        self.m_database.deleteDataPolicy(self.m_connId, self.m_dataPolicy)
        self.tablesListSelectionChanged() # Call this to get non-meta indformation from DB
        QMessageBox.information(None, "Data Policy deleted",
                                "Data Policy of table '%s' is deleted.\n Note: Table itself and metadata info still exists" % (self.m_currTableNameAndTitle))

    def reassignDataPolicyPressed(self):
        tableNames = []
        for idx in range(self.ui.schemasDataPolicyTableList.count()):
            nameAndTitle = self.ui.schemasDataPolicyTableList.item(idx).text()
            tableNames.append(self.parseTableName(nameAndTitle))
        res = QMessageBox.question(None, 'Reassign Data Policy?',
                                   "Do you want to assign Data Policy for following tables\n%s? \n" % "\n".join(
                                       '\t' + tableName for tableName in tableNames),
                                   QMessageBox.Yes, QMessageBox.No)
        if res == QMessageBox.No:
            return

        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            for tableName in tableNames:
                meta = self.m_database.dataPolicy(self.m_connId, tableName, self.m_schema)
                meta.copyFrom(self.m_dataPolicy)
                self.m_database.saveDataPolicy(self.m_connId, meta)

            self.setTableNames()
            QApplication.restoreOverrideCursor()
        except Exception as e:
            QApplication.restoreOverrideCursor()
            raise e

    def resetDataPolicyPressed(self):
        self.m_dataPolicy.reset()

    def disableAll(self, disable):
        self.ui.schemasDataPolicyDataAccessEdit.setDisabled(disable)
        self.ui.schemasDataPolicyCopyrightEdit.setDisabled(disable)
        self.ui.schemasDataPolicyUseRightEdit.setDisabled(disable)
        self.ui.schemasDataPolicyClassificationCombo.setDisabled(disable)
        self.ui.schemaDatePolicyreferenceDateEdit.setDisabled(disable)
        self.ui.schemasDataPolicyCopyFromGlobalButton.setDisabled(disable)

    def bindControls(self):
        self.bindEdit("schemasDataPolicyDataAccessEdit", "dataAccess")
        self.bindEdit("schemasDataPolicyCopyrightEdit", "copyright")
        self.bindEdit("schemasDataPolicyUseRightEdit", "useRight")
        self.bindCombo("schemasDataPolicyClassificationCombo", "classification")
        self.bindRefDateEdit("schemaDatePolicyreferenceDateEdit", "referenceDate")

    def updateButtonStates(self):
        sel = self.ui.schemasDataPolicyTableList.selectionModel().selectedIndexes()
        disable = len(sel) == 0
        disable2 = disable
        if not disable2 and self.m_dataPolicy is not None:
            disable2 = not self.m_dataPolicy.isModified()
        self.ui.schemasDataPolicyDeleteButton.setDisabled(disable)
        self.ui.schemasDataPolicySaveButton.setDisabled(disable2)
        #self.ui.schemasDataPolicyXMLOutButton.setDisabled(disable)
        self.ui.schemasDataPolicyResetButton.setDisabled(disable2)

    def newDataPolicy(self):
        self.setDataPolicy(TableDataPolicy())

    def setDataPolicy(self, dataPolicy):
        self.m_dataPolicy = dataPolicy
        self.m_dataPolicy.changedSignal.connect(self.updateButtonStates)
        self.updateButtonStates()

    def parseTableName(self, tableNameTitle):
        match = re.search("([^\\(\\)]+) \((.+)\\)", tableNameTitle)

        tableName = match.group(2)
        title = match.group(1)
        return tableName

    def tablesListSelectionChanged(self):
        sel = self.ui.schemasDataPolicyTableList.selectionModel().selectedIndexes()
        if len(sel) == 0:
            self.newDataPolicy()
            self.bindControls()
            self.disableAll(True)
            return
        if len(sel) != 1:
            return

        idx = sel[0].row()

        self.m_currTableNameAndTitle = self.ui.schemasDataPolicyTableList.item(idx).text()

        tableName = self.parseTableName(self.m_currTableNameAndTitle)

        self.setDataPolicy(self.m_database.dataPolicy(self.m_connId, tableName, self.m_schema))
        self.bindControls()
        self.disableAll(False)
        self.updateButtonStates()

    def tableLabel(self, nameTitlePair):
        return nameTitlePair[1] + (" (%s)" % nameTitlePair[0])

    def setTableNames(self):
        sel = self.ui.schemasDataPolicyTableList.selectionModel().selectedIndexes()

        selTableNameTitle = None
        selMeta = None
        if len(sel) == 1:
            idx = sel[0].row()
            selTableNameTitle = self.ui.schemasDataPolicyTableList.item(idx).text()
            selMeta = self.m_dataPolicy

        self.ui.schemasDataPolicyTableList.clearSelection()
        self.ui.schemasDataPolicyTableList.clear()

        orphans = self.ui.schemasDataPolicyOrphansState.isChecked()
        tables = self.m_database.localDatabase().localTableAndTitleList(self.m_connId, orphans)
        self.ui.schemasDataPolicyReassignButton.setEnabled(orphans)

        for table in tables:
            self.ui.schemasDataPolicyTableList.addItem(self.tableLabel(table))

        for idx in range(self.ui.schemasDataPolicyTableList.count()):
            if self.ui.schemasDataPolicyTableList.item(idx).text() == selTableNameTitle:
                self.ui.schemasDataPolicyTableList.item(idx).setSelected(True)
                self.m_dataPolicy = selMeta
                self.bindControls()
                break
