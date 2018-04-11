
from PyQt5.QtCore import QObject
from PyQt5.QtCore import QDate

class ControlBinder(QObject):
    def __init__(self):
        super(ControlBinder, self).__init__()

    def document(self):
        pass

    def bindEdit(self, controlName, attrName):
        val = self.document().modifiedValue(attrName)
        getattr(self.ui, controlName).setText(str(val))
        getattr(self.ui, controlName).textChanged.connect(lambda val : self.document().setModified(attrName, val))
        self.document().changedSignal.connect(
            lambda attr, meta=self.document(), thisAttr=attrName: getattr(self.ui, controlName).setText(
                str(meta.modifiedValue(attrName))) if (attr == thisAttr)  and getattr(self.ui, controlName).text() != str(meta.modifiedValue(attrName)) else None)

    def bindTextEdit(self, controlName, attrName):
        getattr(self.ui, controlName).setPlainText(self.document().modifiedValue(attrName))
        getattr(self.ui, controlName).textChanged.connect(lambda control=getattr(self.ui, controlName): self.document().setModified(attrName, control.toPlainText()))
        self.document().changedSignal.connect(
            lambda attr, meta=self.document(), thisAttr=attrName: getattr(self.ui, controlName).setPlainText(
                meta.modifiedValue(attrName)) if (attr == thisAttr) and getattr(self.ui, controlName).toPlainText() != meta.modifiedValue(attrName) else None)

    def bindCombo(self, controlName, attrName):
        if self.document().modifiedValue(attrName) == "":
            self.document().setAttr(attrName, getattr(self.ui, controlName).itemText(0))
        getattr(self.ui, controlName).setCurrentText(self.document().modifiedValue(attrName))
        getattr(self.ui, controlName).currentIndexChanged.connect(lambda idx, control=getattr(self.ui, controlName): self.document().setModified(attrName, control.currentText()))
        self.document().changedSignal.connect(
            lambda attr, meta=self.document(), thisAttr=attrName: getattr(self.ui, controlName).setCurrentText(
                meta.modifiedValue(attrName)) if (attr == thisAttr) and getattr(self.ui, controlName).currentText() != meta.modifiedValue(attrName) else None)

    def bindMCombo(self, controlName, attrName):
        if self.document().modifiedValue(attrName) == 0:
            self.document().setAttr(attrName, getattr(self.ui, controlName).firstId())
        getattr(self.ui, controlName).setCurrentText(self.document().modifiedValue(attrName))
        getattr(self.ui, controlName).currentIndexChanged.connect(lambda idx, control=getattr(self.ui, controlName): self.document().setModified(attrName, control.currentText()))
        self.document().changedSignal.connect(
            lambda attr, meta=self.document(), thisAttr=attrName: getattr(self.ui, controlName).setCurrentText(
                meta.modifiedValue(attrName)) if (attr == thisAttr) and getattr(self.ui, controlName).currentText() != meta.modifiedValue(attrName) else None)

    def bindDateEdit(self, controlName, attrName):
        if self.document().modifiedValue(attrName) == "":
            self.document().setAttr(attrName, QDate.currentDate().toString("yyyy-MM-dd"))
        getattr(self.ui, controlName).setDate(QDate.fromString(self.document().modifiedValue(attrName), "yyyy-MM-dd"))
        getattr(self.ui, controlName).dateChanged.connect(lambda val: self.document().setModified(attrName, val.toString("yyyy-MM-dd")))
        self.document().changedSignal.connect(
            lambda attr, meta=self.document(), thisAttr=attrName: getattr(self.ui, controlName).setDate(QDate.fromString(
                meta.modifiedValue(attrName), "yyyy-MM-dd")) if (attr == thisAttr)  and getattr(self.ui, controlName).date().toString("yyyy-MM-dd") != meta.modifiedValue(attrName) else None)

    def setRadioButtons(self, attrName, controlsAndVals, thisAttrName):
        if attrName == thisAttrName:
            for control, val in controlsAndVals:
                if val == self.document().modifiedValue(thisAttrName):
                    getattr(self.ui, control).setChecked(True)
                    break

    def bindRadioButtonGroup(self, controlsAndVals, attrName):
        if self.document().modifiedValue(attrName) == "":
            self.document().setAttr(attrName, controlsAndVals[0][1])

        for control, val in controlsAndVals:
            if val == self.document().modifiedValue(attrName):
                getattr(self.ui, control).setChecked(True)
                break

        for control, val in controlsAndVals:
            getattr(self.ui, control).toggled.connect(lambda checked, value=val : self.document().setModified(attrName, value) if checked else None)
        self.document().changedSignal.connect(
            lambda attr, self_=self, controlsAndVals=controlsAndVals, thisAttr=attrName: self_.setRadioButtons(attr, controlsAndVals, thisAttr))

    def bindRefDateEdit(self, controlName, attrName):
        val = self.document().modifiedValue(attrName)
        getattr(self.ui, controlName).setText(str(val))
        getattr(self.ui, controlName).textChanged.connect(lambda val : self.document().setModified(attrName, val))
        self.document().changedSignal.connect(
            lambda attr, meta=self.document(), thisAttr=attrName: getattr(self.ui, controlName).setText(
                str(meta.modifiedValue(attrName))) if (attr == thisAttr)  and getattr(self.ui, controlName).text() != str(meta.modifiedValue(attrName)) else None)
