
from PyQt5.QtCore import QObject
from PyQt5.QtCore import QAbstractTableModel
from SqlModel import SqlModelFactory
from TableInfo import TableInfo
from ModelWithValidators import ModelWithValidatorsFactory

class AvailbleServicesModel(QAbstractTableModel):
    def __init__(self, database):
        super(AvailbleServicesModel, self).__init__(None)

        self.m_data = []
        self.m_database = database
        self.m_modified = False
        self.m_columns = ["Description", "URL", "User", "Password", "Max Features"]

    def fetchDataImpl(self):
        infos = self.m_database.availbleServicesInfo()
        if infos is None:
            self.m_data = []
        else:
            self.m_data = list(TableInfo(info[0], False, *info[1:]) for info in infos)

    def saveRowImpl(self, row):
        self.m_database.saveAvailbleServicesInfo(row)

class AvailbleServicesTabController(QObject):

    def __init__(self, ui, database):
        super(AvailbleServicesTabController, self).__init__()
        self.ui = ui
        self.m_database = database
        self.initAvailbleServicesTab()

    def initAvailbleServicesTab(self):
        model = SqlModelFactory(ModelWithValidatorsFactory(AvailbleServicesModel))(self.m_database)
        model.fetchData()

        self.ui.availableServicesTable.setModel(model)

        self.ui.availableServicesTable.addBtn().pressed.connect(self.addService)
        self.ui.availableServicesTable.deleteBtn().pressed.connect(self.deleteService)

        self.ui.availableServicesSaveBtn.pressed.connect(self.saveAvailbleServices)
        self.ui.availableServicesResetBtn.pressed.connect(self.resetAvailbleServices)

        self.ui.availableServicesTable.model().modified.connect(self.updateAvailbleServicesButtons)
        self.ui.availableServicesTable.model().dataChanged.connect(self.updateAvailbleServicesButtons)
        self.updateAvailbleServicesButtons()

    def updateAvailbleServicesButtons(self):
        dirty = self.ui.availableServicesTable.table().model().isModified()
        self.ui.availableServicesSaveBtn.setEnabled(dirty)
        self.ui.availableServicesResetBtn.setEnabled(dirty)

    def saveAvailbleServices(self):
        self.ui.availableServicesTable.table().model().save()
        self.updateAvailbleServicesButtons()

    def resetAvailbleServices(self):
        self.ui.availableServicesTable.table().model().reset()
        self.updateAvailbleServicesButtons()

    def addService(self):
        selecteds = self.ui.availableServicesTable.table().selectionModel().selectedIndexes()
        if len(selecteds) != 0:
            idx = selecteds[-1].row() + 1
        else:
            idx = self.ui.availableServicesTable.model().rowCount()
        self.ui.availableServicesTable.model().addRow(idx)
        self.ui.availableServicesTable.table().scrollToBottom()

    def deleteService(self):
        selecteds = self.ui.availableServicesTable.table().selectionModel().selectedIndexes()
        if len(selecteds) == 0:
            return
        self.ui.availableServicesTable.model().deleteRows([sel.row() for sel in selecteds])

