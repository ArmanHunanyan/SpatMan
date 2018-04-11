from PyQt5.QtCore import QObject
from PyQt5.QtCore import pyqtSignal
import fnmatch

class TableListWithFiltersController(QObject):

    selectTableNameSignal = pyqtSignal(int, str)
    deselectTableNameSignal = pyqtSignal(int, str)

    def __init__(self, database, schema, connId, listWidget, filterEdit, filterBtn, isModifiedProc, tableListProc):
        super(TableListWithFiltersController, self).__init__()

        self.m_visibleIndices = []
        self.m_filterBtn = filterBtn
        self.m_filterEdit = filterEdit
        self.m_database = database
        self.m_schema = schema
        self.m_connId = connId
        self.m_listWidget = listWidget
        self.m_isModifiedProc = isModifiedProc
        self.m_tableRenamedDuringSave = False
        self.m_tableListProc = tableListProc

        # Modify these members together
        self.setTableNames()
        self.m_filterBtn.pressed.connect(self.doFilter)
        self.m_filterEdit.returnPressed.connect(self.doFilter)
        self.m_database.tableNameChanged.connect(self.renameTable)
        self.m_database.tableListChanged.connect(self.setTableNames)

        self.m_listWidget.selectionModel().selectionChanged.connect(self.tablesListSelectionChanged)

    def renameTable(self, orig, modified):
        for idx in range(self.m_listWidget.count()):
            if self.m_listWidget.item(idx).text() == orig:
                self.m_listWidget.item(idx).setText(modified)
                break
        self.m_tables = self.m_database.schemaTableList(self.m_schema)
        self.m_tableRenamedDuringSave = True

    def filterRenamedTables(self):
        if self.m_tableRenamedDuringSave:
            self.m_tableRenamedDuringSave = False
            self.doFilter(False)

    def setTableNames(self):
        self.m_listWidget.clearSelection()
        self.m_visibleIndices = []
        self.m_listWidget.clear()
        self.m_tables = self.m_tableListProc(self.m_database, self.m_schema, self.m_connId)
        self.doFilter()

    def doFilter(self, promt = True):
        # disconnect deselected signal to not loose information in table
        filter = self.m_filterEdit.text()
        filteredItems = self.m_tables if len(filter) == 0 else fnmatch.filter(self.m_tables, filter)

        if promt:
            lostInfoTables = []
            for idxv in range(len(self.m_visibleIndices)):
                idx = self.m_visibleIndices[idxv]
                if idx is not None:
                    if self.m_listWidget.item(idxv).text() not in filteredItems:
                        if self.m_isModifiedProc(idx):
                            lostInfoTables.append(self.m_listWidget.item(idxv).text())

            if len(lostInfoTables) != 0:
                res = QMessageBox.question(None, 'Filter Tables?',
                                           "All modifications for following tables will be lost \n" +
                                           ("\n").join(lostInfoTables) + "\nDo you want to proceed?",
                                           QMessageBox.Yes, QMessageBox.No)
                if res == QMessageBox.No:
                    return

        # Deselect items that are going to be lost
        for idx in range(self.m_listWidget.count()):
            if self.m_listWidget.item(idx).text() not in filteredItems:
                self.m_listWidget.item(idx).setSelected(False)

        # Update items
        knownIndx = 0
        for table in self.m_tables:
            if table not in filteredItems:
                idx = 0
                while idx < self.m_listWidget.count():
                    if self.m_listWidget.item(idx).text() == table:
                        self.m_listWidget.takeItem(idx)
                        knownIndx = idx
                        break
                    else:
                        idx += 1

            else:
                found = False
                for idx in range(self.m_listWidget.count()):
                    if self.m_listWidget.item(idx).text() == table:
                        found = True
                        break
                if not found:
                    self.m_listWidget.insertItem(knownIndx, table)
                    knownIndx += 1

        # Reconstruct visible indices
        self.m_visibleIndices = [None] * self.m_listWidget.count()

        tableRow = 0
        for idx in range(len(self.m_visibleIndices)):
            if self.m_listWidget.item(idx).isSelected():
                self.m_visibleIndices[idx] = tableRow
                tableRow += 1

    def tablesListSelectionChanged(self, selected, deselected):
        sel = self.m_listWidget.selectionModel().selectedIndexes()

        deselectedIndices = deselected.indexes()
        deselectedIndices.sort(reverse=True)
        for idx in deselectedIndices:
            if self.m_visibleIndices[idx.row()] is not None:
                self.deselectTableNameSignal.emit(self.m_visibleIndices[idx.row()], self.m_listWidget.item(idx.row()).text())
                self.m_visibleIndices[idx.row()] = None

        for idx in selected.indexes():
            self.m_visibleIndices[idx.row()] = -1 # Set uninitialized state

        tableRow = 0
        for idx in range(len(self.m_visibleIndices)):
            if self.m_visibleIndices[idx] is not None:
                if self.m_visibleIndices[idx] == -1:
                    self.selectTableNameSignal.emit(tableRow, self.m_listWidget.item(idx).text())
                self.m_visibleIndices[idx] = tableRow # Set initialized state
                tableRow += 1

    def tables(self):
        return self.m_tables