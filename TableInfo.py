from Value import Value

class TableInfo:
    def __init__(self, id, local, *args):
        self.m_data = list(Value(arg) for arg in args)
        self.m_added = False
        self.m_deleted = False
        self.m_frozen = False
        self.m_id = id
        self.m_local = local

    def id(self):
        return self.m_id

    def local(self):
        return self.m_local

    def freez(self, f):
        self.m_frozen = f

    def setLocal(self, l):
        self.m_local = True

    def resize(self, size):
        self.m_data = list([Value("") for x in range(size)])

    def setAdded(self):
        self.m_added = True

    def setDeleted(self):
        self.m_deleted = True

    def added(self):
        return self.m_added

    def deleted(self):
        return self.m_deleted

    def frozen(self):
        return self.m_frozen

    def modifiedTuple(self):
        return tuple(val.modifiedValue for val in self.m_data)

    def displayValue(self, idx):
        if idx >= len(self.m_data):
            return ""
        return self.m_data[idx].modifiedValue

    def setValue(self, idx, value):
        if idx >= len(self.m_data):
            self.m_data += [Value("")] * (idx + 1 - len(self.m_data))
        if value != self.m_data[idx].modifiedValue:
            self.m_data[idx].modifiedValue = value
            return True
        return False

    def value(self, idx):
        if idx >= len(self.m_data):
            return Value("")
        return self.m_data[idx]

    def reset(self):
        for val in self.m_data:
            val.reset()
        self.m_added = False
        self.m_deleted = False

    def commitChanges(self):
        for val in self.m_data:
            val.commitChanges()
        self.m_added = False
        self.m_deleted = False

    def isModified(self, idx):
         return self.m_added or self.m_deleted or (self.m_data[idx].modifiedValue != self.m_data[idx].originalValue)