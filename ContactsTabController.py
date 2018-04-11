from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QMenu
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QAbstractTableModel
from PyQt5.QtCore import Qt

from ComboboxDelegate import ComboDelegate
from SqlModel import SqlModelFactory
from TableInfo import TableInfo
from ModelWithValidators import ModelWithValidatorsFactory

class ContactAddressModel(QAbstractTableModel):
    def __init__(self, database, contactId):
        super(ContactAddressModel, self).__init__(None)

        self.m_data = []
        self.m_database = database
        self.m_modified = False
        self.m_contactId = contactId
        self.m_columns = ["Address Type", "Address Value"]

    def setContactId(self, contactId):
        self.m_contactId = contactId

    def fetchDataImpl(self):
        infos = self.m_database.contactAddressInfo(self.m_contactId)
        if infos is None:
            self.m_data = []
        else:
            self.m_data = list(TableInfo(info[0], False, *info[1:]) for info in infos)

    def saveRowImpl(self, row):
        self.m_database.saveContactAddressInfo(row, self.m_contactId)

class ContactsTabController(QObject):

    def __init__(self, ui, database):
        super(ContactsTabController, self).__init__()
        self.ui = ui
        self.m_database = database
        self.initContactsTab()

    # Contacts tab related
    def initContactsTab(self):
        self.onContactListChanged()
        self.m_database.contactListChangedSignal.connect(self.onContactListChanged)
        self.ui.addContactButton.pressed.connect(self.onAddContactPressed)
        self.ui.contactListWidget.itemSelectionChanged.connect(self.contactsListSelectionChanged)
        self.ui.contactSaveButton.pressed.connect(self.onSaveContactPressed)
        self.ui.contactResetButton.pressed.connect(self.onResetContactPressed)
        self.ui.addContactLineEdit.textEdited.connect(self.updateAddContactBtnState)
        self.ui.addContactSurnameLineEdit.textEdited.connect(self.updateAddContactBtnState)
        self.ui.contactListWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.contactListWidget.model().rowsInserted.connect(self.updateAddContactBtnState)
        self.ui.contactListWidget.model().rowsRemoved.connect(self.updateAddContactBtnState)
        self.ui.contactListWidget.customContextMenuRequested.connect(self.contactListContextMenu)

        self.ui.contactAddressTable.setModel(
            SqlModelFactory(ModelWithValidatorsFactory(ContactAddressModel))(self.m_database, 0))
        self.ui.contactAddressTable.model().fetchData()

        self.ui.contactAddressTable.model().modified.connect(self.updateContactAddressButtons)
        self.ui.contactAddressTable.model().dataChanged.connect(self.updateContactAddressButtons)
        self.ui.contactAddressTable.model().initValidators(None)

        self.updateContactAddressButtons()

        self.ui.contactAddressTable.addBtn().pressed.connect(self.addContactAddress)
        self.ui.contactAddressTable.deleteBtn().pressed.connect(self.deleteContactAddress)

        self.ui.contactAddressTableSaveButton.pressed.connect(self.saveContactAddresses)
        self.ui.contactAddressTableResetButton.pressed.connect(self.resetContactAddresses)

        delegate = ComboDelegate(['EMAIL', 'PHONE', 'MOBILE', 'FAX', 'POST'], self.ui.contactAddressTable.table())
        self.ui.contactAddressTable.table().setItemDelegateForColumn(0, delegate)

        self.updateAddContactBtnState()
        self.contactsListSelectionChanged()


    def contactListContextMenu(self, point):
        globalPos = self.ui.contactListWidget.mapToGlobal(point)
        menu = QMenu()
        menu.addAction("Delete", self.deleteSelectedContact)
        menu.exec(globalPos)

    def deleteSelectedContact(self):
        sel = self.ui.contactListWidget.selectedItems()
        if len(sel) == 1:
            item = sel[0]
            res = QMessageBox.question(None, 'Delete contact?',
                                       "Delete contact '%s' from database? \n"
                                       "All information about contact will be discarded" % item.text(),
                                       QMessageBox.Yes, QMessageBox.No)
            if res == QMessageBox.Yes:
                names = item.text().split(" ")
                self.m_database.deleteContact(self.m_currentContactId)

    def updateAddContactBtnState(self):
        isValid = (len(self.ui.addContactLineEdit.text())) != 0 and (len(self.ui.addContactSurnameLineEdit.text()) != 0) and \
                  (self.ui.addContactLineEdit.text().find(" ") == -1) and (
                  self.ui.addContactSurnameLineEdit.text().find(" ") == -1) and \
                  (self.ui.addContactLineEdit.text().lower() not in [
                      self.ui.contactListWidget.item(idx).text().lower().split(" ")[0] for idx \
                      in range(self.ui.contactListWidget.count())] or \
                   self.ui.addContactSurnameLineEdit.text().lower() not in [ \
                       self.ui.contactListWidget.item(idx).text().lower().split(" ")[1] for idx \
                       in range(self.ui.contactListWidget.count())] \
                   )
        self.ui.addContactButton.setEnabled(isValid)

    def onContactListChanged(self):
        self.ui.contactListWidget.clear()
        self.ui.contactListWidget.addItems([x[0] + " " + x[1] for x in self.m_database.contactList()])


    def onAddContactPressed(self):
        self.m_database.addContact(self.ui.addContactLineEdit.text(), self.ui.addContactSurnameLineEdit.text())

    def contactsListSelectionChanged(self):
        sel = self.ui.contactListWidget.selectedItems()
        model = self.ui.contactAddressTable.model()
        if len(sel) != 1:
            self.ui.contactNameEdit.setText("")
            self.ui.contactSurnameEdit.setText("")
            self.ui.contactDepartmentEdit.setText("")
            self.ui.contactPositionEdit.setText("")
            self.ui.contactRoleEdit.setText("")
            model.setContactId(0)
            model.fetchData()
            self.ui.contactSaveButton.setEnabled(False)
            self.ui.contactAddressTableSaveButton.setEnabled(False)
            self.ui.contactResetButton.setEnabled(False)
            self.ui.contactAddressTableResetButton.setEnabled(False)

            self.ui.contactNameEdit.setEnabled(False)
            self.ui.contactSurnameEdit.setEnabled(False)
            self.ui.contactDepartmentEdit.setEnabled(False)
            self.ui.contactPositionEdit.setEnabled(False)
            self.ui.contactRoleEdit.setEnabled(False)

            self.ui.contactAddressTable.setEnabled(False)

            return
        else:
            self.ui.contactSaveButton.setEnabled(True)
            self.ui.contactAddressTableSaveButton.setEnabled(True)
            self.ui.contactResetButton.setEnabled(True)
            self.ui.contactAddressTableResetButton.setEnabled(True)

            self.ui.contactNameEdit.setEnabled(True)
            self.ui.contactSurnameEdit.setEnabled(True)
            self.ui.contactDepartmentEdit.setEnabled(True)
            self.ui.contactPositionEdit.setEnabled(True)
            self.ui.contactRoleEdit.setEnabled(True)

            self.ui.contactAddressTable.setEnabled(True)

        item = sel[0]

        names = item.text().split(" ")
        id, name, surname, department, position, role = self.m_database.contactInfo(names[0], names[1])
        self.ui.contactNameEdit.setText(name)
        self.ui.contactSurnameEdit.setText(surname)
        self.ui.contactDepartmentEdit.setText(department)
        self.ui.contactPositionEdit.setText(position)
        self.ui.contactRoleEdit.setText(role)

        self.m_currentContactId = id
        model.setContactId(id)
        model.fetchData()

        self.updateContactAddressButtons()


    def saveContactAddresses(self):
        self.ui.contactAddressTable.model().save()
        self.updateContactAddressButtons()


    def resetContactAddresses(self):
        self.ui.contactAddressTable.model().reset()
        self.updateContactAddressButtons()

    def addContactAddress(self):
        selecteds = self.ui.contactAddressTable.table().selectionModel().selectedIndexes()
        if len(selecteds) != 0:
            idx = selecteds[-1].row() + 1
        else:
            idx = self.ui.contactAddressTable.model().rowCount()
        self.ui.contactAddressTable.model().addRow(idx)
        self.ui.contactAddressTable.table().scrollToBottom()


    def deleteContactAddress(self):
        selecteds = self.ui.contactAddressTable.table().selectionModel().selectedIndexes()
        if len(selecteds) == 0:
            return
        self.ui.contactAddressTable.model().deleteRows([sel.row() for sel in selecteds])

    def updateContactAddressButtons(self):
        dirty = self.ui.contactAddressTable.table().model().isModified()
        self.ui.contactAddressTableSaveButton.setEnabled(dirty)
        self.ui.contactAddressTableResetButton.setEnabled(dirty)


    def onSaveContactPressed(self):
        try:
            name, surname, department, position, role = self.ui.contactNameEdit.text(), self.ui.contactSurnameEdit.text(), \
                                                        self.ui.contactDepartmentEdit.text(), self.ui.contactPositionEdit.text(), \
                                                        self.ui.contactRoleEdit.text()

            self.m_database.saveContactData(name, surname, department, position, role)
        except Exception as e:
            print(e)


    def onResetContactPressed(self):
        sel = self.ui.contactListWidget.selectedItems()
        if len(sel) != 1:
            return
        item = sel[0]

        names = item.text().split(" ")
        id, name, surname, department, position, role = self.m_database.contactInfo(names[0], names[1])
        self.ui.contactNameEdit.setText(name)
        self.ui.contactSurnameEdit.setText(surname)
        self.ui.contactDepartmentEdit.setText(department)
        self.ui.contactPositionEdit.setText(position)
        self.ui.contactRoleEdit.setText(role)

