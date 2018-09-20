
from Database import Database

database = Database("C:/up/db_edit/spatman.db", "Admin", "Admin")

def iterTableRaise(name, fields, cond):
    if isinstance(name, list):
        tables = ','.join(name)
    else:
        tables = name
    if fields is None:
        sql = "select * from %s" % tables
    else:
        sql = "select %s from %s" % (",".join(fields), tables)

    if cond is not None:
        sql += " where " + cond

    res = database.executeQueryNamed(sql)
    for rec in res:
        yield rec

def iterFieldsRaise(name):
    driver = database.qtDatabase().driver()
    rec = driver.record(name)
    if not rec.isEmpty():
        for idx in range(rec.count()):
            yield rec.fieldName(idx)

def iterQueryRaise(sql):
    res = database.executeQueryNamed(sql)
    for rec in res:
        yield rec

def iterTable(name, fields = None, cond = None):
    try:
        for item in iterTableRaise(name, fields, cond):
            yield item
    except Exception as e:
        print("Error: %s" % e)

def iterFields(sql):
    try:
        for item in iterFieldsRaise(sql):
            yield item
    except Exception as e:
        print("Error: %s" % e)


def iterQuery(sql):
    try:
        for item in iterQueryRaise(sql):
            yield item
    except Exception as e:
        print("Error: %s" % e)

xml = " "

def put(s):
    global xml
    xml += s

def putln(s):
    global xml
    xml += s
    xml += "\n"