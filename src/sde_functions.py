import pyodbc
import sys
import pandas as pd
import json
#from arcpy import FromWKT, AsShape, Delete_management, Copy_management
from ui_functions import Debug, Completed, Break, Options, logging
import time
from datetime import datetime
from error import Cancelled, GUIDError
import EsriWktConverter as ewc
#import logging
arcpy = None

def RemoveNulls(dict_in):
    #returns dictionary with only non-null entries
    #dict_in = {k: v for k, v in dict_in.items()}

    return dict_in

def CleanDeltas(dict_in):
    #turn all keys to lower case
    dict_in = {k.lower(): v for k, v in dict_in.items()}

    return dict_in

def LowercaseDataframe(df):
    #converts all column names to lower case
    df.columns = [col.lower() for col in df.columns]

    return df

#gets SQL server and database from .sde file
def GetServerFromSDE(sde_file):
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
            return server, db
        else:
            raise Exception()
    except Exception as e:
        raise Exception("Invalid SDE file")

#connect to sql server
def Connect(server, database, UID, PWD):
    logging.debug('Connecting to SQL Server...')
    connection_string = 'Driver={{SQL Server}};Server={};Database={};User Id={};Password={}'.format(server, database, UID, PWD)
    #logging.debug('SQL Connection string: "{}"\n'.format(connection_string))
    
    try:
        connection = pyodbc.connect(connection_string)    
    except:
        logging.error("Connection error!")#, 0, indent=4)
        logging.error("Connection string: {}".format(connection_string))
        raise

    logging.debug('Connected to SQL!')#, 2, indent=4)
    return connection



#DWB Backup FC
##def BackupFeatureClass(sync_num):
##    import shutil, os
##
##    from datetime import datetime
##    now = datetime.now() # current date and time
##    today = now.strftime("%m_%d_%Y")
##    #print("TIMESTAMP: " + now.strftime("%m_%d_%Y, %H:%M:%S"))
##    #print("Loading arcpy (this may take awhile)...")
##
##    # Ask user for Sync number
##    #SyncID = ui.Options('Enter next SyncID :', menu, allow_filter=True)
##    sync_label = raw_input("Enter optional note to include in name of backup copy: ").strip()
##
##    if len(sync_label) > 0:
##        sync_label = '_{}'.format(sync_label)
##        
##    # Local variables:
##    redw_DBO_VEG_InvasivesCurrent_py_s = "N:\\GIS_Data\\_SDE_Connects\\REDW (generic).sde\\redw.DBO.VEG_InvasivesCurrent_py_s"
##    VEG_InvasivesCurrent_py_s_BU = "N:\\Admin\\Backup\\LSync_Backup\\LSync_Veg.gdb\\VEG_" + str(sync_num) + "_InvasivesCurrent_py_s_" + str(today) + sync_label
##
##    fileout = r'N:\Admin\Backup\LSync_Backup\syncs_ID'+ str(sync_num)+ '_' + str(today) + sync_label + '.json'
##    filein = r'N:\GIS_Projects\236_ARC_LSync\LSync py_s 111221\config\syncs.json'    
##    shutil.copy(filein, fileout)
##    print("Created: " + fileout)
##    # if FC already exists, best to delete it, and if it fail, continue
##    try:
##        Delete_management(VEG_InvasivesCurrent_py_s_BU, "FeatureClass")
##        Debug('Attempting to delete feature class (in case it already exists)'  + '.\n', 0, indent=4)
##        print("")
##    except:
##        Debug('Feature class copy does not currently exist. Ok to crreate.\n', 0, indent=4)    
##
##    # Process:
##    Copy_management(redw_DBO_VEG_InvasivesCurrent_py_s, VEG_InvasivesCurrent_py_s_BU, "FeatureClass")
##    print("Created: " + VEG_InvasivesCurrent_py_s_BU)
##    print("")

#queries sql, logs query, and converts returned dataframe to lowercase
def ReadSQLWithDebug(query, connection):
    logging.debug('Excecuting SQL query: "{}"'.format(query))#, 3)
    try: 
        df = pd.read_sql(query, connection)
    except:
        logging.error('Error excecuting SQL!\nSQL Query:"{}"\n'.format(query))
        raise

    df = LowercaseDataframe(df)
    return df


def BackupFeatureClass(service, sync_num):
    if ('sde_connect' not in service.keys()) or (not service['sde_connect']):
        print("SDE service does not include .sde filepath.")
        while(True):
            sde_connect = raw_input("Enter .sde filepath for this SDE database:")
            try:
                server, db = GetServerFromSDE(sde_connect)
            except:
                print("Invalid filepath!")
                continue
            if not db == service['database']:
                print("Database name does not match this service!")
                continue
            break
        
    
    from datetime import datetime
    ##import shutil, os
    
    now = datetime.now() # current date and time
    today = now.strftime("%m%d%Y")

    if (not arcpy):
        logging.info("Loading arcpy (this may take awhile)...")
        from arcpy import Copy_management, Delete_management

    ##fileout = r'N:\Admin\Backup\LSync_Backup\syncs_ID'+ str(sync_num)+ '_' + str(today) + '.json'
    ##filein = r'config\syncs.json'
    ##shutil.copy(filein, fileout)

    fcName = service['featureclass']
    db = service['database']
    
    backup_name = '{}_BACKUP_{}_{}'.format(fcName, str(sync_num), today)

    fcPath = '{}\\{}.dbo.{}'.format(sde_connect, db, fcName)
    backup_path = '{}\\{}.dbo.{}'.format(sde_connect, db, backup_name)

    logging.debug('Creating backup at: {}'.format(backup_name))

    # if FC already exists, best to delete it, and if it fail, continue
    try:
        Delete_management(backup_path, "FeatureClass")
        logging.debug('Attempting to delete feature class (in case it already exists')
    except:
        logging.debug('Feature class copy does not currently exist. Ok to crreate')    

    # Process:
    Copy_management(fcPath, backup_path, "FeatureClass")
    logging.info("Created: " + backup_path)
    
    #query = 'SELECT * INTO {} FROM {}_evw'.format(backup_name, fcName)

    #cursor = connection.cursor()
    #cursor.execute(query)

    #print(cursor.messages)
    

def GetRowcount(connection):    #gets number of rows affected by most recent query
    cursor = connection.cursor()
    cursor.execute('print @@rowcount')
    try:
        rowcount = cursor.messages[0][1].split('[SQL Server]')[1]
        return rowcount
    except:
        logging.error('Error with GetRowcount!')
        logging.error(cursor.messages)
        return -1

def GetDatatypes(connection, fcName):
    #grabs column datatypes from featureclass

    query = "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{}'".format(fcName)
    response = ReadSQLWithDebug(query, connection)

    #print(response)
    return response

def CheckFeatureclass(connection, fcName):
    #Checks that featureclass has globalids and is registered as versioned, returns versioned view name
    
    logging.debug('Checking "{}"...'.format(fcName))#, 1)
    
    query = "SELECT imv_view_name FROM SDE_table_registry WHERE table_name = '{}'".format(fcName)
    data = ReadSQLWithDebug(query, connection)
    
    if (len(data.index) < 1) or (data['imv_view_name'][0] is None):
        logging.error("'{}' not found in SDE table registry. Check that it has been registered as versioned.\n".format(fcName))#, 1)
        return False

    evwName = data['imv_view_name'][0]
    logging.debug("Versioned view name: {}".format(evwName))

    datatypes = GetDatatypes(connection, fcName)
    datatypes['column_name'] = [val.lower() for val in datatypes['column_name']]
    datatypes['data_type'] = [val.lower() for val in datatypes['data_type']]

    globalid = datatypes.loc[datatypes['column_name'] == 'globalid']
    shape = datatypes.loc[datatypes['column_name'] == 'shape']

    #query = "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{}' AND COLUMN_NAME = 'GLOBALID'".format(fcName)
    #data = ReadSQLWithDebug(query, connection)
    
    if (len(globalid.index) < 1):
        logging.error('Featureclass has no global IDs!')#, 0)
        return False
    elif not (globalid['data_type'].iloc[0] == 'uniqueidentifier'):
        logging.warning('WARNING: GlobalID is not of type "uniqueidentifier!"')

    if (len(shape.index) < 1):
        logging.error('Featureclass has no SHAPE column!')  # , 0)
        return False
    elif not (shape['data_type'].iloc[0] == 'geometry'):
        logging.error('Featureclass SHAPE column is not of type "geometry"!')
        print('Please migrate this featureclass\' storage type to "geometry".')
        return False

    logging.debug('Featureclass is valid.')#, 1, indent=4)
    return evwName

def GetCurrentStateId(connection):
    #returns current state id of DEFAULT version
    logging.debug('Getting current SDE state id...')#, 2)
    
    query = "SELECT state_id FROM SDE_versions WHERE NAME='DEFAULT'" #TODO: allow for other versions?
    response = ReadSQLWithDebug(query, connection)

    try:
        state_id = int(response.iloc[0, 0])
              
    except:
        logging.error('Fatal error! Could not aquire current state id.')
        raise

    logging.debug('SDE state id: {}'.format(state_id))#, 2, indent=4)
              
    return state_id

def NoSRID(): #if SRID cannot be found, user will be asked to decide next step
    logging.warning('Error getting SRID!')
    menu = ['Cancel', 'Default to 26910', 'Enter SRID manually']
    choice = Options('Error getting SRID! How would you like to proceed?', menu)
    if choice == 2:
        logging.warning('Continuing with SRID=26910')
        return 26910
    elif choice == 3:
        while True:
            try:
                value = int(raw_input('Enter SRID: '))
            except ValueError: 
                print('Please enter an integer.')
                continue

            logging.warning('Continuing with SRID={}'.format(value))
            return value
    
    print('Cancelling.')
    return -1

def GetSRID(connection, evwName, fc): #TODO remove fcName, just here to throw error for unchanged functions
    #gets SRID of featureclass

    logging.debug('Getting SRID...')#, 2)


    query = "SELECT TOP 1 SHAPE.STSrid FROM {}".format(evwName)
    response = ReadSQLWithDebug(query, connection)

    try:
        srid = int(response.iloc[0])
    except:
        srid = NoSRID()
    logging.debug('SRID acquired. SRID = {}'.format(srid))#, 2, indent=4)

    return srid

def GetGlobalIds(connection, evwName, fc):  #TODO remove fcName, just here to throw error for unchanged functions
    #returns list of global ids existing in featureclass
    logging.debug('Getting SDE global IDs...')#, 2)

    query = "SELECT GLOBALID FROM {}".format(evwName)
    globalIds = ReadSQLWithDebug(query, connection)

    globalIdsList = globalIds.iloc[:, 0].tolist()

    #Debug(globalIdsList, 3)

    logging.debug("{} global ID's acquired".format(len(globalIdsList)))#, 2, indent=4)

    return globalIdsList

def GetServergen(connection, evwName):
    stateId = GetCurrentStateId(connection)
    globalIds = GetGlobalIds(connection, evwName, evwName)

    return {'stateId': stateId, 'globalIds': globalIds}

def GetChanges(connection, evwName, stateId, fc):  #TODO remove fcName, just here to throw error for unchanged functions
    #returns rows from versioned view with state id > state

    logging.debug('Getting changes from {} since state ID {}'.format(evwName, stateId))#, 2)

    currentStateId = GetCurrentStateId(connection)

    #get rows from adds table since lastState
    query = "SELECT * FROM {} WHERE SDE_STATE_ID > {} AND SDE_STATE_ID <= {}".format(evwName, stateId, currentStateId)
    adds = ReadSQLWithDebug(query, connection)

    if(len(adds.index) > 0 and 'shape' in adds.columns):
        #reaquire SHAPE column as WKT
        query = "SELECT SHAPE.AsTextZM() FROM {} WHERE SDE_STATE_ID > {} AND SDE_STATE_ID <= {}".format(evwName, stateId, currentStateId)
        shape = ReadSQLWithDebug(query, connection)

        
        #replace shape column with text
        adds['shape'] = shape.values
        
    return adds

def WktToEsri(WKT):
    #converts well known binary to esri json
    logging.debug('Converting WKT to Esri Json...')#, 3)
    logging.debug('WKT: {}'.format(WKT))#, 3, indent=4)

    #geom = FromWKT(WKT)
    #esri = geom.JSON

    esri = ewc.WktToEsri(WKT)
    
    logging.debug('Converted Esri Json: {}'.format(json.dumps(esri)))#, 3, indent=4)
    
    return esri

def EsriToWkt(esri):
    #converts esri json to well known text

    logging.debug('Converting Esri Json to WKT...')#, 3)

    try:
        srid = esri['spatialReference']['wkid']
    except:
        srid = NoSRID()
        if srid == -1:
            return -1
    
    logging.debug('Esri Json: {}'.format(json.dumps(esri)))#, 3, indent=4)
     
    #geom = AsShape(jsn, True)
    #wkt = geom.WKT
    #wkt = wkt.replace(' Z ', ' ')   #SQL takes strings in the format "POLYGON (...)" rather than "POLYGON Z (...)". 
   # wkt = wkt.replace(' M ', ' ')

    wkt = ewc.EsriToWkt(esri)

    logging.debug('Converted WKT: {}'.format(wkt))#, 3, indent=4)

    sql = "geometry::STGeomFromText('{}', {})".format(wkt, srid)
    
    return sql

#get columns of datetime datatype (need to be converted)
def GetDatetimeColumns(datatypes):
    datetime_columns = (datatypes[datatypes['data_type'].str.contains('datetime')])['column_name'].tolist()
    datetime_columns = [col.lower() for col in datetime_columns]

    return datetime_columns

#convert SQL datetime string to epoch timestamp
def SqlDatetimeToEpoch(string):
    if string is not None: 
        string = string.split('.')[0]
        utc_time = datetime.strptime(string, "%Y-%m-%d %H:%M:%S")
        return (utc_time - datetime(1970, 1, 1)).total_seconds()*1000
    else:
        return None
    
def SqlToJson(df, datatypes):
    #takes adds or updates dataframe and converts into agol-json-like dictionary
    dict_out = []

    #get columns containing datetime objects
    datetime_columns = GetDatetimeColumns(datatypes)
    
    for i in range(0, len(df.index)):
        attributes = df.iloc[i]
        #attributes['shape'] = [x for x in attributes['shape']]      #compress byte array into integers so it can be converted to json
        attributes = json.loads(attributes.to_json(orient='index'))

        #remove nulls, convert keys to lower case
        attributes = CleanDeltas(attributes)

        #separate out shape
        if ('shape' in attributes.keys()):
            try:
                geometry = WktToEsri(attributes['shape'])
            except:
                logging.error('Error converting object "{}" from WKT to JSON!'.format(attributes['globalid']))
                raise
            del attributes['shape']
        else:
            logging.warning('No shape')

        #convert datetime strings to epoch timestamps
        for k in attributes.keys():
            if k in datetime_columns:
                epoch = SqlDatetimeToEpoch(attributes[k])
                attributes[k] = epoch

        entry = {'geometry': geometry, 'attributes': attributes}
        dict_out.append(entry)

    return dict_out

def JsonToSql(deltas, datatypes):
    logging.debug("Converting json to SQL")
    #takes adds or updates json and turns it into sql-writable format
    dict_out = []

    #get datetime columns (need to be converted to epoch)
    datetime_columns = GetDatetimeColumns(datatypes)
    
    for delta in deltas:
        #turn geometry json into syntax for SQL
        try: 
            SHAPE = EsriToWkt(delta['geometry'])
        except:
            logging.error('Error converting object "{}" from json to WKT!'.format(delta['attributes']['globalid']))
            raise    

        if SHAPE == -1:     
            raise   #TODO: make EsriToWkt raise instead

        #extract attributes
        #attributes = RemoveNulls(delta['attributes'])

        #clean attributes
        for key in attributes.keys():

            #turn Nones and empty objects into NULLs for SQL
            if (attributes[key] in [None, {}]):
                attributes[key] = "NULL"
            
            #convert epoch timestamps to sql string
            elif key.lower() in datetime_columns:
                timestamp = True
                try:
                    epoch = int(attributes[key])
                except:
                    timestamp = False
                if(timestamp):
                    if epoch < 0:
                        epoch = 0
                    attributes[key] = "DATEADD(S, {}, '1970-01-01')".format(epoch/1000)
                else:
                    attributes[key] = "NULL"

                #add quotes to strings, escape apostrophes
            elif (not isinstance(attributes[key], float)) and (not isinstance(attributes[key], int)):
                attributes[key] = str(attributes[key]).replace("'", "''")
                attributes[key] = "'{}'".format(attributes[key])

            #convert everything else to a string for joining later
            else:
                attributes[key] = str(attributes[key])

        #combine attributes and shape into one dict
        attributes.update({'shape': SHAPE})

        dict_out.append(attributes)

    return dict_out

##def WkbToSql(text):
##    SRID = '26910'
##    return 'STGeomFromText({})'.format(text)

def EditTable(query, connection, expectedRowCount):
    cursor = connection.cursor()

    logging.debug('Editing table. SQL Query: "{}"'.format(query))#, 3)
    
    try:     
        cursor.execute(query)
    except:
        logging.error('Error executing SQL!')
        logging.error('{}'.format(cursor.messages))
        logging.error('Executed SQL query: {}'.format(query))
        logging.error('Rolling back SQL edits and exiting.')
        connection.rollback()
        raise
        
    for i in range(0, 100):
        cursor.execute('print @@rowcount')
        rowcount = -1
        
        try:
            rowcount = int(cursor.messages[0][1].split('[SQL Server]')[1])
        except:
            logging.error('Error with GetRowcount.')

        if(rowcount == expectedRowCount or rowcount != -1):
            break

    if (rowcount != expectedRowCount):
        #raise RowcountError('Unexpected number of rows affected')
        logging.error('Unexpected number of rows affected: {}\n Expected: {}\n'.format(cursor.rowcount, expectedRowCount))
        if(raw_input("Press enter to ignore, or type anything to cancel sync") != ''):
           raise Cancelled('Sync cancelled.')

    return rowcount

def Add(connection, evwName, dict_in, fc): #TODO remove fcName, just here to throw error for unchanged functions
    #add a feature to the versioned view of a featureclass
    keys = ','.join(dict_in.keys())
    values = ','.join(dict_in.values())

    try:
        globalId = dict_in['globalid']
    except NameError:
        logging.error('ERROR! Add object has no global ID!\n')
        print(json.dumps(dict_in))
        raise GUIDError('Add object has no global ID!')

    logging.info('Adding object {}'.format(globalId))#, 2, indent=4)
    
    query = "INSERT INTO {} ({}) VALUES ({});".format(evwName, keys, values) #TODO: make SRID variable
    
    return EditTable(query, connection, 1)

def Update(connection, evwName, dict_in, fc):
    #update a feature in the versioned view of a featureclass

    try:
          globalId = dict_in['globalid']
    except NameError:
          logging.error('ERROR! Update object has no global ID!\n')
          print(json.dumps(dict_in))
          raise GUIDError('Update object has no global ID!')
          
    del dict_in['globalid']

    logging.info('Updating object {}'.format(globalId))#, 2, indent=4)

    pairs = []
    
    for k,v in dict_in.items():       
        pairs.append('{}={}'.format(k, v))

    data = ','.join(pairs)

    query = "UPDATE {} SET {} WHERE GLOBALID = {}".format(evwName, data, globalId) #TODO: make SRID variable

    return EditTable(query, connection, 1)
    

def Delete(connection, evwName, GUID, fc):
    #remove feature from versioned view of featureclass

    logging.info("Deleting object '{}'".format(GUID))#, 2, indent=4)
    
    query = "DELETE FROM  {} WHERE GLOBALID = '{}'".format(evwName, GUID)
    
    return EditTable(query, connection, 1)

def ExtractChanges(service, cfg):#connection, fcName, lastGlobalIds, lastState, datatypes):
    #returns object lists for adds and updates, and list of objects deleted
  
    connection = Connect(service['hostname'], service['database'], cfg.SQL_username, cfg.SQL_password)

    fcName = service['featureclass']

    # ensure featureclass is ready to go
    evwName = CheckFeatureclass(connection, fcName)

    if not (connection and evwName):
        raise Exception('Failed to connect to SDE featureclass')
    
    #get featureclass data
    datatypes = GetDatatypes(connection, fcName)   
    srid = GetSRID(connection, evwName, fcName)

    if srid == -1:
        raise Exception('Failed to acquire SRID')
    
    #get data from previous run
    lastGlobalIds = service['servergen']['globalIds']
    lastState = service['servergen']['stateId']
    
    #get global ids and changes from versioned view
    globalIds = GetGlobalIds(connection, evwName, fcName)
    changes = GetChanges(connection, evwName, lastState, fcName)
    
    #extrapolate updates and deletes
    logging.info('Processing changes...')#, 2)

    #missing ids = deletes
    deleteIds = list(set(lastGlobalIds).difference(globalIds))

    #get global ids from changes
    changeGlobalIds = set(changes['globalid'].tolist())

    #new ids = adds
    addIds = list(changeGlobalIds.difference(lastGlobalIds))

    #get rows containing adds
    addRows = changes['globalid'].isin(addIds)

    #split changes into adds and updates
    adds = changes[addRows]
    updates = changes[~addRows]

    adds_json = SqlToJson(adds, datatypes)
    updates_json = SqlToJson(updates, datatypes)

    deltas = {"adds": adds_json, "updates": updates_json, "deleteIds": deleteIds}
    
    data = {'connection': connection, 'datatypes': datatypes, 'evwName': evwName}
    
    logging.info('SDE change extraction complete.')#, 0)
    
    return deltas, data, srid

def AskToCancel(e):     #asks to cancel edits after a failed edit
    print(e.message)
    if(raw_input("Edit failed. Press enter to ignore, or type anything to cancel sync") != ''):
        return True
        
    logging.warning('Continuing although edit failed')
    return False
              
def ApplyEdits(service, cfg, deltas, sync_num, backup, data=None): #connection, fcName, deltas, datatypes):
    #applies deltas to versioned view. Returns success codes and new SDE_STATE_ID

    fcName = service['featureclass']
    
    #get connection data
    if data == None:
        connection = Connect(service['hostname'], service['database'], cfg.SQL_username, cfg.SQL_password)
        evwName = CheckFeatureclass(connection, service['featureclass'])
        if not (connection and evwName):
            return False
        datatypes = GetDatatypes(connection, service['featureclass'])
    else:
        connection = data['connection']
        datatypes = data['datatypes']
        evwName = data['evwName']

    if backup:
        BackupFeatureClass(service, sync_num)

    #get attribute names
    columns = GetDatatypes(connection, fcName)['column_name'].tolist()
    columns = [col.lower() for col in columns]

    #redefine adds and updates based on current data to avoid errors/conflicts
    addsUpdates = deltas["adds"] + deltas["updates"]
    globalIds = GetGlobalIds(connection, evwName, fcName)

    adds = []
    updates = []
    
    for addUpdate in addsUpdates:
        #check for attributes that don't exist in destination
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

    adds = JsonToSql(adds, datatypes)
    updates = JsonToSql(updates, datatypes)

    successfulAdds = 0
    successfulUpdates = 0
    successfulDeletes = 0
    
    for add in adds:
        try: 
            rowcount = Add(connection, evwName, add, fcName)
        except Exception as e:
            if(AskToCancel(e)):
                raise
            rowcount = 0
              
        if rowcount > 0: 
            successfulAdds += rowcount

    for update in updates:
        try: 
            rowcount = Update(connection, evwName, update, evwName)
        except Exception as e:
            if(AskToCancel(e)):
                raise
            rowcount = 0

        if rowcount > 0: 
            successfulUpdates += rowcount

    for GUID in deleteGUIDs:
        try: 
            rowcount = Delete(connection, evwName, GUID, evwName)
        except Exception as e:
            if(AskToCancel(e)):
                raise
            rowcount = 0

        if rowcount > 0: 
            successfulDeletes += rowcount

    if(len(adds) + len(updates) + len(deleteGUIDs) > 0):  #if any edits were attempted
        print('')
        logging.info('SDE apply edit results:')
        Completed('add', len(adds), successfulAdds)
        Completed('update', len(updates), successfulUpdates)
        Completed('delete', len(deleteGUIDs), successfulDeletes)
        print('')
        
        menu = ['Commit changes', 'Cancel changes']
        choice = Options('Changes have not been commited. Commit?', menu)
    
        if choice == 2:
            raise Cancelled('Sync cancelled.')
    
        connection.commit()
        logging.info('Changes committed.')

    #get new state id and global ids
    state_id = GetCurrentStateId(connection)
    globalIds = GetGlobalIds(connection, evwName, fcName)

    #close connection
    connection.close()

    return {'stateId': state_id, 'globalIds': globalIds}


