
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QPlainTextEdit
from PyQt5.QtWidgets import QComboBox
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QObject

class QLineEditAdaptor:
    def __init__(self, lineEdit):
        self.m_lineEdit = lineEdit

    def value(self):
        return self.m_lineEdit.text()

    def setValue(self, value):
        self.m_lineEdit.setText(value)

    def changedSignal(self):
        return self.m_lineEdit.textChanged

class QPlainTextEditAdaptor:
    def __init__(self, plainEdit):
        self.m_plainEdit = plainEdit

    def value(self):
        return self.m_plainEdit.toPlainText()

    def setValue(self, value):
        self.m_plainEdit.setPlainText(value)

    def changedSignal(self):
        return self.m_plainEdit.textChanged

class QComboBoxdaptor:
    def __init__(self, combo):
        self.m_combo = combo

    def value(self):
        return self.m_combo.currentText()

    def setValue(self, value):
        self.m_combo.setCurrentText(value)

    def changedSignal(self):
        return self.m_combo.currentTextChanged

def qtFieldAdaptor(widget):
    if type(widget) == QLineEdit:
        return QLineEditAdaptor(widget)
    if type(widget) == QPlainTextEdit:
        return QPlainTextEditAdaptor(widget)
    elif isinstance(widget, QComboBox):
        return QComboBoxdaptor(widget)
    else:
        print("Error")
        assert False

class VariableGroupController(QObject):
    def __init__(self, saveBtn, resetBtn, dbPropertyName, database, *args):
        super(VariableGroupController, self).__init__()
        self.m_fields = []
        for arg in args:
            self.m_fields.append(qtFieldAdaptor(arg))

        self.m_saveBtn = saveBtn
        self.m_resetBtn = resetBtn
        self.m_dbPropertyName = dbPropertyName
        self.m_database = database

        self.init()

    saved = pyqtSignal()

    def init(self):
        self.m_saveBtn.pressed.connect(self.save)
        self.m_resetBtn.pressed.connect(self.reset)

        self.m_cache = getattr(self.m_database, self.m_dbPropertyName)

        if len(self.m_cache) != len(self.m_fields):
            raise Exception("Programming Error")

        for idx in range(len(self.m_cache)):
            self.m_fields[idx].setValue(self.m_cache[idx])
            self.m_fields[idx].changedSignal().connect(self.updateButtonState)

        self.updateButtonState()

    def data(self):
        return tuple(x.value() for x in self.m_fields)

    def updateButtonState(self):
        enable = (self.data() != self.m_cache)
        self.m_saveBtn.setEnabled(enable)
        self.m_resetBtn.setEnabled(enable)

    def save(self):
        self.m_cache = self.data()
        setattr(self.m_database, self.m_dbPropertyName, self.m_cache)
        self.updateButtonState()
        self.saved.emit()

    def reset(self):
        for idx in range(len(self.m_cache)):
            self.m_fields[idx].setValue(self.m_cache[idx])