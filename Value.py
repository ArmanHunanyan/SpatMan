class Value:
    def __init__(self, origValue):
        self.originalValue = origValue
        self.modifiedValue = origValue

    def reset(self):
        self.modifiedValue = self.originalValue

    def commitChanges(self):
        self.originalValue = self.modifiedValue