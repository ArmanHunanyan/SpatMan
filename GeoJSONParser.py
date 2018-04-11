
import json

class GeoJSONVisitor:

    def visitType(self, type):
        pass

    def visitName(self, name):
        pass

    def visitSRID(self, SRID):
        pass

    def beginFeatures(self):
        pass

    def endFeatures(self):
        pass

    def visitGeometry(self, propsDict, geomObj):
        pass

def visitRequiredProp(visitor, jsonDict, propName, errorMsg, funcName = None):
    val = jsonDict.get(propName, None)
    if val is None:
        raise Exception(errorMsg % propName)

    if funcName is None:
        funcName = 'visit' + propName[0].upper() + propName[1:].lower()
    getattr(visitor, funcName)(val)

def visitOptionalProp(visitor, jsonDict, propName, errorMsg, funcName = None):
    val = jsonDict.get(propName, None)
    if val is None:
        return

    if funcName is None:
        funcName = 'visit' + propName[0].upper() + propName[1:].lower()
    getattr(visitor, funcName)(val)

def readRequireProp(jsonDict, propName, errorMsg, expectedValue = None):
    if propName not in jsonDict:
        raise Exception(errorMsg + ": '%s' not found" % propName)
    val = jsonDict.get(propName, None)

    if expectedValue is not None:
        if val != expectedValue:
            raise Exception(errorMsg + ": '%s' should be '%s' but got '%s'" % (propName, expectedValue, val))

    return val

def readOptionalProp(jsonDict, propName, errorMsg, expectedValue = None):
    if propName not in jsonDict:
        return None
    val = jsonDict.get(propName, None)

    if expectedValue is not None:
        if val != expectedValue:
            raise Exception(errorMsg + ": '%s' should be '%s' but got '%s'" % (propName, expectedValue, val))

    return val

class FutureGeometry:
    def __init__(self, type, coordinates):
        self.type = type
        self.coordinates = coordinates

def parseGeoJSONFeature(feature, visitor):
    type = readRequireProp(feature, 'type', "Unexpected 'feature' section")

    if feature['type'] != 'Feature':
        # TODO handle other types
        return

    properties = readRequireProp(feature, 'properties', "Unexpected 'feature' section")

    geometry = readRequireProp(feature, 'geometry', "Unexpected 'feature' section")
    geomObj = FutureGeometry(readRequireProp(geometry, 'type', "Unexpected 'feature geometry' section"),
                             readRequireProp(geometry, 'coordinates', "Unexpected 'feature geometry' section"))

    visitor.visitGeometry(properties, geomObj)

def parseGeoJSON(fileName, visitor):
    file = open(fileName, 'r')
    try:
        data = json.load(file)

        visitRequiredProp(visitor, data, 'type', "'%s' GetJSON file does not contain '%s' property" % (fileName, '%s'))
        visitOptionalProp(visitor, data, 'name', "'%s' GetJSON file does not contain '%s' property" % (fileName, '%s'))

        crs = readOptionalProp(data, 'crs', "Error parsing GeoJSON")
        if crs is None:
            visitor.visitSRID(None)
        else:
            readRequireProp(crs, 'type', "Unexpected 'crs' section", "name")

            crsProps = readRequireProp(crs, 'properties', "Unexpected 'crs' section")
            visitRequiredProp(visitor, crsProps, 'name', "Missing '%s' in 'crs' section: Err3", 'visitSRID')

        features = readRequireProp(data, 'features', "Unexpected GeoJSON file")

        visitor.beginFeatures()
        for feature in features:
            parseGeoJSONFeature(feature, visitor)
        visitor.endFeatures()
    finally:
        file.close()
