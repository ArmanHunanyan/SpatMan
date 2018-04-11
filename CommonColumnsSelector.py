from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QComboBox
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QGridLayout
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QSpacerItem
from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtWidgets import QCheckBox
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QAbstractTableModel
from PyQt5.QtCore import QDir
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QModelIndex
from PyQt5.QtGui import QIcon

from TableInfo import TableInfo
from ColumnsTableModel import ColumnsTableModelFactory
from ColumnsTableWidget import ColumnsTableWidget
from ModelWithValidators import ModelWithValidatorsFactory

import icons

class AddedColumnseModel(QAbstractTableModel):
    def __init__(self, data):
        super(AddedColumnseModel, self).__init__()
        self.m_data = data

class OtherColumnseModel(QAbstractTableModel):
    def __init__(self, data, database, connId):
        super(OtherColumnseModel, self).__init__()
        self.m_data = []

        columns = database.commonColumnsInfo(connId)

        for col in columns:
            if not col[0] in [d.id() for d in data]:
                self.m_data.append(TableInfo(col[0], False, *col[1:]))
                self.m_data[-1].freez(True)

class CommonColumnsSelector(QDialog):
    def __init__(self, currentCommonColumns, database, connId):
        super(CommonColumnsSelector, self).__init__()

        self.setWindowTitle("CommonColumss")
        self.setWindowIcon(QIcon(":/icons/favicon.ico"))
        self.resize(900, 700)

        self.m_addedColumns = ColumnsTableWidget(self)
        self.m_addedColumns.showBtns(False)
        self.m_otherColumns = ColumnsTableWidget(self)
        self.m_otherColumns.showBtns(False)

        self.m_addedColumns.setModel(ColumnsTableModelFactory(ModelWithValidatorsFactory(AddedColumnseModel))(currentCommonColumns))
        self.m_otherColumns.setModel(ColumnsTableModelFactory(ModelWithValidatorsFactory(OtherColumnseModel))(currentCommonColumns, database, connId))

        self.m_addedColumns.model().initValidators(None)
        self.m_otherColumns.model().initValidators(None)

        self.m_toOtherBtn = QPushButton(">>")
        self.m_toOtherBtn.setFixedWidth(30)
        self.m_toAddedBtn = QPushButton("<<")
        self.m_toAddedBtn.setFixedWidth(30)

        self.m_toOtherBtn.pressed.connect(self.selectedToOther)
        self.m_toAddedBtn.pressed.connect(self.selectedToAdd)
        self.m_addedColumns.table().selectionModel().selectionChanged.connect(
            self.addedColumnsSelectionChanged)
        self.m_otherColumns.table().selectionModel().selectionChanged.connect(
            self.otherColumnsSelectionChanged)
        self.addedColumnsSelectionChanged()
        self.otherColumnsSelectionChanged()

        tableBtnsLayout = QVBoxLayout()
        tableBtnsLayout.addItem(QSpacerItem(5, 1, QSizePolicy.Minimum, QSizePolicy.Expanding))
        tableBtnsLayout.addWidget(self.m_toOtherBtn, 0, Qt.AlignRight)
        tableBtnsLayout.addWidget(self.m_toAddedBtn, 0, Qt.AlignRight)
        tableBtnsLayout.addItem(QSpacerItem(5, 1, QSizePolicy.Minimum, QSizePolicy.Expanding))

        tablesLayout = QHBoxLayout()
        addedLabel = QLabel("Columns to add")
        addedTableLayout = QVBoxLayout()
        addedTableLayout.addWidget(addedLabel)
        addedTableLayout.addWidget(self.m_addedColumns)
        addedTableLayout.setSpacing(9)
        tablesLayout.addItem(addedTableLayout)
        tablesLayout.addItem(tableBtnsLayout)
        otherLabel = QLabel("Common Columns")
        otherTableLayout = QVBoxLayout()
        otherTableLayout.addWidget(otherLabel)
        otherTableLayout.addWidget(self.m_otherColumns)
        otherTableLayout.setSpacing(9)
        tablesLayout.addItem(otherTableLayout)

        okBtn = QPushButton("OK")
        cancelBtn = QPushButton("Cancel")
        okBtn.pressed.connect(self.accept)
        cancelBtn.pressed.connect(self.reject)

        btnsLayout = QHBoxLayout()
        btnsLayout.addItem(QSpacerItem(5, 1, QSizePolicy.Expanding, QSizePolicy.Minimum))
        btnsLayout.addWidget(cancelBtn, 0, Qt.AlignRight)
        btnsLayout.addWidget(okBtn, 0, Qt.AlignRight)

        mainLayout = QVBoxLayout()
        mainLayout.addItem(tablesLayout)
        mainLayout.addItem(btnsLayout)
        self.setLayout(mainLayout)

    def addedColumnsSelectionChanged(self):
        enable = len(self.m_addedColumns.table().selectionModel().selectedIndexes()) != 0
        self.m_toOtherBtn.setEnabled(enable)

    def otherColumnsSelectionChanged(self):
        enable = len(self.m_otherColumns.table().selectionModel().selectedIndexes()) != 0
        self.m_toAddedBtn.setEnabled(enable)

    def selectedToAdd(self):
        selecteds = self.m_otherColumns.table().selectionModel().selectedIndexes()
        indices = list(set([sel.row() for sel in selecteds]))
        indices.sort(reverse=True)
        for idx in indices:
            row = self.m_otherColumns.model().takeRow(idx)
            self.m_addedColumns.model().insertRow(idx, row)

    def selectedToOther(self):
        selecteds = self.m_addedColumns.table().selectionModel().selectedIndexes()
        indices = list(set([sel.row() for sel in selecteds]))
        indices.sort(reverse=True)
        for idx in indices:
            row = self.m_addedColumns.model().takeRow(idx)
            self.m_otherColumns.model().insertRow(idx, row)

    def result(self):
        return self.m_addedColumns.model().m_data

class ColumnsModel2(QAbstractTableModel):
    def __init__(self, database, connId):
        super(ColumnsModel2, self).__init__()
        self.m_data = []

        columns = database.commonColumnsInfo(connId)

        for col in columns:
            self.m_data.append(TableInfo(col[0], False, *col[1:]))
            self.m_data[-1].freez(True)

class CommonColumnsSelector2(QDialog):
    def __init__(self, database, connId):
        super(CommonColumnsSelector2, self).__init__()

        self.setWindowTitle("CommonColumss")
        self.setWindowIcon(QIcon(":/icons/favicon.ico"))
        self.resize(900, 700)

        self.m_columns = ColumnsTableWidget(self)
        self.m_columns.showBtns(False)

        model = ColumnsTableModelFactory(ModelWithValidatorsFactory(ColumnsModel2))(database, connId)
        model.initValidators(None)
        self.m_columns.setModel(model)

        tablesLayout = QHBoxLayout()
        tablesLayout.addWidget(self.m_columns)

        okBtn = QPushButton("OK")
        cancelBtn = QPushButton("Cancel")
        okBtn.pressed.connect(self.accept)
        cancelBtn.pressed.connect(self.reject)

        btnsLayout = QHBoxLayout()
        btnsLayout.addItem(QSpacerItem(5, 1, QSizePolicy.Expanding, QSizePolicy.Minimum))
        btnsLayout.addWidget(cancelBtn, 0, Qt.AlignRight)
        btnsLayout.addWidget(okBtn, 0, Qt.AlignRight)

        mainLayout = QVBoxLayout()
        mainLayout.addItem(tablesLayout)
        mainLayout.addItem(btnsLayout)
        self.setLayout(mainLayout)

    def result(self):
        selecteds = self.m_columns.table().selectionModel().selectedIndexes()
        indices = list(set([sel.row() for sel in selecteds]))
        indices.sort(reverse=False)
        res = []
        for idx in indices:
            res.append(self.m_columns.model().m_data[idx])

        return res