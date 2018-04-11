
from Value import Value
from PyQt5.QtCore import QObject
from PyQt5.QtCore import pyqtSignal

class TableMetadataBase(QObject):

    changedSignal = pyqtSignal(str)

    def __init__(self):
        super(TableMetadataBase, self).__init__()

    def modifiedValue(self, attrName):
        return getattr(getattr(self, attrName), "modifiedValue")

    def setModified(self, attrName, value):
        if getattr(getattr(self, attrName), "modifiedValue") != value:
            setattr(getattr(self, attrName), "modifiedValue", value)
            self.changedSignal.emit(attrName)

    def setAttr(self, attrName, value):
        if getattr(getattr(self, attrName), "modifiedValue") != value:
            setattr(getattr(self, attrName), "modifiedValue", value)
            setattr(getattr(self, attrName), "originalValue", value)
            self.changedSignal.emit(attrName)

    def isModified(self):
        members = [attr for attr in dir(self) if not callable(getattr(self, attr)) and isinstance(getattr(self, attr), Value)]
        for member in members:
            if str(getattr(self, member).originalValue) != str(getattr(self, member).modifiedValue):
                return True

        return False

    def reset(self):
        members = [attr for attr in dir(self) if
                   not callable(getattr(self, attr)) and isinstance(getattr(self, attr), Value)]
        for member in members:
            val = getattr(self, member)
            self.setModified(member, val.originalValue)

    def commit(self):
        members = [attr for attr in dir(self) if
                   not callable(getattr(self, attr)) and isinstance(getattr(self, attr), Value)]
        for member in members:
            val = getattr(self, member)
            val.originalValue = val.modifiedValue

        self.changedSignal.emit("unknown")

    def copyFrom(self, other):
        members = [attr for attr in dir(self) if
                   not callable(getattr(self, attr)) and isinstance(getattr(self, attr), Value)]
        for member in members:
            setattr(self, member, getattr(other, member))

        self.changedSignal.emit("unknown")

class TableMetadata(TableMetadataBase):
    def __init__(self):
        super(TableMetadata, self).__init__()
        self.tableName = Value("")
        self.title = Value("")
        self.alternativeTitle = Value("")
        self.description = Value("")
        self.abstract = Value("")
        self.theme = Value("")
        self.hierarchy = Value(0)

        self.temporalRangeStartDate = Value("")
        self.temporalRangeEndDate = Value("")
        self.temporalRangeUpdates = Value("")
        self.temporalRangeStatus = Value("")
        self.language = Value("")

        self.contactId = Value(0)

        self.schemaExtentsType = None
        self.westLong = Value("")
        self.eastLong = Value("")
        self.southLat = Value("")
        self.northLat = Value("")


        self.dataType = Value("")  # +
        self.precisionResolution = Value("") # +
        self.lineageStatement = Value("")
        self.lineageMaintain = Value("")

        self.referenceSystem = Value("")
        self.charset = Value("")

        self.updateDateStamp = Value("")

        self.keywords = Value("")
        self.onlineURL = Value("")

        self.tableId = 0
        self.resId = 0
        self.geometryColumn = ""

class TableDataPolicy(TableMetadataBase):
    def __init__(self):
        super(TableDataPolicy, self).__init__()
        self.dataAccess = Value("")
        self.copyright = Value("")
        self.useRight = Value("")
        self.classification = Value("")
        self.referenceDate = Value("")
        self.tableId = 0
        self.resId = 0
