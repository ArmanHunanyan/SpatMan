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
from PyQt5.QtCore import QDir
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QIcon

from Configuration import Configuration

import icons

class DatabaseEdit(QWidget):
    def __init__(self):
        super(DatabaseEdit, self).__init__()
        self.m_combo = QComboBox()
        self.m_combo.setEditable(True)
        self.m_btn = QPushButton("...")
        self.m_btn.setFixedWidth(30)
        self.m_btn.pressed.connect(self.browse)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.m_combo)
        layout.addWidget(self.m_btn)

        self.setLayout(layout)

        self.m_combo.currentTextChanged.connect(self.textEdited)

    def browse(self):
        fileName, filter = QFileDialog.getOpenFileName(self, "Database",
                                                       QDir.currentPath())
        if fileName:
            self.m_combo.setEditText(fileName)

    def addToHistory(self, history):
        for item in history:
            self.m_combo.addItem(item)

    def text(self):
        return self.m_combo.currentText()

    textEdited = pyqtSignal()

class LoginDialog(QDialog):
    def __init__(self):
        super(LoginDialog, self).__init__()

        self.setWindowTitle("SpatMan")
        self.setWindowIcon(QIcon(":/icons/favicon.ico"))

        self.m_databaseEdit = DatabaseEdit()
        self.m_userNameEdit = QLineEdit()
        self.m_passwordEdit = QLineEdit()
        self.m_passwordEdit.setEchoMode(QLineEdit.Password)
        self.m_rememberCheckbox = QCheckBox("Remember me")

        inputLayout = QGridLayout()
        inputLayout.addWidget(QLabel("Database"), 0, 0)
        inputLayout.addWidget(QLabel("User name"), 1, 0)
        inputLayout.addWidget(QLabel("Password"), 2, 0)
        inputLayout.addWidget(self.m_databaseEdit, 0, 1)
        inputLayout.addWidget(self.m_userNameEdit, 1, 1)
        inputLayout.addWidget(self.m_passwordEdit, 2, 1)
        inputLayout.addWidget(self.m_rememberCheckbox, 3, 1)
        self.m_rememberCheckbox.setVisible(False)

        config = Configuration()
        self.m_databaseEdit.addToHistory(config.recentDBs())

        self.m_loginButton = QPushButton("Login")
        self.m_cancelButton = QPushButton("Cancel")
        self.m_loginButton.setDefault(True)
        btnLayout = QHBoxLayout()
        btnLayout.addItem(QSpacerItem(5, 1, QSizePolicy.Expanding, QSizePolicy.Minimum))
        btnLayout.addWidget(self.m_cancelButton)
        btnLayout.addWidget(self.m_loginButton)

        mainLayout = QVBoxLayout()
        mainLayout.addLayout(inputLayout)
        mainLayout.addItem(QSpacerItem(5, 1, QSizePolicy.Minimum, QSizePolicy.Expanding))
        mainLayout.addLayout(btnLayout)

        self.setLayout(mainLayout)

        self.m_databaseEdit.textEdited.connect(self.updateLoginBtnState)
        self.m_userNameEdit.textEdited.connect(self.updateLoginBtnState)
        self.m_passwordEdit.textEdited.connect(self.updateLoginBtnState)
        self.updateLoginBtnState()

        self.m_loginButton.pressed.connect(self.accept)
        self.m_cancelButton.pressed.connect(self.reject)

        self.resize(300, 150)

    def updateLoginBtnState(self):
        self.m_loginButton.setEnabled(len(self.m_userNameEdit.text()) != 0 and
                                      len(self.m_passwordEdit.text()) != 0 and
                                      len(self.m_databaseEdit.text()) != 0)

    def result(self):
        return (self.m_databaseEdit.text(), self.m_userNameEdit.text(), self.m_passwordEdit.text())