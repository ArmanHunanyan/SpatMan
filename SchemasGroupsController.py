
from PyQt5.QtCore import QObject
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMenu
from PyQt5.QtWidgets import QMessageBox

class SchemasGroupsController(QObject):

    def __init__(self, ui, database, schemaId):
        super(SchemasGroupsController, self).__init__()
        self.ui = ui
        self.m_database = database
        self.m_schemaId = schemaId

        self.ui.schemasGroupsGroupsList.clear()
        self.ui.schemasGroupsGroupsList.addItems(self.m_database.schemaGroupList(self.m_schemaId))
        try:
            self.m_database.schemaGroupListChangedSignal.disconnect(self.onSchemaGroupListChanged)
            self.ui.schemasGroupsAddGroupButton.pressed.disconnect(self.onAddSchemaGroupPressed)
            self.ui.schemasGroupsGroupsList.itemSelectionChanged.disconnect(self.schemaGroupListSelectionChanged)
            self.ui.schemasGroupsSaveButton.pressed.disconnect(self.onSaveSchemaGroupsPressed)
            self.ui.schemasGroupsResetButton.pressed.disconnect(self.onResetSchemaGroupsPressed)
            self.ui.schemasGroupsManageGroupsEdit.textEdited.disconnect(self.updateManageGroupsBtnState)
            self.ui.schemasGroupsGroupsList.model().rowsInserted.disconnect(self.updateAddGroupsBtnState)
            self.ui.schemasGroupsGroupsList.model().rowsRemoved.disconnect(self.updateAddGroupsBtnState)
            self.ui.schemasGroupsGroupsList.customContextMenuRequested.disconnect(self.schemaGroupsListContextMenu)
        except:
            pass
        self.m_database.schemaGroupListChangedSignal.connect(self.onSchemaGroupListChanged)
        self.ui.schemasGroupsAddGroupButton.pressed.connect(self.onAddSchemaGroupPressed)
        self.ui.schemasGroupsGroupsList.itemSelectionChanged.connect(self.schemaGroupListSelectionChanged)
        self.ui.schemasGroupsSaveButton.pressed.connect(self.onSaveSchemaGroupsPressed)
        self.ui.schemasGroupsResetButton.pressed.connect(self.onResetSchemaGroupsPressed)
        self.ui.schemasGroupsManageGroupsEdit.textChanged.connect(self.updateAddGroupsBtnState)
        self.ui.schemasGroupsGroupsList.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.schemasGroupsGroupsList.model().rowsInserted.connect(self.updateAddGroupsBtnState)
        self.ui.schemasGroupsGroupsList.model().rowsRemoved.connect(self.updateAddGroupsBtnState)
        self.ui.schemasGroupsGroupsList.customContextMenuRequested.connect(self.schemaGroupsListContextMenu)

        self.updateAddGroupsBtnState()
        self.schemaGroupListSelectionChanged()

    def schemaGroupsListContextMenu(self, point):
        globalPos = self.ui.schemasGroupsGroupsList.mapToGlobal(point)
        menu = QMenu()
        menu.addAction("Delete", self.deleteSelectedSchemaGroup)
        menu.exec(globalPos)

    def deleteSelectedSchemaGroup(self):
        sel = self.ui.schemasGroupsGroupsList.selectedItems()
        if len(sel) == 1:
            item = sel[0]
            res = QMessageBox.question(None, 'Delete Group?',
                                       "Delete group '%s' from database? \n"
                                       "All information about group will be discarded" % item.text(),
                                       QMessageBox.Yes, QMessageBox.No)
            if res == QMessageBox.Yes:
                self.m_database.deleteSchemaGroup(self.m_schemaId, item.text())

    def updateAddGroupsBtnState(self):
        isValid = len(self.ui.schemasGroupsManageGroupsEdit.text()) != 0 and \
                  (
                  self.ui.schemasGroupsManageGroupsEdit.text().lower() not in [self.ui.schemasGroupsGroupsList.item(idx).text().lower() for idx
                                                                 in range(self.ui.schemasGroupsGroupsList.count())])
        self.ui.schemasGroupsAddGroupButton.setEnabled(isValid)

    def onSchemaGroupListChanged(self):
        self.ui.schemasGroupsGroupsList.clear()
        self.ui.schemasGroupsGroupsList.addItems(self.m_database.schemaGroupList(self.m_schemaId))

    def onAddSchemaGroupPressed(self):
        self.m_database.addSchemaGroup(self.m_schemaId, self.ui.schemasGroupsManageGroupsEdit.text())

    def schemaGroupListSelectionChanged(self):
        sel = self.ui.schemasGroupsGroupsList.selectedItems()
        if len(sel) != 1:
            self.ui.schemasGroupsGroupNameEdit.setText("")
            self.ui.schemasGroupsGroupDescrEdit.setText("")
            self.ui.schemasGroupsGroupTablePrefixEdit.setText("")
            self.ui.schemasGroupsGroupMenuNameEdit.setText("")

            self.ui.schemasGroupsResetButton.setEnabled(False)
            self.ui.schemasGroupsSaveButton.setEnabled(False)
            self.ui.schemasGroupsGroupNameEdit.setEnabled(False)
            self.ui.schemasGroupsGroupDescrEdit.setEnabled(False)
            self.ui.schemasGroupsGroupTablePrefixEdit.setEnabled(False)
            self.ui.schemasGroupsGroupMenuNameEdit.setEnabled(False)
            return
        else:
            self.ui.schemasGroupsResetButton.setEnabled(True)
            self.ui.schemasGroupsSaveButton.setEnabled(True)
            self.ui.schemasGroupsGroupNameEdit.setEnabled(True)
            self.ui.schemasGroupsGroupDescrEdit.setEnabled(True)
            self.ui.schemasGroupsGroupTablePrefixEdit.setEnabled(True)
            self.ui.schemasGroupsGroupMenuNameEdit.setEnabled(True)
        item = sel[0]

        self.ui.schemasGroupsGroupNameEdit.setText(item.text())
        descr, prefix, menu = self.m_database.schemaGroupInfo(self.m_schemaId, item.text())
        self.ui.schemasGroupsGroupDescrEdit.setText(descr)
        self.ui.schemasGroupsGroupTablePrefixEdit.setText(prefix)
        self.ui.schemasGroupsGroupMenuNameEdit.setText(menu)

    def onSaveSchemaGroupsPressed(self):
        name = self.ui.schemasGroupsGroupNameEdit.text()
        descr = self.ui.schemasGroupsGroupDescrEdit.text()
        prefix = self.ui.schemasGroupsGroupTablePrefixEdit.text()
        menu = self.ui.schemasGroupsGroupMenuNameEdit.text()

        self.m_database.saveSchemasGroupData(self.m_schemaId, name, descr, prefix, menu)

        self.ui.schemasGroupsGroupNameEdit.setText("")
        self.ui.schemasGroupsGroupDescrEdit.setText("")
        self.ui.schemasGroupsGroupTablePrefixEdit.setText("")
        self.ui.schemasGroupsGroupMenuNameEdit.setText("")

        self.ui.schemasGroupsGroupsList.clearSelection()

    def onResetSchemaGroupsPressed(self):
        sel = self.ui.schemasGroupsGroupsList.selectedItems()
        if len(sel) != 1:
            return
        item = sel[0]

        self.ui.schemasGroupsGroupNameEdit.setText(item.text())
        descr, prefix, menu = self.m_database.schemaGroupInfo(self.m_schemaId, item.text())
        self.ui.schemasGroupsGroupDescrEdit.setText(descr)
        self.ui.schemasGroupsGroupTablePrefixEdit.setText(prefix)
        self.ui.schemasGroupsGroupMenuNameEdit.setText(menu)