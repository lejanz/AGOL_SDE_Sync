#custom errors

class Error(Exception):   #base class for custom errors
    def __init__(self, message):
        self.msg = message
        self.message = message  # lol
        super(Error, self).__init__(message)

    def __str__(self):
        return self.msg

#AGOL

class HTTPError(Error):   #invalid http response
    def __init__(self, message, url, code):
        super(HTTPError, self).__init__('{}\nURL: {}\nError code: {}'.format(message, url, code))

class AGOLError(Error):   #generic AGOL error
    def __init__(self, message, url):
        super(AGOLError, self).__init__('{}\nURL: {}'.format(message, url))    

class AGOLServiceError(AGOLError):    #error returned by AGOL
    def __init__(self, parsedJson, url):
        super(AGOLServiceError, self).__init__(parsedJson['error'], url)

class JSONDecodeError(Error):
    def __init__(self, message):
        super(JSONDecodeError, self).__init__(message)


#SDE

##class SQLReadError(Error):
##    def __init__(self, message, query):
##        super(SQLReadError).__init__('{}\nSQL Query: "{}"'.format(message, query))

class Cancelled(Error):
    def __init__(self, message):
        super(Cancelled, self).__init__(message)

class GUIDError(Error):
    def __init__(self, message, geometry):
        self.geometry = geometry
        super(GUIDError, self).__init__(message)

class RowcountError(Error):
    def __init__(self, message, rowcount, expectedRowCount):
        self.rowcount = rowcount
        super(RowcountError, self).__init__('{}\nRowcount was {}, exptected {}'.format(message, rowcount, expectedRowCount))

class GeometryConversionError(Error):
    def __init__(self, message, query):
        super(GeometryConversionError, self).__init__('{}\nSQL Query: "{}"'.format(message, query))
