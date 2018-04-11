
from TableWidget import TableWidget
from ComboboxDelegate import ComboDelegate
from PyQt5.QtWidgets import QItemDelegate
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtGui import QIntValidator
from PyQt5.QtCore import Qt

class DBValueTextEditWithNullsDelegate(QItemDelegate):
    def __init__(self, parent):
        super(DBValueTextEditWithNullsDelegate, self).__init__(parent)

    def createEditor(self, parent, option, proxyModelIndex):
        edit = QLineEdit(parent)
        edit.textChanged.connect(self.textChanged)
        return edit

    def setModelData(self, edit, model, index):
        text = edit.text()
        model.setData(index, text, Qt.EditRole)

    def setEditorData(self, editor, index):
        editor.setText(index.model().data(index, Qt.DisplayRole))
        if editor.text() == "":
            editor.setPlaceholderText("[null]")
        else:
            editor.setPlaceholderText("")

    def textChanged(self):
        edit = self.sender()
        if edit.text() == "":
            edit.setPlaceholderText("[null]")
        else:
            edit.setPlaceholderText("")
        self.commitData.emit(self.sender())

class DBUIntValueTextEditWithNullsDelegate(QItemDelegate):
    def __init__(self, parent):
        super(DBUIntValueTextEditWithNullsDelegate, self).__init__(parent)

    def createEditor(self, parent, option, proxyModelIndex):
        edit = QLineEdit(parent)
        validator = QIntValidator(0, 1000000)
        edit.setValidator(validator)
        edit.textChanged.connect(self.textChanged)
        return edit

    def setModelData(self, edit, model, index):
        text = edit.text()
        model.setData(index, text, Qt.EditRole)

    def setEditorData(self, editor, index):
        editor.setText(str(index.model().data(index, Qt.DisplayRole)))
        if editor.text() == "":
            editor.setPlaceholderText("[null]")
        else:
            editor.setPlaceholderText("")

    def textChanged(self):
        edit = self.sender()
        if edit.text() == "":
            edit.setPlaceholderText("[null]")
        else:
            edit.setPlaceholderText("")
        self.commitData.emit(self.sender())

class TypeComboDelegate(ComboDelegate):
    def __init__(self, parent):
        super(TypeComboDelegate, self).__init__(["date", "varchar", "real", "double precision", "numeric", "decimal", "smallint", "integer", "bigint"], parent)

class ColumnsTableWidget(TableWidget):

    def __init__(self, parent):
        super(ColumnsTableWidget, self).__init__(parent)

    def init(self, visibleColIndices):
        self.m_visibleColIndices = visibleColIndices

        self.table().setItemDelegateForColumn(self.mapColumn(1), DBValueTextEditWithNullsDelegate(self))
        self.table().setItemDelegateForColumn(self.mapColumn(2), TypeComboDelegate(self))
        self.table().setItemDelegateForColumn(self.mapColumn(3), DBUIntValueTextEditWithNullsDelegate(self))
        self.table().setItemDelegateForColumn(self.mapColumn(4), DBUIntValueTextEditWithNullsDelegate(self))
        self.table().setItemDelegateForColumn(self.mapColumn(5), DBValueTextEditWithNullsDelegate(self))
        self.table().setItemDelegateForColumn(self.mapColumn(6), DBValueTextEditWithNullsDelegate(self))
        self.table().setItemDelegateForColumn(self.mapColumn(10), ComboDelegate(["Yes", "No"], self))
        self.table().setItemDelegateForColumn(self.mapColumn(11), ComboDelegate(["Yes", "No"], self))

    def mapColumn(self, idx):
        if self.m_visibleColIndices is None:
            return idx
        else:
            return self.m_visibleColIndices[idx]
