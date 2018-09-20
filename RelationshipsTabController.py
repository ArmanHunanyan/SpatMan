
from PyQt5.QtCore import QObject
from RelationshipsLookupTablesController import RelationshipsLookupTablesController
from RelationshipsAttributeJoinsController import RelationshipAttributeJoinsController
from RelationshipsNetworksController import RelationshipNetworksController

class RelationshipsTabController(QObject):
    def __init__(self, ui, database, schema, connId, host, port, dbName, user, password):
        super(RelationshipsTabController, self).__init__()
        self.m_lookuoTablesController = RelationshipsLookupTablesController(ui, database, schema, connId, host, port, dbName,
                                                                user, password)
        self.m_attributeJoinsController = RelationshipAttributeJoinsController(ui, database, schema, connId, host, port, dbName,
                                                                user, password)
        self.m_networksController = RelationshipNetworksController(ui, database, schema, connId, host, port, dbName,
                                                                user, password)