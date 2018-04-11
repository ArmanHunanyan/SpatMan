
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

def ModelWithValidatorsFactory(baseClass):
    class ModelWithValidators(baseClass):
        def __init__(self, *args):
            super(ModelWithValidators, self).__init__(*args)
            self.m_validators = []
            self.m_isEditableColumnProcs = []
            self.m_isEditable = None
            self.m_callbacks = []
            self.m_validity = None

        def value(self, row, column):
            return super(ModelWithValidators, self).data(self.createIndex(row, column), Qt.EditRole)

        def data(self, item, role):
            if not item.isValid():
                return None

            if role == Qt.BackgroundRole:
                if not self.validate(item.row(), item.column(), super(ModelWithValidators, self).data(item, Qt.EditRole)):
                    return QColor(255, 0, 0)
                elif self.isDirty(item):
                    return QColor(255, 165, 0)

            return None

        def validate(self, row, column, data):
            if (column < len(self.m_validators)):
                validator = self.m_validators[column]
                if validator is not None:
                    return validator(self, row, data)

            return True

        def globallyEditable(self, row):
            if self.m_isEditable is None:
                return True
            else:
                return self.m_isEditable(self, row)

        def isEditable(self, row, column, data):
            if (column < len(self.m_isEditableColumnProcs)):
                isEditableProc = self.m_isEditableColumnProcs[column]
                if isEditableProc is not None:
                    return self.globallyEditable(row) and isEditableProc(self, row, data)

            return self.globallyEditable(row)

        def callback(self, row, column, data):
            if (column < len(self.m_callbacks)):
                callbackProc = self.m_callbacks[column]
                if callbackProc is not None:
                    return callbackProc(self, row, data)

            return True

        def setColumnValidator(self, idx, proc):
            if idx >= len(self.m_validators):
                self.m_validators += [None]*(idx + 1 - len(self.m_validators))
            self.m_validators[idx] = proc

        def setColumnEditableProc(self, idx, proc):
            if idx >= len(self.m_isEditableColumnProcs):
                self.m_isEditableColumnProcs += [None] * (idx + 1 - len(self.m_isEditableColumnProcs))
            self.m_isEditableColumnProcs[idx] = proc

        def setEditableProc(self, proc):
            self.m_isEditable = proc

        def setColumnCallback(self, idx, proc):
            if idx >= len(self.m_callbacks):
                self.m_callbacks += [None]*(idx + 1 - len(self.m_callbacks))
            self.m_callbacks[idx] = proc

        def setData(self, index, value, role):
            # Don't flag cell as changed when it hasn't
          #  if role == Qt.EditRole and index.data(Qt.DisplayRole) == value:
           #     return False
            if role == Qt.EditRole:
                self.callback(index.row(), index.column(), value)
            return super(ModelWithValidators, self).setData(index, value, role)


        def flags(self, index):
            if self.isEditable(index.row(), index.column(), super(ModelWithValidators, self).data(index, Qt.EditRole)):
                return super(ModelWithValidators, self).flags(index) | Qt.ItemIsEditable
            else:
                return super(ModelWithValidators, self).flags(index) & ~Qt.ItemIsEditable

    return ModelWithValidators
