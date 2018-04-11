import hashlib, binascii
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QObject
from PyQt5.QtSql import QSqlDatabase
from PyQt5.QtSql import QSqlQuery
from TableInfo import Value
from TableMetadata import TableMetadata
from TableMetadata import TableDataPolicy

from TableInfo import TableInfo

def quoteString(s):
    return str(s).replace("'", "''")

class DbNotFound(Exception):
    pass

class WrongUserPass(Exception):
    pass

class SQLLog:
    def __init__(self):
        self.m_fileName = "sql.log"
        self.m_file = open(self.m_fileName, "w")

    def write(self, sql, name):
        numChars = 80
        self.m_file.write("\n%s %s\n" % (name, ">" * (numChars - len(name) - 1)))
        self.m_file.write(sql)
        self.m_file.write("\n%s\n" % (">" * numChars))
        self.m_file.flush()

sqlLog = SQLLog()

class DBCursorWrapper:
    def __init__(self, query, name):
        self.m_query = query
        self.m_dbLogName = name

    def execute(self, sql):
        sqlLog.write(sql, self.m_dbLogName)
        self.m_query.exec(sql)
        if self.m_query.lastError().isValid():
            raise Exception(self.m_query.lastError().text())

    def executeArgs(self, sql, *args):
        newArgs = (quoteString(arg) for arg in args)
        sql = sql % newArgs
        sqlLog.write(sql, self.m_dbLogName)
        self.m_query.exec(sql)
        if self.m_query.lastError().isValid():
            raise Exception(self.m_query.lastError().text())

    def fetchone(self):
        if not self.m_query.next():
            return None
        rec = self.m_query.record()
        return tuple(self.m_query.value(idx) for idx in range(rec.count()))

    def fetchall(self):
        res = []
        rec = self.m_query.record()
        while self.m_query.next():
            res.append(tuple(None if self.m_query.isNull(idx) else self.m_query.value(idx)  for idx in range(rec.count())))

        return res

    def numRowsAffected(self):
        return self.m_query.numRowsAffected()

    def lastInsertId(self):
        return self.m_query.lastInsertId()

def qtDBType(dbType):
    if dbType == "Oracle":
        return "QOCI"
    elif dbType == "PostgreSQL":
        return "QPSQL"
    elif dbType == "MySQL":
        return "QMYSQL"
    elif dbType == "MS SQL":
        return "QODBC"
    else:
        assert(False)

class DBConnWrapper:

    conn_num = 0

    def __init__(self, dbName, dbType, server=None, port=None, username=None, password=None):
        self.m_database = QSqlDatabase.addDatabase(dbType, "conn" + str(DBConnWrapper.conn_num))
        DBConnWrapper.conn_num += 1
        if server is None:
            self.m_logName = dbType + ":localhost"
        else:
            self.m_logName = dbType + ":%s:%s" % (server, str(port))

        if server is not None:
            self.m_database.setHostName(server)

        if port is not None:
            self.m_database.setPort(port)

        self.m_database.setDatabaseName(dbName)

        if username is not None:
            self.m_database.setUserName(username)

        if password is not None:
            self.m_database.setPassword(password)

        if self.m_database is None:
            raise DbNotFound(self.m_database.lastError().text())
        self.m_database.setDatabaseName(dbName)

        if not self.m_database.open():
            raise DbNotFound(self.m_database.lastError().text())

    def cursor(self):
        return DBCursorWrapper(QSqlQuery(self.m_database), self.m_logName)

    def commit(self):
        self.m_database.commit()

    def qtDatabase(self):
        return self.m_database

def testConnection(active, dbType, server, database, schema, username, password):
    driver = qtDBType(dbType)
    db = QSqlDatabase.addDatabase(driver, "test_conn")
    db.setHostName(server)
    db.setDatabaseName(database)
    db.setUserName(username)
    db.setPassword(password)
    ok = db.open()
    print("Open status: %s" % str(ok))
    if not ok:
        return False

    query = QSqlQuery(db)
    sql = "select exists (select * from pg_catalog.pg_namespace where nspname = '%s')" % quoteString(schema);
    ok = query.exec(sql)
    print("Exec status: %s" % str(ok))
    if not ok:
        return False
    return True


class DBVariablesDescriptor():

    # Last column name considered the value column that need to be accessed
    def __init__(self, tableName, columnNames, variables, varnameColumn, readOnly = [], filterKey = None, filterColumn = None):
        super
        assert len(columnNames) == (len(variables[0]) + 1 + (1 if filterKey is not None else 0))
        assert varnameColumn < len(variables)
        self.m_tableName = tableName
        self.m_columnNames = columnNames
        self.m_variables = variables
        self.m_varNameColumn = varnameColumn
        self.m_readOnly = readOnly
        self.m_filterKey = filterKey
        self.m_filterColumn = filterColumn

    def generate_get_SQL(self):
        res = "SELECT\n    %s\nFROM\n    %s" % (self.m_columnNames[-1-(1 if self.m_filterKey is not None else 0)], self.m_tableName)
        res += "\nWHERE\n"
        res += "    %s IN (%s)" % (self.m_columnNames[self.m_varNameColumn], ", ".join(["'" + x[self.m_varNameColumn] + "'" for x in self.m_variables]))
        if self.m_filterKey is not None:
            res += "\n AND " + self.m_columnNames[self.m_filterColumn]  + " = '" + str(self.m_filterKey) + "'"
        res += "\nORDER BY\n    CASE %s\n        " % self.m_columnNames[self.m_varNameColumn]
        res += "\n        ".join([("WHEN '" + self.m_variables[idx][self.m_varNameColumn] + "' THEN " + str(idx) + "") for idx in range(len(self.m_variables))])
        res += "\n    END"

        return res

    def __get__(self, database, objtype):
        return self.getImpl(database, objtype, "OneMoreTry")

    def getImpl(self, database, objtype, hint):
        cur = database.m_connection.cursor()
        sql = self.generate_get_SQL()
        cur.execute(sql)
        res = cur.fetchall()
        res = tuple(i[0] for i in res)
        if len(res) == 0:
            res = ("",) * len(self.m_variables)
        if len(res) != len(self.m_variables):
            # First time access. Incomlete databse
            if hint == "OneMoreTry" and len(self.m_readOnly) == 0:
                self.__set__(database, ("",) * len(self.m_variables))
                res = self.getImpl(database, objtype, "NoAnyTries")
            else:
                msg = "Incomplete database:\nTable '%s', does not contain one of the following properties\n" % self.m_tableName
                for rd in self.m_readOnly:
                    msg += "\t" + self.m_variables[rd][1] + "\n"
                raise Exception(msg)

        return res

    def generate_set_SQL(self, values):
        assert len(values) == len(self.m_variables)
        res = "INSERT OR REPLACE INTO %s\n" % self.m_tableName
        res += "     (" + ", ".join(self.m_columnNames) + ")\n"
        res += "VALUES\n    "
        if self.m_filterKey is None:
            res += ",\n    ".join(["(" + ", ".join(["'" + quoteString(x) + "'" for x in self.m_variables[idx] + (values[idx],)]) + ")" for idx in range(len(self.m_variables)) if not idx in self.m_readOnly])
        else:
            res += ",\n    ".join(
                ["(" + ", ".join(["'" + quoteString(x) + "'" for x in self.m_variables[idx] + (str(values[idx]),) + (str(self.m_filterKey),)]) + ")" for idx in range(len(self.m_variables)) if not idx in self.m_readOnly])
        return res

    def __set__(self, database, val):
        cur = database.m_connection.cursor()
        sql = self.generate_set_SQL(val)
        cur.execute(sql)
        database.m_connection.commit()

def encryptPassword(passwd, salt):
    dk = hashlib.pbkdf2_hmac('sha256', passwd.encode(), salt.encode(), 100000)
    return binascii.hexlify(dk).decode('ascii')

class SchemaProperties:
    def __init__(self, connection, connId):
        self.m_connection = connection
        SchemaProperties.properties = DBVariablesDescriptor("sm_conn_sett",
                                                 ['sm_type', 'sm_variable', 'description', 'sm_value', 'conn_id'],
                                                 [('T', 'SCHEMADESCR', 'Schema description'),
                                                  ('T', 'SCHEMALANG', 'Language'),
                                                  ('T', 'SCHEMACHARSET', 'Character set'),
                                                  ('T', 'EPSG_SRID', 'Default EPSG SRID for this schema'),
                                                  ('D', 'DBUNITS', 'Unit of measure applied in this schema.'),
                                                  ('R', 'DB_PRECS', 'Default precision applied across this schema'),
                                                  ('D', 'WESTEXTENTS', 'The Western Extents in default SRID coordinates.'),
                                                  ('D', 'NORTHEXTENTS', 'The Northern Extents in default SRID coordinates.'),
                                                  ('D', 'EASTEXTENTS', 'The Eastern Extents in default SRID coordinates.'),
                                                  ('D', 'SOUTHEXTENTS', 'The Southern Extents in default SRID coordinates.'),
                                                  ('D', 'DATA_ACCESS', 'Data access'),
                                                  ('D', 'COPYRIGHT', 'Copyright'),
                                                  ('D', 'USERRIGHTS', 'User rights'),
                                                  ('T', 'CUSTODIAN', 'The organisation that owns or manages the copyright of a dataset.'),
                                                  ('T', 'MAINCONTACTID','The ID of the Main Contact Person.'),
                                                  ], 1, [], connId, 4)

class DatabaseBase(QObject):
    def __init__(self):
        super(DatabaseBase, self).__init__()

    def executeListQuery(self, query):
        cur = self.m_connection.cursor()
        cur.execute(query)
        res = cur.fetchall()
        if len(res) == 0:
            return res

        if len(res[0]) == 1:
            return [i[0] for i in res]
        else:
            return res

class ClientDatabase(DatabaseBase):
    def __init__(self, localDatabase, db, dbType, server, port, username, password):
        super(ClientDatabase, self).__init__()
        self.m_connection = DBConnWrapper(db, qtDBType(dbType), server, port, username, password)
        self.m_dbType = qtDBType(dbType)
        self.m_localDatabase = localDatabase
        self.m_localDatabase.schemaGroupListChangedSignal.connect(self.schemaGroupListChangedSignal)
        self.m_localDatabase.globalNamingConvChanged.connect(self.uidChangedSignal)


    @property
    def globalNamingConv(self):
        return self.m_localDatabase.globalNamingConv

    def localDatabase(self):
        return self.m_localDatabase

    def uidColumn(self):
        idColId = 0
        idColName = self.m_localDatabase.globalNamingConv[5]
        if idColName is None or idColName == "":
            return None
        idColDesc = "Primary Key"
        idColtype = "integer"
        idColSyze = 32
        idColScale = 0
        idcolUnits = ""
        idColDefaultValue = ""
        idColLUTable = ""
        idColMaxVal = ""
        idColMinVal = ""
        idColIsPrimKey = "Yes"
        geomColAllowNulls = "No"
        return (idColId, idColName, idColDesc, idColtype, idColSyze, idColScale, idcolUnits, idColDefaultValue, idColLUTable, idColMaxVal, idColMinVal, idColIsPrimKey, geomColAllowNulls)

    def geomColumn(self, type, connId):
        srid = self.m_localDatabase.schemaProperties(connId).properties[3]
        try:
            int(srid)
        except Exception as e:
            return None
        geomColId = -1
        if type.lower() in ["raster", "surface"]:
            geomColName = self.m_localDatabase.globalNamingConv[7]
        else:
            geomColName = self.m_localDatabase.globalNamingConv[6]
        if geomColName is None or geomColName == "":
            return None
        geomColDesc = "Geometry column"
        geomColtype = type
        geomColSyze = ""
        geomColScale = ""
        geomcolUnits = ""
        geomColDefaultValue = ""
        geomColLUTable = ""
        geomColMaxVal = ""
        geomColMinVal = ""
        geomColIsPrimKey = "No"
        geomColAllowNulls = "Yes"
        return (geomColId, geomColName, geomColDesc, geomColtype, geomColSyze, geomColScale, geomcolUnits,
                geomColDefaultValue, geomColLUTable, geomColMaxVal, geomColMinVal, geomColIsPrimKey, geomColAllowNulls)

    uidChangedSignal = pyqtSignal()

    def schemaTableList(self, schema):
        sql = "SELECT                         \n" \
              "    table_name                 \n" \
              "FROM                           \n" \
              "    information_schema.tables  \n" \
              "WHERE                          \n" \
              "     table_schema='%s'           " % quoteString(schema)

        cur = self.m_connection.cursor()
        cur.execute(sql)
        res = cur.fetchall()
        return [i[0] for i in res]

    def deleteTableAndInfo(self, schema, connId, tableName):
        self.m_localDatabase.deleteTableInfo(tableName, connId)
        sql = "DROP TABLE %s.%s;" % (schema, tableName)
        cur = self.m_connection.cursor()
        cur.execute(sql)
        self.tableListChanged.emit()

    def tableInfo(self, schema, connId, tableName, defGroup = "FromDB", defTitle=None, defDescription=None, defIsSpatial = None, defSpatialType = None):
        group, title, description, isSpatial, spatialType, local = self.m_localDatabase.tableInfo(tableName, connId)
        if isSpatial == "Y":
            isSpatial = True
        elif isSpatial == "N":
            isSpatial = False

        if group is None:
            group = defGroup
            if group is None:
                group = "FromDB"
        if title is None:
            title = defTitle
            if title is None:
                title = tableName
        if description is None:
            description = defDescription
            if description is None:
                description = tableName
        if isSpatial is None:
            isSpatial = defIsSpatial
            spatialType = defSpatialType
            if isSpatial is None:
                isSpatial, spatialType, colName_ = self.spatialInfo(schema, tableName)
        return (local, tableName, group, title, description, isSpatial, spatialType, schema)

    def spatialInfo(self, schema, tableName):
        sql = "SELECT column_name                       \n" \
              "FROM information_schema.columns          \n" \
              "WHERE                                    \n" \
              "    table_name = '%s' AND                \n" \
              "    table_schema = '%s' AND              \n" \
              "    udt_name IN('geometry', 'geography')   " % (quoteString(tableName.lower()), quoteString(schema))

        cur = self.m_connection.cursor()
        cur.execute(sql)
        res = cur.fetchall()

        if len(res) == 0:
            return (False, None, None)

        columnName = res[0][0]

        sql = "SELECT type                    \n" \
              "FROM geometry_columns          \n" \
              "WHERE                          \n" \
              "    f_table_schema = '%s' AND  \n" \
              "    f_table_name = '%s' AND    \n" \
              "    f_geometry_column = '%s'     " % (quoteString(schema), quoteString(tableName.lower()), quoteString(columnName))

        cur.execute(sql)
        res = cur.fetchall()

        return (True, res[0][0], columnName)

    tableNameChanged = pyqtSignal(str, str)
    tableListChanged = pyqtSignal()

    def saveTable(self, tableName, group, title, description, isSpatial, spatialType, schema, connId):
        if tableName.originalValue != tableName.modifiedValue:
            sql="ALTER TABLE %s.%s RENAME TO %s" % (schema.originalValue, tableName.originalValue, tableName.modifiedValue)
            cur = self.m_connection.cursor()
            cur.execute(sql)

        self.m_localDatabase.saveTableInfo(tableName, connId, group.modifiedValue, title.modifiedValue, description.modifiedValue, isSpatial.modifiedValue, spatialType.modifiedValue)

        if tableName.originalValue != tableName.modifiedValue:
            self.tableNameChanged.emit(tableName.originalValue, tableName.modifiedValue)

    def schemaGroupList(self, connId):
        return self.m_localDatabase.schemaGroupList(connId)

    schemaGroupListChangedSignal = pyqtSignal()

    def doTypeCorrection(self, client, schema, tableName):
        new_client = []
        for col in client:
            type = col[2]
            if type == "USER-DEFINED":
                sql = "SELECT type                   \n" \
                      "FROM geometry_columns         \n" \
                      "WHERE                         \n" \
                      "    f_table_schema = '%s' AND \n" \
                      "    f_table_name = '%s' AND   \n" \
                      "    f_geometry_column = '%s'    " % (
                      quoteString(schema), quoteString(tableName.lower()), quoteString(col[0]))
                cur = self.m_connection.cursor()
                cur.execute(sql)
                res = cur.fetchall()
                if res is None or len(res) == 0:
                    continue
                col = list(col)
                col[2] = res[0][0]
            new_client.append(col)
        client = new_client

        res = []
        for col in client:
            type = col[2]
            changeInDb = True
            if type.lower() in ["date", "varchar", "real", "double precision", "smallint", "integer", "bigint", "decimal", "numeric", "text", "point", "line", "polygon", "raster", "surface"]:
                # Types are OK. Just return them
                newType = type.lower()
            elif type in ["character varying"]:
                newType = "varchar"
                changeInDb = False
            else:
                # Not interesting type. Skipping
                continue

            newCol = list(col)
            newCol[2] = newType
            if newCol[2] in ["real", "double precision", "smallint", "integer", "bigint", "numeric", "decimal"]:
                newCol[3] = col[5] # assigning precision to size field
            res.append(newCol)

        return res

    def fillMissingColumnInfo(self, info, primKey):
        return (info[0], "", info[2], info[3], info[4], "", info[1], "", "", "", "Yes" if info[0] == primKey else "No", "Yes" if info[6].lower() == "yes" else "No")

    def primaryKey(self, schema, tableName):
        sql = "SELECT column_name                                                   \n" \
              "FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS AS TC                      \n" \
              "INNER JOIN                                                           \n" \
              "     INFORMATION_SCHEMA.KEY_COLUMN_USAGE AS KU                       \n" \
              "         ON TC.CONSTRAINT_TYPE = 'PRIMARY KEY'                       \n" \
              "         AND TC.CONSTRAINT_NAME = KU.CONSTRAINT_NAME                 \n" \
              "         AND KU.table_name = '%s'                                    \n" \
              "         AND KU.table_schema = '%s'                                  \n" % (quoteString(tableName.lower()), quoteString(schema))

        cur = self.m_connection.cursor()
        cur.execute(sql)
        res = cur.fetchone()
        if res is None:
            return None
        return res[0]

    def columnsInfo(self, schema, tableName, connId):
        sql = "SELECT                         \n" \
              "    column_name,               \n" \
              "    column_default,            \n" \
              "    data_type,                 \n" \
              "    character_maximum_length,  \n" \
              "    numeric_scale,             \n" \
              "    numeric_precision,         \n" \
              "    is_nullable                \n" \
              "FROM                           \n" \
              "    information_schema.columns \n" \
              "WHERE                          \n" \
              "    table_name = '%s' AND      \n" \
              "    table_schema = '%s'          " % (quoteString(tableName.lower()), quoteString(schema))
        cur = self.m_connection.cursor()
        cur.execute(sql)
        client = cur.fetchall()
        client = self.doTypeCorrection(client, schema, tableName)
        local = self.m_localDatabase.columnInfos(client, tableName, connId)

        res = []
        client_idx = 0
        local_idx = 0
        primKey = None
        primKeyInitialized = False
        db_order = dict()
        for idx in range(len(client)):
            db_order[client[idx][0]] = idx
        client.sort(key=lambda x : x[0]) # sort by name
        while client_idx < len(client) and local_idx < len(local):
            if client[client_idx][0] < local[local_idx][0]:
                if not primKeyInitialized:
                    primKey = self.primaryKey(schema, tableName)
                    primKeyInitialized = True
                res.append(self.fillMissingColumnInfo(client[client_idx], primKey))
                client_idx += 1
            elif client[client_idx][0] == local[local_idx][0]:
                res.append((client[client_idx][0], local[local_idx][1], client[client_idx][2], client[client_idx][3],
                            client[client_idx][4], local[local_idx][5], client[client_idx][1], local[local_idx][7],
                            local[local_idx][8], local[local_idx][9], "Yes" if local[local_idx][10] == "Y" else "No", "Yes" if local[local_idx][11] == "Y" else "No"))
                local_idx += 1
                client_idx += 1
            else:
                local_idx += 1

        while client_idx < len(client):
            if not primKeyInitialized:
                primKey = self.primaryKey(schema, tableName)
                primKeyInitialized = True
            res.append(self.fillMissingColumnInfo(client[client_idx], primKey))
            client_idx += 1

        resOrd = [None] * len(res)

        for r in res:
            resOrd[db_order[r[0]]] = r

        return resOrd

    def sqlColType(self, type, size, scale, primaryKey, allowNull, connId):
        if primaryKey:
            return self.__sqlColType(type, size, scale, connId) + " primary key"
        else:
            return self.__sqlColType(type, size, scale, connId) + (" not null " if not allowNull else "")

    def __sqlGeomCol(self, type, connId):
        pattern = ""
        needSub = True
        if type == "text":
            pattern = "geometry(point,%s)"
        elif type == "point":
            pattern = "geometry(point,%s)"
        elif type == "line":
            pattern = "geometry(linestring,%s)"
        elif type == "polygon":
            pattern = "geometry(polygon,%s)"
        elif type == "raster":
            pattern = "raster"
            needSub = False
        elif type == "surface":
            pattern = "lo"
            needSub = False

        if needSub:
            srid = self.m_localDatabase.schemaProperties(connId).properties[3]
            pattern = pattern % srid

        return pattern

    def __sqlColType(self, type, size, scale, connId):
        if type.lower() in ["text", "point", "line", "polygon", "raster", "surface"]:
            return self.__sqlGeomCol(type.lower(), connId)
        if type not in ["varchar", "numeric", "decimal"]:
            return str(type)
        sz = None
        try:
            sz = int(size)
        except:
            pass
        sc = None
        try:
            sc = int(scale)
        except:
            pass
        if sz is None and sc is None:
            size = ""
        elif sc is None:
            size = "(%s)" % str(sz)
        else:
            size = "(%s, %s)" % (str(sz), str(sc))

        return type+size

    def ensureTableIsCached(self, tableName, connId, schema):
        res = self.m_localDatabase.tableId(tableName, connId)
        if len(res) != 0:
            return res[0][0]
        else:
            local, tableName, group, title, description, isSpatial, spatialType, schema = self.tableInfo(schema, connId, tableName)
            self.m_localDatabase.saveTableInfo(Value(tableName), connId, group, title, description,
                                               "Y" if isSpatial else "N", spatialType)
            res = self.m_localDatabase.tableId(tableName, connId)
            return res[0][0]

    def ensureTableAndColumnsAreCached(self, tableName, connId, schema):
        tableId = self.ensureTableIsCached(tableName, connId, schema)
        columnInfo = self.columnsInfo(schema, tableName, connId)
        columnInfo = list(TableInfo(0, False, *info) for info in columnInfo)
        for row in columnInfo:
            self.m_localDatabase.saveColumnInfo(row, tableId, schema, connId)

    def saveColumn(self, row, tableName, schema, connId):
        sql = ""
        if row.deleted():
            sql += "ALTER TABLE %s.%s DROP COLUMN %s;" % (schema, tableName, row.value(0).modifiedValue)
        else:
            newType = row.value(2).modifiedValue
            newlyAdded = False
            if row.added():
                sql += "ALTER TABLE %s.%s ADD COLUMN %s %s;" % (schema, tableName, row.value(0).modifiedValue,
                                            self.sqlColType(newType, row.value(3).modifiedValue, row.value(4).modifiedValue, row.value(10).modifiedValue == "Yes", row.value(11).modifiedValue == "Yes", connId))
                newlyAdded = True

            if not newlyAdded and (row.value(0).originalValue != row.value(0).modifiedValue):
                sql += "ALTER TABLE %s.%s RENAME COLUMN %s TO %s;" % (schema, tableName, row.value(0).originalValue, row.value(0).modifiedValue)

            if not newlyAdded and (row.value(10).originalValue != row.value(10).modifiedValue):
                if row.value(10).modifiedValue == "No":
                    sql1 = "SELECT constraint_name                    \n" \
                           "FROM information_schema.table_constraints \n" \
                           "WHERE                                     \n" \
                           "    table_schema = '%s' AND               \n" \
                           "    table_name = '%s' AND                 \n" \
                           "    constraint_type = 'PRIMARY KEY'         " % (quoteString(schema), quoteString(tableName))
                    cur = self.m_connection.cursor()
                    cur.execute(sql1)
                    constr_name = cur.fetchone()[0]
                    sql += "ALTER TABLE %s.%s DROP CONSTRAINT \"%s\";" % (schema, tableName, constr_name)
                else:
                    sql += "ALTER TABLE %s.%s ADD PRIMARY KEY (%s);" % (schema, tableName, row.value(0).modifiedValue)

            if not newlyAdded and (row.value(11).originalValue != row.value(11).modifiedValue):
                if row.value(11).modifiedValue == "No":
                    sql += "ALTER TABLE %s.%s ALTER COLUMN %s SET NOT NULL;" % (schema, tableName, row.value(0).modifiedValue)
                else:
                    sql += "ALTER TABLE %s.%s ALTER COLUMN %s DROP NOT NULL;" % (schema, tableName, row.value(0).modifiedValue)

            if not newlyAdded and (row.value(2).originalValue != row.value(2).modifiedValue or
                                                        row.value(3).originalValue != row.value(3).modifiedValue or
                                                        row.value(4).originalValue != row.value(4).modifiedValue):
                sql += "ALTER TABLE %s.%s ALTER COLUMN %s TYPE %s;" % (
                    schema, tableName, row.value(0).modifiedValue, self.sqlColType(newType, row.value(3).modifiedValue, row.value(4).modifiedValue, False, True, connId))

            if row.value(6).originalValue != row.value(6).modifiedValue:
                if row.value(6).modifiedValue is None or (row.value(6).modifiedValue == ''):
                    sql += "ALTER TABLE %s.%s ALTER COLUMN %s DROP DEFAULT" % (
                    schema, tableName, row.value(0).modifiedValue)
                else:
                    sql += "ALTER TABLE %s.%s ALTER COLUMN %s SET DEFAULT %s;" % (schema, tableName, row.value(0).modifiedValue,
                                        ("%s" if newType in ["double precision", "smallint", "integer", "bigint"] else "'%s'") % quoteString(row.value(6).modifiedValue))

        cur = self.m_connection.cursor()
        cur.execute(sql)
        tableId = self.ensureTableIsCached(tableName, connId, schema)
        self.m_localDatabase.saveColumnInfo(row, tableId, schema, connId)

    def commonColumnsInfo(self, connId):
        res = self.m_localDatabase.commonColumnsInfo(connId)
        return res

    commonColumnsChangedSignal = pyqtSignal()

    def saveCommonColumnInfo(self, row, connId):
        self.m_localDatabase.saveCommonColumnInfo(row, connId)
        self.commonColumnsChangedSignal.emit()

    def createTableSQL(self, schema, name, group, title, description, isSpatial, spatialType, columns, connId):
        sql = "CREATE TABLE %s.%s (" % (schema, name)
        firstLine = True
        for col in columns:
            colName, _colDesc, colType, colSize, colScale, _colUnits, defaultValue, _luTable, _columnMaxval, _columnMinval, isPrimaryKey, allowNulls = col.modifiedTuple()
            isPrimaryKey = isPrimaryKey == "Yes"
            allowNulls = allowNulls == "Yes"
            if firstLine:
                sql += "\n"
                firstLine = False
            else:
                sql += ",\n"
            if colType in ["character varying", "varchar"]:
                if defaultValue is not None and defaultValue != "":
                    defaultValue = "'%s'" % quoteString(defaultValue)
            colType = self.sqlColType(colType, colSize, colScale, isPrimaryKey, allowNulls, connId)
            sql += "%s %s" % (colName, colType)
            if defaultValue is not None and defaultValue != "":
                sql += " DEFAULT %s" % defaultValue
        sql += ")"
        return sql

    def createTable(self, connId, schema, name, group, title, description, isSpatial, spatialType, columns):
        sql = self.createTableSQL(schema, name, group, title, description, isSpatial, spatialType, columns, connId)
        cur = self.m_connection.cursor()
        cur.execute(sql)

        local, tableName, group, title, description, isSpatial, spatialType, schema = \
                    self.tableInfo(schema, connId, name, group, title, description, isSpatial, spatialType)
        self.m_localDatabase.saveTableInfo(Value(tableName), connId, group, title, description, "Y" if isSpatial else "N", spatialType)
        tableId = self.ensureTableIsCached(name, connId, schema)
        for column in columns:
            self.m_localDatabase.saveColumnInfo(column, tableId, schema, connId)

        self.tableListChanged.emit()

    def geometryColumn(self, schema, tableName):
        isSpatial, spatialType, colName = self.spatialInfo(schema, tableName)
        if not isSpatial:
            return ""
        return colName

    def dataPolicy(self, connId, tableName, schema):
        res = self.m_localDatabase.dataPolicy(connId, tableName)
        return res

    def saveDataPolicy(self, connId, metadata):
        self.m_localDatabase.saveDataPolicy(connId, metadata)

    def deleteDataPolicy(self, connId, metadata):
        self.m_localDatabase.deleteDataPolicy(connId, metadata)

    def metadata(self, connId, tableName, schema):
        res = self.m_localDatabase.metadata(connId, tableName)
        res.geometryColumn = self.geometryColumn(schema, tableName)
        return res

    def saveMetadata(self, connId, metadata):
        self.m_localDatabase.saveMetadata(connId, metadata)

    def deleteMetadata(self, connId, metadata):
        self.m_localDatabase.deleteMetadata(connId, metadata)

    def spatialExtents(self, metadata, schema):
        if metadata.geometryColumn == "":
            return None
        sql = "SELECT                      \n" \
              "    st_xmin(st_extent(%s)), \n" \
              "    st_ymin(st_extent(%s)), \n" \
              "    st_xmax(st_extent(%s)), \n" \
              "    st_ymax(st_extent(%s))  \n" \
              "FROM %s.%s                   " \
              % (metadata.geometryColumn, metadata.geometryColumn, metadata.geometryColumn, metadata.geometryColumn, schema, metadata.tableName.modifiedValue)

        cur = self.m_connection.cursor()
        cur.execute(sql)
        res = cur.fetchone()
        if res is None:
            return

        xmin, ymin, xmax, ymax = res

        metadata.setModified("westLong", xmax)
        metadata.setModified("eastLong", xmin)
        metadata.setModified("southLat", ymin)
        metadata.setModified("northLat", ymax)

class Database(DatabaseBase):
    def __init__(self, db, provUserName, provPassword):
        super(Database, self).__init__()
        self.m_connection = DBConnWrapper(db, "QSQLITE")
        self.m_name = db

        if not self.checkPassword(provUserName, provPassword):
            if provUserName != "Admin" or provPassword != "Admin":
                raise WrongUserPass()
            else:
                self.m_userName = "Admin"
                self.m_isAdmin = True
                self.m_password = encryptPassword(provPassword, self.otherGeneral[0])

        cur = self.m_connection.cursor()
        cur.execute("PRAGMA foreign_keys = ON")

    def name(self):
        return self.m_name

    def executeListQuery(self, query):
        cur = self.m_connection.cursor()
        cur.execute(query)
        res = cur.fetchall()
        if len(res) == 0:
            return res

        if len(res[0]) == 1:
            return [i[0] for i in res]
        else:
            return res

    def localTableList(self, connId, orphans):
        if not orphans:
            return self.executeListQuery("SELECT table_name FROM sm_tables WHERE conn_id = %s" % connId)
        else:
            return self.executeListQuery("SELECT table_name                       \n" \
                                         "FROM sm_tables WHERE                    \n" \
                                         "    conn_id = %s AND                    \n" \
                                         "    md_id IS NULL OR                    \n" \
                                         "    md_id NOT IN                        \n" \
                                         "          (SELECT res_id FROM md_resource)" % connId)

    def localTableAndTitleList(self, connId, orphans):
        if not orphans:
            return self.executeListQuery("SELECT table_name, title FROM sm_tables WHERE conn_id = %s" % connId)
        else:
            return self.executeListQuery(
                "SELECT table_name, title              \n" \
                "FROM sm_tables                        \n" \
                "WHERE                                 \n" \
                "    conn_id = %s AND                  \n" \
                "    md_id IS NULL OR                  \n" \
                "    md_id NOT IN                      \n" \
                "        (SELECT res_id FROM md_resource)" % connId)

    def dataPolicy(self, connId, tableName):
        cur = self.m_connection.cursor()
        cur.execute("SELECT                                                                         \n"
                    "   md_resource.use_limitation, md_resource.copyright,                          \n"
                    "   md_resource.legal_restr_use, md_resource.legal_restr_access,                \n"
                    "   md_resource.ref_dates, sm_tables.table_id, md_resource.res_id               \n"
                    "FROM sm_tables, md_resource                                                    \n"
                    "WHERE                                                                          \n"
                    "   sm_tables.md_id == md_resource.res_id and                                   \n"
                    "   sm_tables.table_name == '%s' and sm_tables.conn_id == %s                    \n" % (quoteString(tableName), connId))
        qres = cur.fetchone()

        res = TableDataPolicy()
        if qres is None:
            cur.execute("SELECT                    \n"
                        "   table_id               \n"
                        "FROM sm_tables            \n"
                        "WHERE                     \n"
                        "   table_name == '%s' AND \n"
                        "   conn_id == %s          \n" % (quoteString(tableName), connId))
            qres = cur.fetchone()
            res.tableId = qres[-1]
            return res

        res.dataAccess = Value(qres[0])
        res.copyright = Value(qres[1])
        res.useRight = Value(qres[2])
        res.classification = Value(qres[3])
        res.referenceDate = Value(qres[4])

        res.tableId = qres[-2]
        res.resId = qres[-1]

        return res

    def saveDataPolicy(self, connId, dataPolicy):
        cur = self.m_connection.cursor()

        mdResColVals = [("use_limitation", dataPolicy.dataAccess),
                        ("copyright", dataPolicy.copyright),
                        ("legal_restr_use", dataPolicy.useRight),
                        ("legal_restr_access", dataPolicy.classification),
                        ("ref_dates", dataPolicy.referenceDate)]

        update_sql = "UPDATE md_resource   \n" \
                     "SET                  \n"
        update_sql += (",\n").join(["    " + col + " = '" + str(val.modifiedValue) + "'" for col, val in mdResColVals])
        update_sql += "\n WHERE             \n" \
                     "     res_id = %s      \n" % dataPolicy.resId

        insert_sql = "INSERT INTO md_resource \n("
        insert_sql += (",\n").join([col  for col, val in mdResColVals])
        insert_sql += ")\nVALUES\n("
        insert_sql += (",\n").join(["'" + str(val.modifiedValue) +  "'" for col, val in mdResColVals])
        insert_sql += ")\n"

        if dataPolicy.resId != 0:
            cur.execute(update_sql)
        else:
            cur.execute(insert_sql)
            dataPolicy.resId = cur.lastInsertId()
            update_table_sql = "UPDATE sm_tables      \n" \
                               "    set  md_id = %s   \n" \
                               "WHERE                 \n" \
                               "     conn_id = %s AND \n" \
                               "     table_id = %s    \n" % (dataPolicy.resId, connId, dataPolicy.tableId)
            cur.execute(update_table_sql)

    def deleteDataPolicy(self, connId, dataPolicy):
        if dataPolicy.resId == 0:
            return
        cur = self.m_connection.cursor()
        delete_sql =  "UPDATE md_resource               \n" \
                      "SET                              \n" \
                      "    use_limitation = NULL,       \n" \
                      "    copyright = NULL,            \n" \
                      "    legal_restr_use = NULL,      \n" \
                      "    legal_restr_access = NULL,   \n" \
                      "    ref_dates = NULL             \n" \
                      "WHERE                            \n" \
                      "    res_id = %s                  \n" % dataPolicy.resId

        cur.execute(delete_sql)

    def metadata(self, connId, tableName):
        cur = self.m_connection.cursor()
        cur.execute("SELECT                                                                         \n"
                    "   sm_tables.title, md_resource.title, md_resource.alt_title,                  \n"
                    "   sm_tables.description, md_resource.abstract,                                \n"
                    "   md_resource.topic_cat, md_resource.hier, md_resource.temporal_from, md_resource.temporal_to,  \n"
                    "   md_resource.maint_freq, md_resource.status, md_resource.lang,               \n"
                    "   md_resource.cntct_id, md_resource.west_long, md_resource.east_long,         \n"
                    "   md_resource.south_lat, md_resource.north_lat, md_resource.spat_rep_type,    \n"
                    "   md_resource.spat_res, md_resource.lineage, md_resource.lnge_maint,          \n"
                    "   md_resource.ref_system, md_resource.char_set, md_resource.dt_nxt_upd,       \n"
                    "   md_resource.keywords, md_resource.md_online,                                \n"
                    "   sm_tables.table_id, md_resource.res_id                                      \n"
                    "FROM sm_tables, md_resource                                                    \n"
                    "WHERE                                                                          \n"
                    "   sm_tables.md_id == md_resource.res_id AND                                   \n"
                    "   sm_tables.table_name == '%s' AND sm_tables.conn_id == %s                    \n" % (quoteString(tableName), connId))
        qres = cur.fetchone()

        res = TableMetadata()
        res.tableName = Value(tableName)
        if qres is None:
            cur.execute("SELECT                    \n"
                        "   title,                 \n"
                        "   description,           \n"
                        "   table_id               \n"
                        "FROM sm_tables            \n"
                        "WHERE                     \n"
                        "   table_name == '%s' AND \n"
                        "   conn_id == %s          \n" % (quoteString(tableName), connId))
            qres = cur.fetchone()
            res.title = Value(qres[0])
            res.description = Value(qres[1])
            res.tableId = qres[-1]
            return res

        if qres[1] == "":
            res.title = Value(qres[0])
        else:
            res.title = Value(qres[1])
        res.alternativeTitle = Value(qres[2])
        res.description = Value(qres[3])
        res.abstract = Value(qres[4])
        res.theme = Value(qres[5])
        res.hierarchy = Value(qres[6])
        res.temporalRangeStartDate = Value(qres[7])
        res.temporalRangeEndDate = Value(qres[8])
        res.temporalRangeUpdates = Value(qres[9])
        res.temporalRangeStatus = Value(qres[10])
        res.language = Value(qres[11])
        res.contactId = Value(qres[12])
        res.westLong = Value(qres[13])
        res.eastLong = Value(qres[14])
        res.southLat = Value(qres[15])
        res.northLat = Value(qres[16])
        res.dataType = Value(qres[17])
        res.precisionResolution = Value(qres[18])
        res.lineageStatement = Value(qres[19])
        res.lineageMaintain = Value(qres[20])

        res.referenceSystem = Value(qres[21])
        res.charset = Value(qres[22])
        res.updateDateStamp = Value(qres[23])
        res.keywords = Value(qres[24])
        res.onlineURL = Value(qres[25])

        res.referenceSystem = Value(self.schemaProperties(connId).properties[3])
        res.charset = Value(self.schemaProperties(connId).properties[2])

        res.tableId = qres[-2]
        res.resId = qres[-1]

        return res

    def saveMetadata(self, connId, metadata):
        cur = self.m_connection.cursor()

        mdResColVals = [("title", metadata.title),
                        ("alt_title", metadata.alternativeTitle),
                        ("abstract", metadata.abstract),
                        ("topic_cat", metadata.theme),
                        ("hier", metadata.hierarchy),
                        ("temporal_from", metadata.temporalRangeStartDate),
                        ("temporal_to", metadata.temporalRangeEndDate),
                        ("maint_freq", metadata.temporalRangeUpdates),
                        ("status", metadata.temporalRangeStatus),
                        ("lang", metadata.language),
                        ("cntct_id", metadata.contactId),
                        ("west_long", metadata.westLong),
                        ("east_long", metadata.eastLong),
                        ("south_lat", metadata.southLat),
                        ("north_lat", metadata.northLat),
                        ("spat_rep_type", metadata.dataType),
                        ("spat_res", metadata.precisionResolution),
                        ("lineage", metadata.lineageStatement),
                        ("lnge_maint", metadata.lineageMaintain),
                        ("ref_system", metadata.referenceSystem),
                        ("char_set", metadata.charset),
                        ("dt_nxt_upd", metadata.updateDateStamp),
                        ("keywords", metadata.keywords),
                        ("md_online", metadata.onlineURL)]

        for idx in range(len(mdResColVals)):
            col, val = mdResColVals[idx]
            val = quoteString(str(val.modifiedValue))
            mdResColVals[idx] = (col, val)

        update_sql = "UPDATE md_resource    \n" \
                     "SET                   \n"
        update_sql += (",\n").join(["    " + col + " = '" + str(val) + "'" for col, val in mdResColVals])
        update_sql += "\nWHERE              \n" \
                     "     res_id = %s      \n" % metadata.resId

        insert_sql = "INSERT INTO md_resource \n("
        insert_sql += (",\n").join([col  for col, val in mdResColVals])
        insert_sql += ")\nVALUES\n("
        insert_sql += (",\n").join(["'" + str(val) +  "'" for col, val in mdResColVals])
        insert_sql += ")\n"

        if metadata.resId != 0:
            cur.execute(update_sql)
        else:
            cur.execute(insert_sql)
            metadata.resId = cur.lastInsertId()
            update_table_sql = "UPDATE sm_tables     \n" \
                               "    SET  md_id = %s  \n" \
                               "WHERE                \n" \
                               "    conn_id = %s AND \n" \
                               "    table_id = %s    \n" % (metadata.resId, connId, metadata.tableId)
            cur.execute(update_table_sql)

    def deleteMetadata(self, connId, metadata):
        if metadata.resId == 0:
            return
        cur = self.m_connection.cursor()
        delete_sql = "DELETE FROM md_resource  \n"\
                     "WHERE                    \n"\
                     "  res_id = %s            \n" % metadata.resId
        cur.execute(delete_sql)
        # sm_tables will be automatically updated by foreign key constraint

    def userName(self):
        return self.m_userName

    def passwordEncrypted(self):
        return self.m_password

    def qtDatabase(self):
        return self.m_connection.qtDatabase()

    def schemaProperties(self, connId):
        return SchemaProperties(self.m_connection, connId)

    globalNamingConvChanged = pyqtSignal()

    globalNamingConv = DBVariablesDescriptor("sm_db_sett",
            ['sm_type', 'sm_variable'       , 'description'      , 'sm_value'],
           [('T'      , 'GNC_SPTAB_PREFIX'  , 'Spatial Table Prefix'),
            ('T'      , 'GNC_NSPTAB_PREFIX' , 'Non-Spatial Table Prefix'),
            ('T'      , 'GNC_SYSTAB_PREFIX' , 'System Table Prefix'),
            ('T'      , 'GNC_LUTAB_PREFIX'  , 'Lookup Table Prefix'),
            ('T'      , 'GNC_LNKTAB_PREFIX' , 'Link Table Prefix'),
            ('T'      , 'GNC_UIDCOL_NAME'   , 'Unique Identifier Column Name'),
            ('T'      , 'GNC_GEOMCOL_NAME'  , 'Geometry Column Name'),
            ('T'      , 'GNC_RASTERCOL_NAME', 'Raster Column Name')], 1)

    globalTableUsagePolicy = DBVariablesDescriptor("sm_db_sett",
            ['sm_type', 'sm_variable'      , 'description'      , 'sm_value'],
           [('T'      , 'USE_POL_DATAACCESS' , 'General Data Access policy'),
            ('T'      , 'USE_POL_COPYRIGHT', 'General Data Copyright policy'),
            ('T'      , 'USE_POL_USERIGHTS', 'General Data Usage policy'),
            ('T'      , 'USE_POL_CLASS', 'General Data Classification')], 1)

    generalSettings = DBVariablesDescriptor("sm_db_sett",
            ['sm_type', 'sm_variable'      , 'description'      , 'sm_value'],
           [('T'      , 'ORGNAME'          , 'Organisation Name'),
            ('T'      , 'ORGPHONE'         , 'Phone Number'),
            ('T'      , 'ORGEMAIL'         , 'General Email'),
            ('T'      , 'ORGADD1'          , 'Main Address 1'),
            ('T'      , 'ORGADD2'          , 'Main Address 2'),
            ('T'      , 'ORGADD3'          , 'Main Address 3'),
            ('T'      , 'ORGPCODE'         , 'Postal Code')], 1)

    otherGeneral = DBVariablesDescriptor("sm_db_sett",
            ['sm_type', 'sm_variable'      , 'description'      , 'sm_value'],
           [('T'      , 'GNC_ENC_SALT'     , 'Encryption Salt'),
            ('T'      , 'ORGNOTE'          , 'Note')], 1, [0])

    def checkPassword(self, provUserName, provPassword):
        info = self.userInfo(provUserName)
        if info is None:
            return False

        password, isAdmin = info
        if password != encryptPassword(provPassword, self.otherGeneral[0]):
            return False

        self.m_userName = provUserName
        self.m_isAdmin = isAdmin
        self.m_password = password
        return True

    # Users management
    userListChangedSignal = pyqtSignal()

    def userList(self):
        cur = self.m_connection.cursor()
        cur.execute("SELECT user_name FROM sm_auth_user;")
        res = cur.fetchall()
        return [i[0] for i in res]

    def addUser(self, userName):
        cur = self.m_connection.cursor()
        cur.execute("INSERT  INTO sm_auth_user              \n"
                    "    (user_name)                        \n"
                    "VALUES                                 \n"
                    "    ('%s')                             \n"
                    % quoteString(userName))
        self.m_connection.commit()
        self.userListChangedSignal.emit()

    def deleteUser(self, userName):
        cur = self.m_connection.cursor()
        cur.execute("DELETE FROM sm_auth_user              \n"
                    "WHERE                                  \n"
                    "    user_name = '%s'                   \n"
                    % quoteString(userName))
        self.m_connection.commit()
        self.userListChangedSignal.emit()

    def saveUserData(self, userName, password, isAdmin):
        cur = self.m_connection.cursor()
        cur.execute("UPDATE sm_auth_user                    \n"
                    "SET                                    \n"
                    "    user_password = '%s',              \n"
                    "    isadmin = '%s'                     \n"
                    "WHERE                                  \n"
                    "    user_name = '%s'                   \n"
                    % (encryptPassword(password, self.otherGeneral[0]), 'Y' if isAdmin else 'N', quoteString(userName)))
        self.m_connection.commit()

    def userInfo(self, userName):
        cur = self.m_connection.cursor()
        cur.execute("SELECT                                 \n"
                    "     user_password, isadmin            \n"
                    "FROM                                   \n"
                    "     sm_auth_user                      \n"
                    "WHERE                                  \n"
                    "    user_name ='%s'                    \n"
                    % quoteString(userName))
        res = cur.fetchone()
        if res is None:
            return None
        return "" if res[0] is None else res[0], True if res[1] == 'Y' else False


    # Schema groups management
    schemaGroupListChangedSignal = pyqtSignal()

    def schemaGroupList(self, conn_id):
        cur = self.m_connection.cursor()
        cur.execute("SELECT tblgrp_name FROM sm_tblgrp WHERE conn_id = '%s'" % conn_id)
        res = cur.fetchall()
        return [i[0] for i in res]

    def addSchemaGroup(self, connId, groupName):
        cur = self.m_connection.cursor()
        cur.execute("INSERT  INTO sm_tblgrp                 \n"
                    "    (tblgrp_name, conn_id)             \n"
                    "VALUES                                 \n"
                    "    ('%s', %s)                         \n"
                    % (quoteString(groupName), connId))
        self.m_connection.commit()
        self.schemaGroupListChangedSignal.emit()

    def deleteSchemaGroup(self, connId, groupName):
        cur = self.m_connection.cursor()
        cur.execute("DELETE FROM sm_tblgrp                  \n"
                    "WHERE                                  \n"
                    "    tblgrp_name = '%s' and             \n"
                    "    conn_id = '%s'                     \n"
                    % (quoteString(groupName), connId))
        self.m_connection.commit()
        self.schemaGroupListChangedSignal.emit()

    def saveSchemasGroupData(self, connId, name, descr, prefix, menu):
        cur = self.m_connection.cursor()
        cur.execute("UPDATE sm_tblgrp                       \n"
                    "SET                                    \n"
                    "    tblgrp_descr = '%s',               \n"
                    "    tblgrp_grp_prefix = '%s',          \n"
                    "    tblgrp_menuname = '%s'             \n"
                    "WHERE                                  \n"
                    "    tblgrp_name = '%s' and             \n"
                    "    conn_id = '%s'                     \n"
                    % (quoteString(descr), quoteString(prefix), quoteString(menu), quoteString(name), connId))
        self.m_connection.commit()

    def schemaGroupInfo(self, connId, groupName):
        cur = self.m_connection.cursor()
        cur.execute("SELECT                                                       \n"
                    "     tblgrp_descr, tblgrp_grp_prefix, tblgrp_menuname        \n"
                    "FROM                                                         \n"
                    "     sm_tblgrp                                               \n"
                    "WHERE                                                        \n"
                    "    tblgrp_name ='%s' AND                                    \n"
                    "    conn_id ='%s'                                            \n"
                    % (quoteString(groupName), connId))
        res = cur.fetchone()
        if res is None:
            return None
        return res

    # Table info
    def deleteTableInfo(self, tableName, connId):
        cur = self.m_connection.cursor()
        cur.execute("DELETE                                                                \n"
                    "FROM                                                                  \n"
                    "     sm_tables                                                        \n"
                    "WHERE                                                                 \n"
                    "    table_name ='%s' AND                                              \n"
                    "    conn_id ='%s'                                                     \n"
                    % (quoteString(tableName.lower()), connId))

    def tableInfo(self, tableName, connId):
        cur = self.m_connection.cursor()
        cur.execute("SELECT                                                                \n"
                    "     group_id, title, description, is_spatial, sp_type                \n"
                    "FROM                                                                  \n"
                    "     sm_tables                                                        \n"
                    "WHERE                                                                 \n"
                    "    table_name ='%s' AND                                              \n"
                    "    conn_id ='%s'                                                     \n"
                    % (quoteString(tableName.lower()), connId))
        res = cur.fetchone()
        if res is None:
            return (None, None, None, None, None, False)
        grpId = res[0]
        if (grpId == -1) or (grpId == ""): # Testing with -1 for backward compatibility. New flows should set NULL
            return ("FromDB",) + res[1:] + (True,)

        cur.execute("SELECT                \n"
                    "     tblgrp_name      \n" 
                    "FROM                  \n"
                    "     sm_tblgrp        \n"
                    "WHERE                 \n"
                    "     tblgrp_id = %s   \n" % grpId)
        gres = cur.fetchone()
        return gres + res[1:] + (True,)

    def columnInfos(self, from_client_db, tableName, connId):
        if len(from_client_db) == 0:
            return []
        sql = "SELECT \n" \
              "       sm_tb_cols.col_name,      \n" \
              "       sm_tb_cols.col_desc,      \n" \
              "       sm_tb_cols.col_type,      \n" \
              "       sm_tb_cols.col_size,      \n" \
              "       sm_tb_cols.col_scale,     \n" \
              "       sm_tb_cols.col_units,     \n" \
              "       sm_tb_cols.default_value, \n" \
              "       sm_tb_cols.lu_table,      \n" \
              "       sm_tb_cols.column_maxval, \n" \
              "       sm_tb_cols.column_minval, \n" \
              "       sm_tb_cols.is_primary_key,\n" \
              "       sm_tb_cols.nullok         \n" \
              "FROM sm_tables, sm_tb_cols       \n" \
              "WHERE                            \n" \
              "       sm_tb_cols.table_id == sm_tables.table_id AND\n" \
              "       sm_tables.conn_id == %s AND\n" \
              "       sm_tables.table_name == '%s' AND\n       (" % (connId, tableName)
        sql += " OR\n       ".join(["sm_tb_cols.col_name = '%s'" % quoteString(name[0]) for name in from_client_db])
        sql += "\n       )"

        sql += "\nORDER BY col_name ASC"

        cur = self.m_connection.cursor()
        cur.execute(sql)

        res = cur.fetchall()
        return res

    def columnInfoByTable(self, tableName):
        sql = "SELECT \n" \
              "       sm_tb_cols.col_name,      \n" \
              "       sm_tb_cols.col_desc,      \n" \
              "       sm_tb_cols.col_type,      \n" \
              "       sm_tb_cols.col_size,      \n" \
              "       sm_tb_cols.col_scale,     \n" \
              "       sm_tb_cols.col_units,     \n" \
              "       sm_tb_cols.default_value, \n" \
              "       sm_tb_cols.lu_table,      \n" \
              "       sm_tb_cols.column_maxval, \n" \
              "       sm_tb_cols.column_minval, \n" \
              "       sm_tb_cols.is_primary_key,\n" \
              "       sm_tb_cols.nullok         \n" \
              "FROM sm_tables, sm_tb_cols       \n" \
              "WHERE                            \n" \
              "       sm_tb_cols.table_id == sm_tables.table_id AND\n" \
              "       sm_tables.table_name == '%s'" % tableName

        cur = self.m_connection.cursor()
        cur.execute(sql)

        res = cur.fetchall()
        return res

    def tableId(self, tableName, connId):
        sql = "SELECT                     \n" \
              "    table_id               \n" \
              "FROM                       \n" \
              "    sm_tables              \n" \
              "WHERE                      \n" \
              "    table_name = '%s' AND  \n" \
              "    conn_id = %s           " % (quoteString(tableName.lower()), connId)
        cur = self.m_connection.cursor()
        cur.execute(sql)

        res = cur.fetchall()
        return res


    def saveTableInfo(self, tableName, connId, group, title, description, isSpatial, spatialType):
        cur = self.m_connection.cursor()
        cur.execute("SELECT                       \n"
                    "     tblgrp_id               \n"
                    "FROM                         \n"
                    "     sm_tblgrp               \n"
                    "WHERE                        \n"
                    "    tblgrp_name = '%s' AND   \n"
                    "    conn_id = '%s'           \n"
                    % (quoteString(group), connId))
        res = cur.fetchone()
        if res is None:
            groupId = "NULL"
        else:
            groupId = res[0]

        update_sql = "UPDATE sm_tables        \n" \
                     "SET table_name = '%s',  \n" \
                     "    group_id = %s,      \n" \
                     "    title = '%s',       \n" \
                     "    description = '%s', \n" \
                     "    is_spatial = '%s',  \n" \
                     "    sp_type = %s        \n" \
                     "WHERE                   \n" \
                     "    conn_id = '%s' AND  \n" \
                     "    table_name = '%s'   \n" % \
                     (quoteString(tableName.modifiedValue.lower()), quoteString(groupId), quoteString(title), quoteString(description), isSpatial[0], \
                      ("NULL" if isSpatial[0] == "N" else "'" + spatialType + "'"), connId, quoteString(tableName.originalValue))

        set_sql = "INSERT INTO sm_tables                                                          \n" \
                  "   (table_name, group_id, title, description, is_spatial, sp_type, conn_id)    \n" \
                  "VALUES                                                                         \n" \
                  "   ('%s', %s, '%s', '%s', '%s', %s, %s)                                        \n" \
                    % (quoteString(tableName.modifiedValue.lower()), quoteString(groupId), quoteString(title), quoteString(description), isSpatial[0], ("NULL" if isSpatial[0] == "N" else "'" + spatialType + "'"), connId)

        cur.execute(update_sql)
        if cur.numRowsAffected() == 0:
            cur.execute(set_sql)

    def saveColumnInfo(self, row, tableId, schema, connId):

        cur = self.m_connection.cursor()
        modifiedTuple = row.modifiedTuple()
        YNmodifiedTuple = modifiedTuple[:-2] + ('Y' if modifiedTuple[-2] == "Yes" else "N", 'Y' if modifiedTuple[-1] == "Yes" else "N")
        args = ((connId, tableId) + tuple(quoteString(str) for str in YNmodifiedTuple) + (row.value(0).originalValue,))
        insert_args = ((connId, tableId) + tuple(quoteString(str) for str in YNmodifiedTuple))

        update_sql = "UPDATE sm_tb_cols                \n" \
                     "SET col_name = '{2}',            \n" \
                     "    col_desc = '{3}',            \n" \
                     "    col_type = '{4}',            \n" \
                     "    col_size = '{5}',            \n" \
                     "    col_scale = '{6}',           \n" \
                     "    col_units = '{7}',           \n" \
                     "    default_value = '{8}',       \n" \
                     "    lu_table = '{9}',            \n" \
                     "    column_maxval = '{10}',      \n" \
                     "    column_minval = '{11}',      \n" \
                     "    is_primary_key = '{12}',     \n" \
                     "    nullok = '{13}'              \n" \
                     "WHERE                            \n" \
                     "    conn_id = '{0}' AND          \n" \
                     "    table_id = '{1}' AND         \n" \
                     "    col_name = '{14}'            \n".format(*args)

        insert_sql = ("INSERT INTO sm_tb_cols   \n" \
                      "     (conn_id,           \n" \
                      "      table_id,          \n" \
                      "      col_name,          \n" \
                      "      col_desc,          \n" \
                      "      col_type,          \n" \
                      "      col_size,          \n" \
                      "      col_scale,         \n" \
                      "      col_units,         \n" \
                      "      default_value,     \n" \
                      "      lu_table,          \n" \
                      "      column_maxval,     \n" \
                      "      column_minval,     \n" \
                      "      is_primary_key,    \n" \
                      "      nullok)            \n" \
                      "VALUES                   \n" \
                      "('%s', '%s', " + ", ".join(["'%s'"] * len(row.modifiedTuple())) + ");") % insert_args

        delete_sql = "DELETE FROM sm_tb_cols     \n"\
                     "WHERE                      \n"\
                     "    conn_id = '{0}' AND    \n"\
                     "    table_id = '{1}' AND   \n"\
                     "    col_name = '{2}'".format(connId, tableId, row.value(0).modifiedValue)
        if row.added():
            cur.execute(insert_sql)
        elif row.deleted():
            cur.execute(delete_sql)
        else:
            cur.execute(update_sql)
            if cur.numRowsAffected() == 0:
                cur.execute(insert_sql)

    def commonColumnsInfo(self, connId):
        sql = "SELECT def_col_id,      \n" \
              "       col_name,        \n" \
              "       col_desc,        \n" \
              "       col_type,        \n" \
              "       col_size,        \n" \
              "       col_scale,       \n" \
              "       col_units,       \n" \
              "       default_value,   \n" \
              "       lu_table,        \n" \
              "       column_maxval,   \n" \
              "       column_minval,   \n" \
              "       is_primary_key,  \n" \
              "       nullok           \n" \
              "FROM sm_tb_def_cols     \n" \
              "WHERE conn_id = %s      " % connId

        sql += "ORDER BY col_name ASC"

        cur = self.m_connection.cursor()
        cur.execute(sql)

        res = cur.fetchall()
        ares = []
        for r in res:
            ares.append(r[:-2] + ("Yes" if r[-2] == 'Y' else "No", "Yes" if r[-1] == 'Y' else "No"))
        return ares

    def saveCommonColumnInfo(self, row, connId):
        cur = self.m_connection.cursor()
        modifiedTuple = row.modifiedTuple()
        YNmodifiedTuple = modifiedTuple[:-2] + ('Y' if modifiedTuple[-2] == "Yes" else 'N',) + ('Y' if modifiedTuple[-1] == "Yes" else 'N',)
        args = ((connId,) + tuple(quoteString(str) for str in YNmodifiedTuple) + (row.value(0).originalValue,))
        insert_args = ((connId, ) + tuple(quoteString(str) for str in YNmodifiedTuple))

        update_sql = "UPDATE sm_tb_def_cols            \n" \
                     "SET  col_name = '{1}',           \n" \
                     "     col_desc = '{2}',           \n" \
                     "     col_type = '{3}',           \n" \
                     "     col_size = '{4}',           \n" \
                     "     col_scale = '{5}',          \n" \
                     "     col_units = '{6}',          \n" \
                     "     default_value = '{7}',      \n" \
                     "     lu_table = '{8}',           \n" \
                     "     column_maxval = '{9}',      \n" \
                     "     column_minval = '{10}',     \n" \
                     "     is_primary_key = '{11}',    \n" \
                     "     nullok = '{12}'             \n" \
                     "WHERE                            \n" \
                     "     conn_id = '{0}' AND         \n" \
                     "     col_name = '{13}'           \n".format(*args)

        insert_sql = ("INSERT INTO sm_tb_def_cols   \n" \
                      "    (conn_id,                \n" \
                      "    col_name,                \n" \
                      "    col_desc,                \n" \
                      "    col_type,                \n" \
                      "    col_size,                \n" \
                      "    col_scale,               \n" \
                      "    col_units,               \n" \
                      "    default_value,           \n" \
                      "    lu_table,                \n" \
                      "    column_maxval,           \n" \
                      "    column_minval,           \n" \
                      "    is_primary_key,          \n" \
                      "    nullok)                  \n" \
                      "VALUES                       \n" \
                      "('%s', " + ", ".join(["'%s'"] * len(row.modifiedTuple())) + ");") % insert_args

        delete_sql = "DELETE FROM sm_tb_def_cols  \n"\
                     "WHERE                       \n"\
                     "    conn_id = '{0}' AND     \n"\
                     "    col_name = '{1}'".format(connId, row.value(0).modifiedValue)
        if row.added():
            cur.execute(insert_sql)
        elif row.deleted():
            cur.execute(delete_sql)
        else:
            cur.execute(update_sql)
            if cur.numRowsAffected() == 0:
                cur.execute(insert_sql)

    # Contacts management
    contactListChangedSignal = pyqtSignal()

    def contactList(self):
        cur = self.m_connection.cursor()
        cur.execute("SELECT cntct_name, cntct_surname, cntct_id FROM md_contact")
        res = cur.fetchall()
        return res

    def hierList(self):
        cur = self.m_connection.cursor()
        cur.execute("SELECT hier_lvl_name, hier_lvl_id FROM md_hier")
        res = cur.fetchall()
        return res

    def addContact(self, contactName, contactSurname):
        cur = self.m_connection.cursor()
        cur.execute("INSERT INTO md_contact                 \n"
                    "    (cntct_name, cntct_surname)        \n"
                    "VALUES                                 \n"
                    "    ('%s', '%s')                       \n"
                    % (quoteString(contactName), quoteString(contactSurname)))
        self.m_connection.commit()
        self.contactListChangedSignal.emit()

    def deleteContact(self, contactId):
        cur = self.m_connection.cursor()
        cur.execute("DELETE FROM md_cntct_addr             \n"
                    "WHERE                                 \n"
                    "    cntct_id = '%s'                   \n"
                    % contactId)
        cur.execute("DELETE FROM md_contact                \n"
                    "WHERE                                 \n"
                    "    cntct_id = '%s'                   \n"
                    % contactId)
        self.m_connection.commit()
        self.contactListChangedSignal.emit()

    def saveContactData(self, name, surname, department, position, role):
        cur = self.m_connection.cursor()
        cur.execute("UPDATE md_contact                     \n"
                    "SET                                   \n"
                    "    cntct_dpt = '%s',                 \n"
                    "    cntct_pos = '%s',                 \n"
                    "    cntct_role = '%s'                 \n"
                    "WHERE                                 \n"
                    "    cntct_name = '%s' and             \n"
                    "    cntct_surname = '%s'              \n"
                    % (quoteString(department), quoteString(position), quoteString(role), quoteString(name), quoteString(surname)))
        self.m_connection.commit()

    def contactInfo(self, contactName, contactSurname):
        cur = self.m_connection.cursor()
        cur.execute("SELECT                                                                      \n"
                    "     cntct_id, cntct_name, cntct_surname, cntct_dpt, cntct_pos, cntct_role  \n"
                    "FROM                                                                        \n"
                    "     md_contact                                                             \n"
                    "WHERE                                                                       \n"
                    "    cntct_name ='%s' AND                                                    \n"
                    "    cntct_surname ='%s'                                                     \n"
                    % (quoteString(contactName), quoteString(contactSurname)))
        res = cur.fetchone()
        if res is None:
            return None
        return tuple("" if r is None else r for r in res)

    def contactAddressInfo(self, contactId):
        cur = self.m_connection.cursor()
        cur.execute("SELECT                                              \n"
                    "     cntct_addr_id, cntct_addr_type, cntct_addr_val \n"
                    "FROM                                                \n"
                    "     md_cntct_addr                                  \n"
                    "WHERE                                               \n"
                    "    cntct_id ='%s'                                  \n"
                    % contactId)
        res = cur.fetchall()
        if res is None:
            return None
        return res

    def saveContactAddressInfo(self, row, contactId):

        cur = self.m_connection.cursor()
        modifiedTuple = row.modifiedTuple()
        args = ((row.id(),) + tuple(quoteString(str) for str in modifiedTuple))
        insert_args = ((contactId,) + tuple(quoteString(str) for str in modifiedTuple))

        update_sql = "UPDATE md_cntct_addr           \n" \
                     "SET cntct_addr_type = '{1}',   \n" \
                     "    cntct_addr_val = '{2}',    \n" \
                     "WHERE                          \n" \
                     "    cntct_addr_id = '{0}'      \n".format(*args)

        insert_sql = ("INSERT INTO md_cntct_addr  \n" \
                      "    (cntct_id,             \n" \
                      "    cntct_addr_type,       \n" \
                      "    cntct_addr_val)        \n" \
                      "VALUES                     \n" \
                      "('%s', '%s', '%s');          ") % insert_args

        delete_sql = "DELETE FROM md_cntct_addr  \n"\
                     "WHERE                      \n"\
                     "    cntct_addr_id = '{0}'  \n".format(row.id())
        if row.added():
            cur.execute(insert_sql)
        elif row.deleted():
            cur.execute(delete_sql)
        else:
            cur.execute(update_sql)
            if cur.numRowsAffected() == 0:
                cur.execute(insert_sql)

    # Availble services
    def availbleServicesInfo(self):
        cur = self.m_connection.cursor()
        cur.execute("SELECT                                           \n"
                    "     webserv_id, webserv_descr, webserv_URL,     \n"
                    "     webserv_usr, webserv_pwd, webserv_maxfeat   \n"
                    "FROM                                             \n"
                    "     sm_webserv                                  \n")

        res = cur.fetchall()
        if res is None:
            return None
        return res

    def saveAvailbleServicesInfo(self, row):
        cur = self.m_connection.cursor()
        modifiedTuple = row.modifiedTuple()
        args = ((row.id(),) + tuple(quoteString(str) for str in modifiedTuple))
        insert_args = tuple(quoteString(str) for str in modifiedTuple)

        update_sql = "UPDATE sm_webserv              \n" \
                     "SET webserv_descr = '{1}',     \n" \
                     "    webserv_URL = '{2}',       \n" \
                     "    webserv_usr = '{3}',       \n" \
                     "    webserv_pwd = '{4}',       \n" \
                     "    webserv_maxfeat = '{5}'    \n" \
                     "WHERE                          \n" \
                     "    webserv_id = '{0}'         \n".format(*args)

        insert_sql = ("INSERT INTO sm_webserv       \n" \
                      "    (webserv_descr,          \n" \
                      "    webserv_URL,             \n" \
                      "    webserv_usr,             \n" \
                      "    webserv_pwd,             \n" \
                      "    webserv_maxfeat)         \n" \
                      "VALUES                         " \
                      "    ('%s', '%s', '%s', '%s', '%s');") % insert_args

        delete_sql = "DELETE FROM sm_webserv    \n" \
                     "WHERE                     \n" \
                     "    webserv_id = '{0}'    \n".format(row.id())
        if row.added():
            cur.execute(insert_sql)
        elif row.deleted():
            cur.execute(delete_sql)
        else:
            cur.execute(update_sql)
            if cur.numRowsAffected() == 0:
                cur.execute(insert_sql)

    # Connection management
    connectionListChangedSignal = pyqtSignal()

    def connectionList(self):
        cur = self.m_connection.cursor()
        cur.execute("SELECT conns_dbschema FROM sm_conns")
        res = cur.fetchall()
        return [i[0] for i in res]

    def addConnection(self, schema):
        cur = self.m_connection.cursor()
        cur.execute("INSERT INTO sm_conns                                \n"
                    "    (conns_dbschema, conns_active, conns_dbtype)    \n"
                    "VALUES                                              \n"
                    "    ('%s', 'Yes', 'PostgreSQL')                     \n"
                    % quoteString(schema))
        self.m_connection.commit()
        self.connectionListChangedSignal.emit()

    def deleteConnection(self, schema):
        cur = self.m_connection.cursor()
        cur.execute("DELETE FROM sm_conns                  \n"
                    "WHERE                                 \n"
                    "    conns_dbschema = '%s'             \n"
                    % quoteString(schema))
        self.m_connection.commit()
        self.connectionListChangedSignal.emit()

    def saveConnectionData(self, schema, active, dbtype, host, port, dbname, user, password):
        cur = self.m_connection.cursor()
        cur.execute("UPDATE sm_conns                       \n"
                    "SET                                   \n"
                    "    conns_active = '%s',              \n"
                    "    conns_dbtype  = '%s',             \n"
                    "    conns_dbhost = '%s',              \n"
                    "    conns_dbname = '%s',              \n"
                    "    conns_dbuser = '%s',              \n"
                    "    conns_dbpwd = '%s'                \n"
                    "WHERE                                 \n"
                    "    conns_dbschema = '%s'             \n"
                    % (quoteString(active), quoteString(dbtype), quoteString(Database.hostJoin(host, port)), quoteString(dbname), quoteString(user), quoteString(password), quoteString(schema)))
        self.m_connection.commit()

    @staticmethod
    def hostParse(host):
        pos = host.find(':')
        if pos == -1:
            return (host, None)
        return host[:pos], int(host[pos + 1:])

    @staticmethod
    def hostJoin(host, port):
        host, oldport = Database.hostParse(host)
        if port is None:
            return host
        return host + ":" + str(port)

    def connectionInfo(self, schema):
        cur = self.m_connection.cursor()
        cur.execute("SELECT                                                                      \n"
                    "     conns_id, conns_dbschema, conns_active, conns_dbtype, conns_dbhost,    \n"
                    "               conns_dbname, conns_dbuser, conns_dbpwd                      \n"
                    "FROM                                                                        \n"
                    "     sm_conns                                                               \n"
                    "WHERE                                                                       \n"
                    "    conns_dbschema ='%s'                                                    \n"
                    % quoteString(schema))
        res = cur.fetchone()
        if res is None:
            return None

        id, schema, active, dbType, host, dbName, user, password = tuple("" if r is None else r for r in res)
        host, port = Database.hostParse(host)
        return (id, schema, active, dbType, host, port, dbName, user, password)