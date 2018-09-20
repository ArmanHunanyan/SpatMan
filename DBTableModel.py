
from PyQt5.QtCore import QModelIndex
from PyQt5.QtCore import Qt
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QVariant
from PyQt5.QtGui import QPixmap
from PyQt5.QtGui import QColor

from TableInfo import TableInfo

# This class is used to wrap functionality which draws * if row is newely added and ! if row is deleted.
def AddDeleteMarkerModelFactory(baseClass):

    class AddDeleteMarkerModel(baseClass):

        def __init__(self, *args):
            super(AddDeleteMarkerModel, self).__init__(*args)

        # Requirments:

        # Must return list of column names
        # def columns(self):

        # Must return list of rows
        # def rows(self):

        # Must return True if row is added and not yet commited
        # def rowIsAdded(self, idx):

        # Must return True if row is deleted and not yet commited
        # def rowIsDeleted(self, idx):

        # Implementation
        def headerData(self, section, orientation, role):
            if role == Qt.DisplayRole and orientation == Qt.Horizontal:
                return self.columns()[section]
            elif role == Qt.DisplayRole and orientation == Qt.Vertical:
                if self.rowIsAdded(section):
                    return "*"
                elif self.rowIsDeleted(section):
                    return "!"
                else:
                    return str(section)

            return super(AddDeleteMarkerModel, self).headerData(section, orientation, role)

        def rowCount(self, parent=None):
            return len(self.rows())

        def columnCount(self, parent=None):
            return len(self.columns())

    return AddDeleteMarkerModel

# This class is used to wrap functionality which paints modified and not commited cells in special color
# This also paints invalid values in special color
def DataChangeMarkerModelFactory(baseClass):

    class DataChangeMarkerModel(baseClass):

        def __init__(self, *args):
            super(DataChangeMarkerModel, self).__init__(*args)

        # Requirments:

        # Must return True if cell's current value is invalid
        # def cellIsValid(self, index):

        # Must return True if cells current value is changed and not commited
        # def cellIsModified(self, index):

        # Implementation
        def data(self, item, role):
            if not item.isValid():
                return None

            if role == Qt.BackgroundRole:
                if not self.cellIsValid(item):
                    return QColor(255, 0, 0)
                elif self.cellIsModified(item):
                    return QColor(255, 165, 0)

            return super(DataChangeMarkerModel, self).data(item, role)

    return DataChangeMarkerModel