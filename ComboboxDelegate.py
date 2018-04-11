
from PyQt5.QtWidgets import QItemDelegate
from PyQt5.QtWidgets import QComboBox
from PyQt5.QtCore import Qt

class ComboDelegate(QItemDelegate):
    def __init__(self, items, parent):
        super(ComboDelegate, self).__init__(parent)
        self.comboItems = items

    def createEditor(self, parent, option, proxyModelIndex):
        combo = QComboBox(parent)
        combo.addItems(self.comboItems)
        # combo.setEditable(True)
        combo.currentIndexChanged.connect(self.currentIndexChanged)
        return combo

    def setModelData(self, combo, model, index):
        comboIndex = combo.currentIndex()
        text = self.comboItems[comboIndex]
        model.setData(index, text, Qt.EditRole)

    def currentIndexChanged(self):
        self.commitData.emit(self.sender())