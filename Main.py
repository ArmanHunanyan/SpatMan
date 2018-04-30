
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QMenu
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QStatusBar
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

from Database import Database
from Database import testConnection
from Database import WrongUserPass
from LoginDialog import LoginDialog
from Configuration import Configuration
from CurrentSchemaController import CurrentSchemaController
from VariableGroupController import VariableGroupController
from AvailbleServicesTabController import AvailbleServicesTabController
from ContactsTabController import ContactsTabController

from ui.SpatManMainUI import Ui_SpatMan

import sys
import os

class MainWindow(QDialog):
    def __init__(self, database):
        super(MainWindow, self).__init__()
        self.setWindowTitle("SpatMan")
        self.setWindowIcon(QIcon(":/icons/favicon.ico"))
        self.ui = Ui_SpatMan()
        self.ui.setupUi(self)
        self.setWindowFlags(Qt.Window)
        self.m_statusBar = QStatusBar()
        self.ui.dialogBottonHorizontalLayout.insertWidget(0, self.m_statusBar)
        self.m_database = database
        self.initUsersTab()
        self.initGeneralTab()
        self.m_availbleServicesTabController = AvailbleServicesTabController(self.ui, self.m_database)
        self.m_contactsTabController = ContactsTabController(self.ui, self.m_database)
        self.initConfigurationTab()
        self.ui.quitButton.pressed.connect(QApplication.instance().quit)
        self.m_currentSchemaController = CurrentSchemaController(self, self.ui, database)
        self.ui.progressBar.hide()
        config = Configuration()

        if config.currentSchema() is not None:
            try:
                self.setCurrentSchema(config.currentSchema())
            except Exception as e:
                print(e)
                QMessageBox.information(self, "Schema error", "Failed to load schema '%s'" % config.currentSchema())
                self.ui.mainTabWidget.setCurrentWidget(self.ui.configuration)

        # Checking if ogr2ogr dir is specifyed
        ogr2ogrDir = config.ogr2ogrDir()
        if ogr2ogrDir is None or ogr2ogrDir == "":
            ogr2ogrDir = "C:\\OSGeo4W64\\bin"

        if not os.path.exists(os.path.join(ogr2ogrDir, "ogr2ogr.exe")):
            res = QMessageBox.question(self, 'ogr2ogr path',
                                       "Cannot find ogr2ogr path in following directory:\n\t\t%s\n \n"
                                       "Do you want to spefify directory to ogr2ogr executable?\n" % ogr2ogrDir,
                                       QMessageBox.Yes, QMessageBox.No)
            if res == QMessageBox.Yes:
                path = QFileDialog.getExistingDirectory(self, "Path to ogr2ogr executable")
                if os.path.exists(os.path.join(path, "ogr2ogr.exe")):
                    config.setOgr2ogrDir(path)
            else:
                config.setOgr2ogrDir(None)

        # Checking if gdal data dir is specifyed
        gdalData = config.gdalDataDir()
        if gdalData is None or gdalData == "" or not os.path.exists(gdalData):
            res = QMessageBox.question(self, 'GDAL_DATA path',
                                       "GDAL_DATA path is not exists:\n\n"
                                       "Do you want to spefify new GDAL_DATA path?\n",
                                       QMessageBox.Yes, QMessageBox.No)
            if res == QMessageBox.Yes:
                path = QFileDialog.getExistingDirectory(self, "Path to GDAL_DATA")
                if os.path.exists(path):
                    config.setGdalDataDir(path)
            else:
                config.setGdalDataDir(None)

    # Users tab related
    def initUsersTab(self):
        self.ui.userListWidget.addItems(self.m_database.userList())
        self.m_database.userListChangedSignal.connect(self.onUserListChanged)
        self.ui.addUserButton.pressed.connect(self.onAddUserPressed)
        self.ui.userListWidget.itemSelectionChanged.connect(self.usersListSelectionChanged)
        self.ui.saveUserButton.pressed.connect(self.onSaveUserPressed)
        self.ui.resetUserButton.pressed.connect(self.onResetUserPressed)
        self.ui.addUserLineEdit.textEdited.connect(self.updateAddUserBtnState)
        self.ui.userListWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.userListWidget.model().rowsInserted.connect(self.updateAddUserBtnState)
        self.ui.userListWidget.model().rowsRemoved.connect(self.updateAddUserBtnState)
        self.ui.userListWidget.customContextMenuRequested.connect(self.userListContextMenu)

        self.updateAddUserBtnState()
        self.usersListSelectionChanged()

    def userListContextMenu(self, point):
        globalPos = self.ui.userListWidget.mapToGlobal(point)
        menu = QMenu()
        menu.addAction("Delete", self.deleteSelectedUser)
        menu.exec(globalPos)

    def deleteSelectedUser(self):
        sel = self.ui.userListWidget.selectedItems()
        if len(sel) == 1:
            item = sel[0]
            res = QMessageBox.question(self, 'Delete user?',
                     "Delete user '%s' from database? \n"
                     "All information about user will be discarded" % item.text(),
                                       QMessageBox.Yes, QMessageBox.No)
            if res == QMessageBox.Yes:
                self.m_database.deleteUser(item.text())

    def updateAddUserBtnState(self):
        isValid = len(self.ui.addUserLineEdit.text()) != 0 and \
                    (self.ui.addUserLineEdit.text().lower() not in [self.ui.userListWidget.item(idx).text().lower() for idx in range(self.ui.userListWidget.count())])
        self.ui.addUserButton.setEnabled(isValid)

    def onUserListChanged(self):
        self.ui.userListWidget.clear()
        self.ui.userListWidget.addItems(self.m_database.userList())

    def onAddUserPressed(self):
        self.m_database.addUser(self.ui.addUserLineEdit.text())

    def usersListSelectionChanged(self):
        sel = self.ui.userListWidget.selectedItems()
        if len(sel) != 1:
            self.ui.passwordEdit.setText("")
            self.ui.isAdminCheckBox.setChecked(False)
            self.ui.userNameEdit.setText("")
            
            self.ui.saveUserButton.setEnabled(False)
            self.ui.resetUserButton.setEnabled(False)
            self.ui.passwordEdit.setEnabled(False)
            self.ui.isAdminCheckBox.setEnabled(False)
            self.ui.userNameEdit.setEnabled(False)
            return
        else:
            self.ui.saveUserButton.setEnabled(True)
            self.ui.resetUserButton.setEnabled(True)
            self.ui.passwordEdit.setEnabled(True)
            self.ui.isAdminCheckBox.setEnabled(True)
            self.ui.userNameEdit.setEnabled(True)
        item = sel[0]

        self.ui.userNameEdit.setText(item.text())
        passwd, isAdmin = self.m_database.userInfo(item.text())
        self.ui.isAdminCheckBox.setChecked(isAdmin)

    def onSaveUserPressed(self):
        passwd = self.ui.passwordEdit.text()
        isAdmin = self.ui.isAdminCheckBox.isChecked()
        userName = self.ui.userNameEdit.text()
        self.m_database.saveUserData(userName, passwd, isAdmin)
        self.ui.passwordEdit.setText("")
        self.ui.isAdminCheckBox.setChecked(False)
        self.ui.userNameEdit.setText("")

    def onResetUserPressed(self):
        sel = self.ui.userListWidget.selectedItems()
        if len(sel) != 1:
            return
        item = sel[0]

        passwd, isAdmin = self.m_database.userInfo(item.text())
        self.ui.isAdminCheckBox.setChecked(isAdmin)
        self.ui.passwordEdit.setText("")

    # General tab related
    def initGeneralTab(self):
        self.m_globalTableUsagePolicyGroupController = VariableGroupController(
            self.ui.saveGlobalTableUsagePolicyButton, self.ui.resetGlobalTableUsagePolicyButton,
            "globalTableUsagePolicy", self.m_database,
            self.ui.dataAccessPolicyEdit, self.ui.copyrightEdit, self.ui.userRightEdit,
            self.ui.classificationCombo)

        self.m_globalNamingConvGroupController = VariableGroupController(
            self.ui.saveGlobalNamingConvButton, self.ui.resetGlobalNamingConvButton,
            "globalNamingConv", self.m_database,
            self.ui.spatialTablePrefixEdit, self.ui.nonSpatialTablePrefixEdit, self.ui.systemTablePrefixEdit,
            self.ui.lookupTablePrefixEdit, self.ui.linkTablePrefixEdit, self.ui.uidColumnNameEdit,
            self.ui.geometryColumnNameEdit, self.ui.rasterColumnNameEdit)

        self.m_globalNamingConvGroupController.saved.connect(self.globalNamingConvSaved)

        self.m_generalSettingsGroupController = VariableGroupController(
            self.ui.saveGeneralSettingsBtn, self.ui.resetGeneralSettingsBtn,
            "generalSettings", self.m_database,
            self.ui.orgNameEdit, self.ui.phoneNumberEdit, self.ui.emailEdit,
            self.ui.mainAddress1Edit, self.ui.mainAddress2Edit, self.ui.mainAddress3Edit,
            self.ui.postalCodeEdit)

        self.m_otherGeneralGroupController = VariableGroupController(
            self.ui.saveOtherGeneralBtn, self.ui.resetOtherGeneralBtn,
            "otherGeneral", self.m_database,
            self.ui.encryptionSaltEdit, self.ui.notesEdit)

    def globalNamingConvSaved(self):
        if self.m_currentSchemaController.currentSchemaId() is not None:
            self.m_currentSchemaController.constructCreateTableTab()

    # Configuration tab related
    def initConfigurationTab(self):
        self.onConnectionListChanged()
        self.m_database.connectionListChangedSignal.connect(self.onConnectionListChanged)
        self.ui.addConnectionButton.pressed.connect(self.onAddConnectionPressed)
        self.ui.connectionListWidget.itemSelectionChanged.connect(self.connectionListSelectionChanged)
        self.connectionListSelectionChanged()
        self.ui.connSaveButton.pressed.connect(self.onSaveConnectionPressed)
        self.ui.connResetButton.pressed.connect(self.onResetConnectionPressed)
        self.ui.connTestButton.pressed.connect(self.onTestConnectionPressed)
        self.ui.addConnectionEdit.textEdited.connect(self.updateAddConnectionBtnState)
        self.updateAddConnectionBtnState()
        self.ui.connectionListWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.connectionListWidget.model().rowsInserted.connect(self.updateAddConnectionBtnState)
        self.ui.connectionListWidget.model().rowsRemoved.connect(self.updateAddConnectionBtnState)
        self.ui.connectionListWidget.customContextMenuRequested.connect(self.connectionListContextMenu)
        self.ui.setCurrentSchemaButton.pressed.connect(self.setSelectedAsCurrentSchema)

        self.ui.connPortCheckBox.toggled.connect(self.ui.connPortEdit.setEnabled)

    def setSelectedAsCurrentSchema(self):
        sel = self.ui.connectionListWidget.selectedItems()
        if len(sel) != 1:
            return
        item = sel[0]

        schema = item.text()
        self.setCurrentSchema(schema)
        config = Configuration()
        config.setCurrentSchema(schema)

    def setCurrentSchema(self, schema):
        id, schema, active, dbType, host, port, dbName, user, password = self.m_database.connectionInfo(schema)
        self.m_currentSchemaController.setCurrent(id, schema, active, dbType, host, port, dbName, user, password)

    def connectionListContextMenu(self, point):
        globalPos = self.ui.connectionListWidget.mapToGlobal(point)
        menu = QMenu()
        menu.addAction("Delete", self.deleteSelectedConnection)
        menu.exec(globalPos)

    def deleteSelectedConnection(self):
        sel = self.ui.connectionListWidget.selectedItems()
        if len(sel) == 1:
            item = sel[0]
            if item.text() == self.m_currentSchemaController.currentSchemaName():
                QMessageBox.information(self, "Delete Error", "Cannot delete current schema.\n Please change current schema before deleting this one.")
                return
            res = QMessageBox.question(self, 'Delete connection?',
                                       "Delete connection '%s' from database? \n"
                                       "All information about connection will be discarded" % item.text(),
                                       QMessageBox.Yes, QMessageBox.No)
            if res == QMessageBox.Yes:
                name = item.text()
                self.m_database.deleteConnection(name)

    def updateAddConnectionBtnState(self):
        isValid = len(self.ui.addConnectionEdit.text()) != 0 and \
                  (
                  self.ui.addConnectionEdit.text().lower() not in [self.ui.connectionListWidget.item(idx).text().lower() for
                                                                 idx in range(self.ui.connectionListWidget.count())])
        self.ui.addConnectionButton.setEnabled(isValid)

    def onConnectionListChanged(self):
        self.ui.connectionListWidget.clear()
        self.ui.connectionListWidget.addItems(self.m_database.connectionList())

    def onAddConnectionPressed(self):
        self.m_database.addConnection(self.ui.addConnectionEdit.text())

    def connectionListSelectionChanged(self):
        sel = self.ui.connectionListWidget.selectedItems()
        if len(sel) != 1:
            self.ui.connActiveCombo.setCurrentIndex(-1)
            self.ui.connDbTypeCombo.setCurrentIndex(-1)
            self.ui.connHostEdit.setText("")
            self.ui.connPortEdit.setValue(0)
            self.ui.connPortCheckBox.setChecked(False)
            self.ui.connDatabaseEdit.setText("")
            self.ui.connSchemaEdit.setText("")
            self.ui.connUserEdit.setText("")
            self.ui.connPasswordEdit.setText("")

            self.ui.connSaveButton.setEnabled(False)
            self.ui.connTestButton.setEnabled(False)
            self.ui.connResetButton.setEnabled(False)
            self.ui.setCurrentSchemaButton.setEnabled(False)

            self.ui.connActiveCombo.setEnabled(False)
            self.ui.connDbTypeCombo.setEnabled(False)
            self.ui.connHostEdit.setEnabled(False)
            self.ui.connPortCheckBox.setEnabled(False)
            self.ui.connPortEdit.setEnabled(False)
            self.ui.connDatabaseEdit.setEnabled(False)
            self.ui.connSchemaEdit.setEnabled(False)
            self.ui.connUserEdit.setEnabled(False)
            self.ui.connPasswordEdit.setEnabled(False)

            return
        else:
            self.ui.connSaveButton.setEnabled(True)
            self.ui.connTestButton.setEnabled(True)
            self.ui.connResetButton.setEnabled(True)
            self.ui.setCurrentSchemaButton.setEnabled(True)

            self.ui.connActiveCombo.setEnabled(True)
            self.ui.connDbTypeCombo.setEnabled(True)
            self.ui.connHostEdit.setEnabled(True)
            self.ui.connPortCheckBox.setEnabled(True)
            self.ui.connDatabaseEdit.setEnabled(True)
            self.ui.connSchemaEdit.setEnabled(True)
            self.ui.connUserEdit.setEnabled(True)
            self.ui.connPasswordEdit.setEnabled(True)

        item = sel[0]

        schema = item.text()
        id, schema, active, dbType, host, port, dbName, user, password = self.m_database.connectionInfo(schema)
        print(id, schema, active, dbType, host, port, dbName, user, password)
        self.ui.connActiveCombo.setCurrentIndex(self.ui.connActiveCombo.findText(active))
        self.ui.connDbTypeCombo.setCurrentIndex(self.ui.connDbTypeCombo.findText(dbType))
        self.ui.connHostEdit.setText(host)
        self.ui.connPortCheckBox.setChecked(port is not None)
        if port is not None:
            self.ui.connPortEdit.setValue(port)
        else:
            self.ui.connPortEdit.setValue(0)
        self.ui.connDatabaseEdit.setText(dbName)
        self.ui.connSchemaEdit.setText(schema)
        self.ui.connUserEdit.setText(user)
        self.ui.connPasswordEdit.setText(password)

    def onSaveConnectionPressed(self):
        active, dbType, host, port, dbName, schema, user, password = self.ui.connActiveCombo.currentText(), \
                                self.ui.connDbTypeCombo.currentText(), self.ui.connHostEdit.text(), \
                                self.ui.connPortEdit.value() if self.ui.connPortCheckBox.isChecked() else None, \
                                self.ui.connDatabaseEdit.text(), self.ui.connSchemaEdit.text(), \
                                self.ui.connUserEdit.text(), self.ui.connPasswordEdit.text()

        self.m_database.saveConnectionData(schema, active, dbType, host, port, dbName, user, password)
        self.m_statusBar.showMessage("Connection '%s' successfully saved" % schema, 2000)

    def onResetConnectionPressed(self):
        sel = self.ui.connectionListWidget.selectedItems()
        if len(sel) != 1:
            return
        item = sel[0]

        schema = item.text()
        id, schema, active, dbType, host, port, dbName, user, password = self.m_database.connectionInfo(schema)
        self.ui.connActiveCombo.setCurrentText(active)
        self.ui.connDbTypeCombo.setCurrentText(dbType)
        self.ui.connHostEdit.setText(host)
        self.ui.connPortCheckBox.setChecked(port is not None)
        if port is not None:
            self.ui.connPortEdit.setValue(port)
        self.ui.connDatabaseEdit.setText(dbName)
        self.ui.connSchemaEdit.setText(schema)
        self.ui.connUserEdit.setText(user)
        self.ui.connPasswordEdit.setText(password)

    def onTestConnectionPressed(self):
        active, dbType, host, dbName, schema, user, password = self.ui.connActiveCombo.currentText(), \
                                                               self.ui.connDbTypeCombo.currentText(), self.ui.connHostEdit.text(), \
                                                               self.ui.connDatabaseEdit.text(), self.ui.connSchemaEdit.text(), \
                                                               self.ui.connUserEdit.text(), self.ui.connPasswordEdit.text()
        if testConnection(active, dbType, host, dbName, schema, user, password):
            QMessageBox.information(self, "Connection test", "Connection is valid")
        else:
            QMessageBox.warning(self, "Connection test", "Connection is not valid")

sys._excepthook = sys.excepthook
def exception_hook(exctype, value, traceback):
    sys._excepthook(exctype, value, traceback)
    sys.exit(1)
sys.excepthook = exception_hook

def main():
    app = QApplication(sys.argv)

    while True:
        loginDialog = LoginDialog()
        if loginDialog.exec() == LoginDialog.Rejected:
            return
        db, userName,  password = loginDialog.result()

        try:
            database = Database(db, userName, password)
            break
        except WrongUserPass as e:
            QMessageBox.warning(None, "Error", "Wrong username or password")
            continue
        except Exception as e:
            QMessageBox.warning(None, "Error", "Failed to open database: \n" + str(e))
            return

    config = Configuration()
    config.addRecentDB(db)

    wnd = MainWindow(database)
    wnd.show()
    res = app.exec_()
    try:
        config.save()
    except Exception as e:
        print("Error: %s" % str(e))
    return res;

main()