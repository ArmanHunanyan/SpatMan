
from PyQt5.QtWidgets import QComboBox

class MappingComboBox(QComboBox):
    def __init__(self, parent):
        super(MappingComboBox, self).__init__(parent)
        self.m_items = None

    def addItems(self, items):
        self.m_items = items
        super(MappingComboBox, self).addItems([x[0] for x in items])

    def currentText(self):
        if self.m_items is None:
            return None

        txt = super(MappingComboBox, self).currentText()

        for x in self.m_items:
            if x[0] == txt:
                return str(x[1])

        return None

    def firstId(self):
        if self.m_items is None:
            return None

        if len(self.m_items) == 0:
            return None

        return str(self.m_items[0][1])

    def setCurrentText(self, value):
        if self.m_items is None:
            return

        txt = None
        for x in self.m_items:
            if str(x[1]) == value:
                txt = x[0]
                break

        if txt is not None:
            super(MappingComboBox, self).setCurrentText(txt)
