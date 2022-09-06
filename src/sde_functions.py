import pyodbc
import sys
import pandas as pd
import json
#from arcpy import FromWKT, AsShape, Delete_management, Copy_management
from src.ui_functions import Completed, Options, logging
import src.ui_functions as ui
import time
from datetime import datetime
from src.error import Cancelled, GUIDError, Error
import src.EsriWktConverter as ewc
from tkinter.filedialog import askopenfilename
from src.misc_functions import CleanJson
#import logging


class sde:
    def __init__(self, cfg, service=None):
        self.cfg = cfg
        self.connection = None
        self.datatypes = None
        self.evwName = None
        self.is_valid = False

        if service is not None:
            if not service['type'] == 'SDE':
                return None

            self.nickname = service['nickname']
            self.hostname = service['hostname']
            self.database = service['database']
            self.fcName = service['featureclass']
            self.servergen = service['servergen']

            try:
                self.sde_connect = service['sde_connect']
            except KeyError:
                self.sde_connect = None

            try:
                self.srid = service['srid']
            except:
                self.srid = None

        else:  # service is none, create new service
            self.servergen = None
            self.nickname = None

            self.sde_connect, self.hostname, self.database = GetSdeFilepath()
            print('')
            self.fcName = ui.GetFcName()
            if not self.fcName:
                raise Cancelled('')

    def ToDict(self):
        service = {'type': 'SDE',
                   'featureclass': self.fcName,
                   'sde_connect': self.sde_connect,
                   'hostname': self.hostname,
                   'database': self.database,
                   'servergen': self.servergen,
                   'nickname': self.nickname}

        return service

    def __str__(self):
        out = ('  Type: SDE\n'
               '  Nickname: {}\n'
               '  SDE connect file: {}\n'
               '  SQL Server: {}\n'
               '  SDE Database: {}\n'
               '  SDE featureclass: {}\n'
               '  SDE state id: {}\n'.format(self.nickname, self.sde_connect,
                                             self.hostname, self.database,
                                             self.fcName, self.servergen['stateId']))

        return out

    # connect to sql server
    def Connect(self):

        if self.connection is not None:
            return

        UID = self.cfg.SQL_username
        PWD = self.cfg.SQL_password

        logging.info('Connecting to SQL Server...')
        connection_string = 'Driver={{SQL Server}};Server={};Database={};User Id={};Password={}'.format(
            self.hostname, self.database, UID, PWD)
        # logging.debug('SQL Connection string: "{}"\n'.format(connection_string))

        try:
            connection = pyodbc.connect(connection_string)
        except:
            logging.error("SQL connection error!")  # , 0, indent=4)
            logging.error("Connection string: {}".format(connection_string))
            raise

        logging.info('Connected to SQL!')  # , 2, indent=4)

        self.connection = connection

    def Disconnect(self):
        self.connection.close()
        self.connection = None

    def Backup(self, sync_num):
        self.Connect()
        if not self.ValidateService():
            return

        logging.info("Loading arcpy (this may take a while)...")
        import arcpy

        if not self.sde_connect:
            out_folder = "sde_connects"
            out_file = "{}_{}.sde".format(self.hostname, self.database)
            self.sde_connect = "{}\\{}".format(out_folder, out_file)

            arcpy.CreateDatabaseConnection_management(out_folder, out_file, 'SQL_SERVER', self.hostname,
                                                      'DATABASE_AUTH', self.cfg.SQL_username, self.cfg.SQL_password,
                                                      'SAVE_USERNAME', self.database)



            # print("SDE service does not include .sde filepath.")
            # while(True):
            #     sde_connect = raw_input("Enter .sde filepath for this SDE database:")
            #     try:
            #         server, db = GetServerFromSDE(sde_connect)
            #     except:
            #         print("Invalid filepath!")
            #         continue
            #     if not db == service['database']:
            #         print("Database name does not match this service!")
            #         continue
            #     break


        from datetime import datetime
        ##import shutil, os

        now = datetime.now()  # current date and time
        today = now.strftime("%m%d%Y")

        ##fileout = r'N:\Admin\Backup\LSync_Backup\syncs_ID'+ str(sync_num)+ '_' + str(today) + '.json'
        ##filein = r'config\syncs.json'
        ##shutil.copy(filein, fileout)

        owner = self.GetOwner()

        backup_name = '{}_BACKUP_{}_{}'.format(self.fcName, str(sync_num), today)

        fcPath = '{}\\{}.{}.{}'.format(self.sde_connect, self.database, owner, self.fcName)
        backup_path = '{}\\{}.{}.{}'.format(self.sde_connect, self.database, owner, backup_name)

        logging.debug('Creating backup at: {}'.format(backup_name))

        # if FC already exists, best to delete it, and if it fail, continue
        try:
            arcpy.Delete_management(backup_path, "FeatureClass")
            logging.debug('Attempting to delete feature class (in case it already exists')
        except:
            logging.debug('Feature class copy does not currently exist. Ok to create')

        # Process:
        arcpy.Copy_management(fcPath, backup_path, "FeatureClass")
        logging.info("Created: " + backup_path)

        #query = 'SELECT * INTO {} FROM {}_evw'.format(backup_name, fcName)

        #cursor = connection.cursor()
        #cursor.execute(query)

        #print(cursor.messages)

    def ValidateService(self):
        #Checks that featureclass has globalids and is registered as versioned, returns versioned view name

        if not self.is_valid:
            logging.info('Validating "{}"...'.format(self.fcName))#, 1)

            self.Connect()

            query = "SELECT imv_view_name FROM SDE_table_registry WHERE table_name = '{}'".format(self.fcName)
            data = self.ReadSQLWithDebug(query)

            if (len(data.index) < 1) or (data['imv_view_name'][0] is None):
                logging.error("'{}' not found in SDE table registry. Check that it has been registered as versioned.\n".format(self.fcName))#, 1)
                return False

            evwName = data['imv_view_name'][0]
            logging.debug("Versioned view name: {}".format(evwName))

            datatypes = self.GetDatatypes()
            datatypes['column_name'] = [val.lower() for val in datatypes['column_name']]
            datatypes['data_type'] = [val.lower() for val in datatypes['data_type']]

            globalid = datatypes.loc[datatypes['column_name'] == 'globalid']
            shape = datatypes.loc[datatypes['column_name'] == 'shape']

            #query = "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{}' AND COLUMN_NAME = 'GLOBALID'".format(fcName)
            #data = ReadSQLWithDebug(query, connection)

            if (len(globalid.index) < 1):
                logging.error('Featureclass has no global IDs!')#, 0)
                self.is_valid = False
                return False
            elif not (globalid['data_type'].iloc[0] == 'uniqueidentifier'):
                logging.warning('WARNING: GlobalID is not of type "uniqueidentifier!"')

            if (len(shape.index) < 1):
                logging.error('Featureclass has no SHAPE column!')  # , 0)
                self.is_valid = False
                return False
            elif not (shape['data_type'].iloc[0] == 'geometry'):
                logging.error('Featureclass SHAPE column is not of type "geometry"!')
                print('Please migrate this featureclass\' storage type to "geometry".')
                self.is_valid = False
                return False

            logging.info('Featureclass is valid.')#, 1, indent=4)
            self.evwName = evwName
            self.is_valid = True

        return self.GetServergen()

    def GetServergen(self):
        stateId = self.GetCurrentStateId()
        globalIds = self.GetGlobalIds()

        return {'stateId': stateId, 'globalIds': globalIds}

    def UpdateServergen(self, servergen=None):
        if not servergen:
            servergen = self.GetServergen()

        self.servergen = servergen

    def ExtractChanges(self):
        #returns object lists for adds and updates, and list of objects deleted

        self.Connect()

        # ensure featureclass is ready to go
        # now done in sync.run()
        #if not self.ValidateService():
        #    raise Exception('Failed to validate featureclass')

        # get featureclass data
        self.datatypes = self.GetDatatypes()
        srid = self.GetSRID()

        if srid == -1:
            raise Exception('Failed to acquire SRID')

        # get data from previous run
        lastGlobalIds = self.servergen['globalIds']
        #lastState = self.servergen['stateId']

        # get global ids and changes from versioned view
        globalIds = self.GetGlobalIds()
        changes = self.GetChanges()

        # extrapolate updates and deletes
        logging.info('Processing changes...')#, 2)

        # missing ids = deletes
        deleteIds = list(set(lastGlobalIds).difference(globalIds))

        # get global ids from changes
        changeGlobalIds = set(changes['globalid'].tolist())

        # new ids = adds
        addIds = list(changeGlobalIds.difference(lastGlobalIds))

        # get rows containing adds
        addRows = changes['globalid'].isin(addIds)

        # split changes into adds and updates
        adds = changes[addRows]
        updates = changes[~addRows]

        adds_json = SqlToJson(adds, self.datatypes)
        updates_json = SqlToJson(updates, self.datatypes)

        deltas = {"adds": adds_json, "updates": updates_json, "deleteIds": deleteIds}

        CleanJson(deltas, srid)

        logging.info('SDE change extraction complete.')#, 0)

        return deltas

    def ApplyEdits(self, deltas): # connection, fcName, deltas, datatypes):
        # applies deltas to versioned view. Returns success codes and new SDE_STATE_ID

        # get connection data
        if self.connection is None:
            self.Connect()
            if not self.ValidateService():
                return False
            self.GetDatatypes()

        # if backup:
        #    BackupFeatureClass(service, sync_num, connection, cfg)

        # get attribute names
        columns = self.datatypes['column_name'].tolist()
        columns = [col.lower() for col in columns]

        # redefine adds and updates based on current data to avoid errors/conflicts
        addsUpdates = deltas["adds"] + deltas["updates"]
        globalIds = self.GetGlobalIds()

        adds = []
        updates = []

        for addUpdate in addsUpdates:
            # check for attributes that don't exist in destination
            keys = addUpdate['attributes'].keys()
            extra_keys = set(keys) - set(columns)
            if len(extra_keys) > 0:
                logging.error('Error! The following attribute fields do not exist in the destination:')
                logging.error(','.join(extra_keys))
                logging.error('Cancelling changes.')
                return False

            if addUpdate['attributes']['globalid'] in globalIds:
                updates.append(addUpdate)
            else:
                adds.append(addUpdate)

        deleteGUIDs = [delete.replace('{', '').replace('}', '') for delete in deltas["deleteIds"]]

        adds = JsonToSql(adds, self.datatypes)
        updates = JsonToSql(updates, self.datatypes)

        successfulAdds = 0
        successfulUpdates = 0
        successfulDeletes = 0

        for add in adds:
            try:
                rowcount = self.Add(add)
            except Exception as e:
                if(AskToCancel(e)):
                    raise
                rowcount = 0

            if rowcount > 0:
                successfulAdds += rowcount

        for update in updates:
            try:
                rowcount = self.Update(update)
            except Exception as e:
                if(AskToCancel(e)):
                    raise
                rowcount = 0

            if rowcount > 0:
                successfulUpdates += rowcount

        for GUID in deleteGUIDs:
            try:
                rowcount = self.Delete(GUID)
            except Exception as e:
                if(AskToCancel(e)):
                    raise
                rowcount = 0

            if rowcount > 0:
                successfulDeletes += rowcount

        if(len(adds) + len(updates) + len(deleteGUIDs) > 0):  # if any edits were attempted
            print('')
            logging.info('SDE apply edit results:')
            Completed('add', len(adds), successfulAdds)
            Completed('update', len(updates), successfulUpdates)
            Completed('delete', len(deleteGUIDs), successfulDeletes)
            print('')

            menu = ['Commit changes', 'Cancel changes']
            choice = Options('Changes have not been committed. Commit?', menu)

            if choice == 2:
                raise Cancelled('Sync cancelled.')

            self.connection.commit()
            logging.info('Changes committed.')

        servergen = self.GetServergen()

        #close connection
        self.Disconnect()

        return servergen

    #gets SQL server and database from .sde file
    def GetServerFromSDE(self):
        sde_file = self.sde_connect

        f = open(sde_file, "rb")
        server = f.read()
        #print(server)
        try:
            if('\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1\x00' in server):
                server = server.replace('\n', '')
                db = server.split('D\x00A\x00T\x00A\x00B\x00A\x00S\x00E')[1].split('\x08\x00')[1].split('\x00\x00')[1]
                db = db.replace('\x00', '')
                server = server.split('s\x00q\x00l\x00s\x00e\x00r\x00v\x00e\x00r\x00:')[1].split('\x00\x00')[0]
                server = server.replace('\x00', '')
            else:
                raise Exception()
        except Exception as e:
            raise Exception("Invalid SDE file")

        self.database = db
        self.hostname = server

    #queries sql, logs query, and converts returned dataframe to lowercase
    def ReadSQLWithDebug(self, query):
        logging.debug('Executing SQL query: "{}"'.format(query))#, 3)
        try:
            df = pd.read_sql(query, self.connection)
        except:
            logging.error('Error excecuting SQL!\nSQL Query:"{}"'.format(query))
            raise

        df = LowercaseDataframe(df)
        return df


    def GetOwner(self):
        query = "SELECT owner FROM sde_table_registry WHERE table_name='{}'".format(self.fcName)
        df = self.ReadSQLWithDebug(query)
        owner = df['owner'].iloc[0]
        return owner

    def GetRowcount(self):    #gets number of rows affected by most recent query
        cursor = self.connection.cursor()
        cursor.execute('print @@rowcount')
        try:
            rowcount = cursor.messages[0][1].split('[SQL Server]')[1]
            return rowcount
        except:
            logging.error('Error with GetRowcount!')
            logging.error(cursor.messages)
            return -1


    def GetDatatypes(self):
        #grabs column datatypes from featureclass

        query = "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{}'".format(self.fcName)
        response = self.ReadSQLWithDebug(query)

        #print(response)
        self.datatypes = response
        return response

    def GetCurrentStateId(self):
        #returns current state id of DEFAULT version
        logging.debug('Getting current SDE state id...')#, 2)

        query = "SELECT state_id FROM SDE_versions WHERE NAME='DEFAULT'" #TODO: allow for other versions?
        response = self.ReadSQLWithDebug(query)

        try:
            state_id = int(response.iloc[0, 0])

        except:
            logging.error('Fatal error! Could not aquire current state id.')
            raise

        logging.debug('SDE state id: {}'.format(state_id))#, 2, indent=4)

        return state_id


    def GetSRID(self):
        # gets SRID of featureclass

        logging.debug('Getting SRID...')#, 2)


        query = "SELECT TOP 1 SHAPE.STSrid FROM {}".format(self.evwName)
        response = self.ReadSQLWithDebug(query)

        try:
            srid = int(response.iloc[0])
        except:
            srid = NoSRID()
        logging.debug('SRID acquired. SRID = {}'.format(srid))

        return srid


    def GetGlobalIds(self):
        # returns list of global ids existing in featureclass
        logging.debug('Getting SDE global IDs...')

        query = "SELECT GLOBALID FROM {}".format(self.evwName)
        globalIds = self.ReadSQLWithDebug(query)
        globalIdsList = globalIds.iloc[:, 0].tolist()

        logging.debug("{} global ID's acquired".format(len(globalIdsList)))

        return globalIdsList

    def GetChanges(self, stateId=None):
        # returns rows from versioned view with state id > state
        if not stateId:
            stateId = self.servergen['stateId']

        logging.debug('Getting changes from {} since state ID {}'.format(self.evwName, stateId))

        currentStateId = self.GetCurrentStateId()

        # get rows from adds table since lastState
        query = "SELECT * FROM {} WHERE SDE_STATE_ID >= {} AND SDE_STATE_ID <= {}".format(self.evwName, stateId, currentStateId)
        adds = self.ReadSQLWithDebug(query)

        if(len(adds.index) > 0 and 'shape' in adds.columns):
            # reaquire SHAPE column as WKT
            query = "SELECT SHAPE.AsTextZM() FROM {} WHERE SDE_STATE_ID >= {} AND SDE_STATE_ID <= {}".format(self.evwName, stateId, currentStateId)
            shape = self.ReadSQLWithDebug(query)

            # replace shape column with text
            adds['shape'] = shape.values

        return adds


    def EditTable(self, query, expectedRowCount):
        cursor = self.connection.cursor()

        logging.debug('Editing table. SQL Query: "{}"'.format(query))

        try:
            cursor.execute(query)
        except Exception as e:
            logging.error('Error executing SQL!')
            logging.error('Executed SQL query: {}'.format(query))
            logging.error('SQL Error message: {}'.format(str(e)))
            logging.error('Rolling back SQL edits and exiting.')
            self.connection.rollback()
            raise
        
        messages = cursor.messages

        for i in range(0, 100):
            cursor.execute('print @@rowcount')
            rowcount = -1

            try:
                rowcount = int(cursor.messages[0][1].split('[SQL Server]')[1])
            except Exception as e:
                logging.error('Error with GetRowcount: {}'.format(str(e)))
                break

            if (rowcount == expectedRowCount) or (rowcount != -1):
                break

        if rowcount != expectedRowCount:
            logging.debug(messages)
            raise Error('Unexpected number of rows affected: {}; Expected: {}'.format(rowcount, expectedRowCount))

        return rowcount

    def Add(self, dict_in):
        # add a feature to the versioned view of a featureclass
        keys = ','.join(dict_in.keys())
        values = ','.join(dict_in.values())

        try:
            globalId = dict_in['globalid']
        except NameError:
            logging.error('ERROR! Add object has no global ID!')
            print(json.dumps(dict_in))
            raise GUIDError('Add object has no global ID!')

        logging.info('Adding object {}'.format(globalId))

        query = "INSERT INTO {} ({}) VALUES ({});".format(self.evwName, keys, values)

        return self.EditTable(query, 1)

    def Update(self, dict_in):
        # update a feature in the versioned view of a featureclass

        try:
              globalId = dict_in['globalid']
        except NameError:
              logging.error('ERROR! Update object has no global ID!')
              print(json.dumps(dict_in))
              raise GUIDError('Update object has no global ID!')

        del dict_in['globalid']

        logging.info('Updating object {}'.format(globalId))

        pairs = []

        for k,v in dict_in.items():
            pairs.append('{}={}'.format(k, v))

        data = ','.join(pairs)

        query = "UPDATE {} SET {} WHERE GLOBALID = {}".format(self.evwName, data, globalId)

        return self.EditTable(query, 1)

    def Delete(self, GUID):
        # remove feature from versioned view of featureclass

        logging.info("Deleting object '{}'".format(GUID))

        query = "DELETE FROM  {} WHERE GLOBALID = '{}'".format(self.evwName, GUID)

        return self.EditTable(query, 1)


def RemoveNulls(dict_in):
    # returns dictionary with only non-null entries
    # dict_in = {k: v for k, v in dict_in.items()}

    return dict_in


def CleanDeltas(dict_in):
    # turn all keys to lower case
    dict_in = {k.lower(): v for k, v in dict_in.items()}

    return dict_in


def LowercaseDataframe(df):
    #converts all column names to lower case
    df.columns = [col.lower() for col in df.columns]

    return df


def NoSRID():  # if SRID cannot be found, user will be asked to decide next step
    logging.warning('Error getting SRID!')
    menu = ['Cancel', 'Default to 26910', 'Enter SRID manually']
    choice = Options('Error getting SRID! How would you like to proceed?', menu)
    if choice == 2:
        logging.warning('Continuing with SRID=26910')
        return 26910
    elif choice == 3:
        while True:
            try:
                value = int(input('Enter SRID: '))
            except ValueError:
                print('Please enter an integer.')
                continue

            logging.warning('Continuing with SRID={}'.format(value))
            return value

    print('Cancelling.')
    return -1


def GetSdeFilepath():
    print('Selecting .sde file...')

    sde_connect = askopenfilename(initialdir="N:\\GIS_Data\\_SDE_Connects", title="Select .sde connect file",
                                  filetypes=(("SDE Files", "*.sde"), ("all files", "*.*")))

    try:
        hostname, database = sde.GetServerFromSDE(sde_connect)
    except Exception as e:
        print("Unable to open .sde file")
        hostname = input('Enter SDE hostname (i.e. inpredwgis2):')
        database = input('Enter SDE database name (i.e. redw):')
        return None, hostname, database

    logging.info("Chose '{}'".format(sde_connect))

    return sde_connect, hostname, database


def EsriToWkt(esri):
    # converts esri json to well known text

    logging.debug('Converting Esri Json to WKT...')  # , 3)

    try:
        srid = esri['spatialReference']['wkid']
    except:
        srid = NoSRID()
        if srid == -1:
            return -1

    logging.debug('Esri Json: {}'.format(json.dumps(esri)))  # , 3, indent=4)

    # geom = AsShape(jsn, True)
    # wkt = geom.WKT
    # wkt = wkt.replace(' Z ', ' ')   #SQL takes strings in the format "POLYGON (...)" rather than "POLYGON Z (...)".
    # wkt = wkt.replace(' M ', ' ')

    wkt = ewc.EsriToWkt(esri)

    logging.debug('Converted WKT: {}'.format(wkt))  # , 3, indent=4)

    sql = "geometry::STGeomFromText('{}', {})".format(wkt, srid)

    return sql


def WktToEsri(WKT):
    # converts well known binary to esri json
    logging.debug('Converting WKT to Esri Json...')  # , 3)
    logging.debug('WKT: {}'.format(WKT))  # , 3, indent=4)

    # geom = FromWKT(WKT)
    # esri = geom.JSON

    esri = ewc.WktToEsri(WKT)

    logging.debug('Converted Esri Json: {}'.format(json.dumps(esri)))  # , 3, indent=4)

    return esri


def GetDatetimeColumns(datatypes):
    # get columns of datetime datatype (need to be converted)
    datetime_columns = (datatypes[datatypes['data_type'].str.contains('datetime')])['column_name'].tolist()
    datetime_columns = [col.lower() for col in datetime_columns]

    return datetime_columns


def SqlDatetimeToEpoch(string):
    # convert SQL datetime string to epoch timestamp
    if string is not None:
        string = string.split('.')[0]
        utc_time = datetime.strptime(string, "%Y-%m-%d %H:%M:%S")
        return (utc_time - datetime(1970, 1, 1)).total_seconds() * 1000
    else:
        return None


def SqlToJson(df, datatypes):
    # takes adds or updates dataframe and converts into agol-json-like dictionary
    dict_out = []

    # get columns containing datetime objects
    datetime_columns = GetDatetimeColumns(datatypes)

    for i in range(0, len(df.index)):
        attributes = df.iloc[i]
        attributes = json.loads(attributes.to_json(orient='index'))
        attributes = CleanDeltas(attributes)  # remove nulls, convert keys to lower case

        # separate out shape
        if ('shape' in attributes.keys()):
            try:
                geometry = WktToEsri(attributes['shape'])
            except:
                logging.error('Error converting object "{}" from WKT to JSON!'.format(attributes['globalid']))
                raise
            del attributes['shape']
        else:
            logging.warning('No shape')

        # convert datetime strings to epoch timestamps
        for k in attributes.keys():
            if k in datetime_columns:
                epoch = SqlDatetimeToEpoch(attributes[k])
                attributes[k] = epoch

        entry = {'geometry': geometry, 'attributes': attributes}
        dict_out.append(entry)

    return dict_out


def JsonToSql(deltas, datatypes):
    logging.debug("Converting json to SQL")
    # takes adds or updates json and turns it into sql-writable format
    dict_out = []

    # get datetime columns (need to be converted to epoch)
    datetime_columns = GetDatetimeColumns(datatypes)

    for delta in deltas:
        # turn geometry json into syntax for SQL
        try:
            SHAPE = EsriToWkt(delta['geometry'])
        except:
            logging.error('Error converting object "{}" from json to WKT!'.format(delta['attributes']['globalid']))
            raise

        if SHAPE == -1:
            raise  # TODO: make EsriToWkt raise instead

        # extract attributes
        attributes = delta['attributes']

        # clean attributes
        for key in attributes.keys():

            # turn Nones and empty objects into NULLs for SQL
            if (attributes[key] in [None, {}]):
                attributes[key] = "NULL"

            # convert epoch timestamps to sql string
            elif key.lower() in datetime_columns:
                timestamp = True
                try:
                    epoch = int(attributes[key])
                except:
                    timestamp = False
                if (timestamp):
                    if epoch < 0:
                        epoch = 0
                    attributes[key] = "DATEADD(S, {}, '1970-01-01')".format(epoch / 1000)
                else:
                    attributes[key] = "NULL"

                # add quotes to strings, escape apostrophes
            elif (not isinstance(attributes[key], float)) and (not isinstance(attributes[key], int)):
                attributes[key] = str(attributes[key]).replace("'", "''")
                attributes[key] = "'{}'".format(attributes[key])

            # convert everything else to a string for joining later
            else:
                attributes[key] = str(attributes[key])

        # combine attributes and shape into one dict
        attributes.update({'shape': SHAPE})

        dict_out.append(attributes)

    return dict_out

def AskToCancel(e):  # asks to cancel edits after a failed edit
    logging.error(str(e))
    if (input("Edit failed. Press enter to ignore, or type anything to cancel sync:") != ''):
        return True

    logging.warning('Continuing although edit failed')
    return False
