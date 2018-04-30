import os
import configparser

def singleton(class_):
    instances = {}
    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]
    return getinstance

@singleton
class Configuration:
    def __init__(self):

        self.m_recentDatabases = []
        self.m_languages = []
        self.m_charsets = []
        self.m_currentSchema = None
        self.m_usernameToSave = ""
        self.m_passwdToSave = ""
        self.m_ogr2ogrDir = ""
        self.m_ogr2ogrFormats = []
        self.m_lastExportDir = ""
        self.m_reportTemplateDir = ""
        self.m_gdalDataDir = ""

        cfg_path = self.configFile()
        print("Loading configuration from '%s'" % cfg_path)
        if not os.path.exists(cfg_path) or not os.path.isfile(cfg_path):
            return

        config = configparser.ConfigParser()
        config.read(cfg_path)

        if 'DEFAULT' in config:
            if 'RECENT_DBS' in config['DEFAULT']:
                self.m_recentDatabases = config['DEFAULT']['RECENT_DBS'].split('+')
            if 'LANGS' in config['DEFAULT']:
                self.m_languages = config['DEFAULT']['LANGS'].split('+')
            if 'CHARSETS' in config['DEFAULT']:
                self.m_charsets = config['DEFAULT']['CHARSETS'].split('+')
            if 'CURRSCHEMA' in config['DEFAULT']:
                self.m_currentSchema = config['DEFAULT']['CURRSCHEMA']
            if 'USERNAME' in config['DEFAULT']:
                self.m_usernameToSave = config['DEFAULT']['USERNAME']
            if 'PASSWD' in config['DEFAULT']:
                self.m_usernameToSave = config['DEFAULT']['PASSWD']
            if 'OGR2OGR_DIR' in config['DEFAULT']:
                self.m_ogr2ogrDir = config['DEFAULT']['OGR2OGR_DIR']
            if 'OGR2OGR_FMTS' in config['DEFAULT']:
                self.m_ogr2ogrFormats = list([tuple([item.strip() for item in rec.split(',')]) for rec in config['DEFAULT']['OGR2OGR_FMTS'].split('+')])
            if 'REPORT_TEMPLATE_DIR' in config['DEFAULT']:
                self.m_reportTemplateDir = config['DEFAULT']['REPORT_TEMPLATE_DIR']
            if 'LAST_EXPORT_DIR' in config['DEFAULT']:
                self.m_lastExportDir = config['DEFAULT']['LAST_EXPORT_DIR']
            if 'GDAL_DATA_DIR' in config['DEFAULT']:
                self.m_gdalDataDir = config['DEFAULT']['GDAL_DATA_DIR']

    def save(self):
        cfg_path = self.configFile()
        print("Saving configuration into '%s'" % cfg_path)

        config = configparser.ConfigParser()
        config['DEFAULT'] = {}
        config['DEFAULT']['RECENT_DBS'] = '+'.join(self.m_recentDatabases)
        config['DEFAULT']['LANGS'] = '+'.join(self.m_languages)
        config['DEFAULT']['CHARSETS'] = '+'.join(self.m_charsets)
        if self.m_currentSchema is not None:
            config['DEFAULT']['CURRSCHEMA'] = self.m_currentSchema
        config['DEFAULT']['USERNAME'] = '+'.join(self.m_usernameToSave)
        config['DEFAULT']['PASSWD'] = '+'.join(self.m_passwdToSave)

        config['DEFAULT']['OGR2OGR_DIR'] = self.m_ogr2ogrDir
        config['DEFAULT']['OGR2OGR_FMTS'] = '+'.join([','.join(rec) for rec in self.m_ogr2ogrFormats])
        config['DEFAULT']['REPORT_TEMPLATE_DIR'] = self.m_reportTemplateDir
        config['DEFAULT']['LAST_EXPORT_DIR'] = self.m_lastExportDir
        config['DEFAULT']['GDAL_DATA_DIR'] = self.m_gdalDataDir

        with open(cfg_path, 'w') as configfile:
            config.write(configfile)

    def configFile(self):
        cfg_path = os.path.join(os.environ['APPDATA'], "SpatMan")
        if not os.path.exists(cfg_path):
            os.makedirs(cfg_path)

        cfg_path = os.path.join(cfg_path, "config")

        return cfg_path

    def addRecentDB(self, db):
        if db in self.m_recentDatabases:
            self.m_recentDatabases.remove(db)
        self.m_recentDatabases.insert(0, db)
        self.save()

    def recentDBs(self):
        return self.m_recentDatabases

    def languages(self):
        return self.m_languages

    def charsets(self):
        return self.m_charsets

    def currentSchema(self):
        return self.m_currentSchema

    def ogr2ogrDir(self):
        return self.m_ogr2ogrDir

    def ogr2ogrFormats(self):
        return self.m_ogr2ogrFormats

    def setCurrentSchema(self, schema):
        self.m_currentSchema = schema
        self.save()

    def setUserNamePass(self, userName, password):
        self.m_usernameToSave = userName
        self.m_passwdToSave = password
        self.save()

    def userNamePass(self):
        return (self.m_usernameToSave, self.m_passwdToSave)

    def gdalDataDir(self):
        return self.m_gdalDataDir

    def setOgr2ogrDir(self, dir):
        self.m_ogr2ogrDir = dir
        self.save()

    def setLastExportDir(self, dir):
        if self.m_lastExportDir != dir:
            self.m_lastExportDir = dir
            self.save()

    def lastExportDir(self):
        return self.m_lastExportDir

    def reportTemplateDir(self):
        return self.m_reportTemplateDir

    def setGdalDataDir(self, dir):
        self.m_gdalDataDir = dir
        self.save()