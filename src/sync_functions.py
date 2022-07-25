from . import ui_functions as ui
import json
from error import HTTPError, AGOLServiceError, AGOLError, JSONDecodeError, Error
from  Tkinter import *
import tkFileDialog

logging = ui.logging

sde = None
agol = None

#load syncs.json
def LoadSyncs():
    #loads json file containing set up syncs
    logging.debug('Loading syncs...')#, 2)
    
    try:
        syncs_file = open('config/syncs.json', 'r')
    except:
        logging.warning('No syncs.json file found!')
        return []

    try:
        syncs = json.load(syncs_file)
    except:
        logging.error('Invalid sync file!')
        syncs_file.close()
        return []

    syncs_file.close()
    logging.debug('Syncs loaded.')#, 2, indent=4)
    return syncs

#write syncs.json
def WriteSyncs(syncs):
    #writes sync.json with data in syncs
    logging.debug('Updating syncs.json...')#, 2)
    
    try:
        json.dumps(syncs)
    except:
        logging.error("Invalid syncs!")
        return
    
    syncs_file = open('config/syncs.json', 'w')
    json.dump(syncs, syncs_file, indent=4)
    syncs_file.close()

    logging.debug('syncs.json updated.')#, 2, indent=4)

#import SDE functions
def ImportSDE():
    global sde
    if sde == None:
        logging.debug('Loading SDE functions...')#, 2)
        from src import sde_functions as sde
        logging.debug('SDE functions loaded.')#, 2, indent=4)

#import AGOL functions
def ImportAGOL():
    global agol
    if agol == None:
        logging.debug('Loading AGOL functions...')#, 2)
        from src import agol_functions as agol
        logging.debug('AGOL functions loaded.')#, 2, indent=4)

def GetSdeFilepath():
    print('Selecting .sde file...')

    sde_connect = tkFileDialog.askopenfilename(initialdir="N:\GIS_Data\_SDE_Connects", title="Select .sde connect file", filetypes=(("SDE Files", "*.sde"),("all files","*.*")))

    try:
        hostname, database = sde.GetServerFromSDE(sde_connect)
    except Exception as e:
        print("Unable to open .sde file")
        hostname = raw_input('Enter SDE hostname (i.e. inpredwgis2):')
        database = raw_input('Enter SDE database name (i.e. redw):')
        return None, hostname, database

    logging.info("Chose '{}'".format(sde_connect))

    return sde_connect, hostname, database

def ValidateService(service, cfg):
    #checks that service is valid, returns serverGen if so
    if service['type'] == 'SDE':
        ImportSDE()

        # check that featureclass exists in sde table registry
        print('Validating SDE featureclass...')

        hostname = service['hostname']
        database = service['database']
        fcName = service['featureclass']

        connection = sde.Connect(hostname, database, cfg.SQL_username, cfg.SQL_password)

        if not connection:
            return False

        evwName = sde.CheckFeatureclass(connection, fcName)

        if (evwName):
            # get current information
            serverGen = sde.GetServergen(connection, evwName)

            logging.info('Featureclass valid!')  # , 1)
        else:
            logging.error('Featureclass validation failed.')
            return False

        return serverGen

    elif service['type'] == 'AGOL':
        ImportAGOL()

        # check that service is set up correctly
        token = agol.GetToken(cfg.AGOL_url, cfg.AGOL_username, cfg.AGOL_password)

        url = service['serviceUrl']
        layerId = service['layerId']

        print('Validating AGOL service...')

        try:
            ready, serverGen, srid = agol.CheckService(url, layerId, token)
        except (HTTPError, AGOLServiceError, AGOLError, JSONDecodeError, Error) as e:
            logging.error('Error checking AGOL service!')
            logging.error(e.message)
            return False

        logging.info('Feature service layer valid!')

        return serverGen

def CreateNewService(cfg, pc):
    types = ['SDE', 'AGOL', 'Back']
    parent_child = ['parent', 'child']

    serviceType = ui.Options('Enter where your {} dataset is stored:'.format(parent_child[pc]), types)
    SDE = 1
    AGOL = 2
    BACK = 3

    if (serviceType == BACK):  # go back to start of this funtion
        return 'loop'

    elif (serviceType == SDE):
        # for SDE services
        ImportSDE()

        sde_connect, hostname, database = GetSdeFilepath()

        print('')

        fcName = ui.GetFcName()
        if not fcName:
            return False

        service = {'type': 'SDE',
                   'featureclass': fcName,
                   'sde_connect': sde_connect,
                   'hostname': hostname,
                   'database': database}

    elif serviceType == AGOL:
        # for AGOL services
        ImportAGOL()

        # get service details

        print('The URL for a AGOL hosted-feature-layer sublayer can be found at nps.maps.arcgis.com.\n'
              'Browse to the hosted feature layer (the URL to the service will end with "FeatureServer").\n'
              'Then click on one of the layers on the main page. At the bottom right, the URL for the\n'
              'sub layer will be displayed. The hosted-feature-layer sublayer URL in the lower right\n'
              'will end with "Feature Server/x, where x is the sub layer ID. A list of URLs for common\n'
              'layers can befound at "https://tinyurl.com/48kj9ccf".\n')

        url, layerId = ui.GetAgolURL()

        if not url:
            return False

        # layerId = raw_input('\nA feature layer consists of one or more SERVICE LAYERS. The first service layer is layer 0.\n'
        #                        'Enter the SERVICE LAYER ID (usually 0). System will verify the service layer:')

        # try:
        #    layerId = int(layerId)
        # except:
        #    print('Please enter a number for the layer id!')
        #    continue

        service = {'type': 'AGOL',
                   'serviceUrl': url,
                   'layerId': layerId}

        # endif
    print('')
    serverGen = ValidateService(service, cfg)

    if (serverGen):
        print('')
        nickname = ui.GetNickname()

        service['servergen'] = serverGen
        service['nickname'] = nickname

        return service

    else:
        # invalid service
        return False

def CreateNewSync(cfg):
    #UI to create a new sync
    logging.debug('Creating sync...')

    print('A SYNC consists of metadata about two datasets that are kept identical (synchronized)\n'
          'by applying updates, inserts, and deletions from one to the other, and visa versa. The\n'
          'datasets can be a feature layer in a AGOL feature service, or a feature class in a SDE\n'
          'enterprise geodatabase. The SYNC name should generally be the same as the SDE feature\n'
          'class it is based on., and parenthesis can be used to help identify the type of service\n'
          'and location. For example: "(SDE/GIS2-SDE/GIS1)" indicates the parent dataset is located\n'
          'in a SDE geodatabase on server GIS2, and the child is located on server GIS1 in SDE.\n')

    print('Ensure that the two datasets are identical. This tool may not function correctly otherwise.\n')

    name = ui.GetName()

    numbers = ['first', 'second']

    sync = {'name': name, 'first': {}, 'second': {}}
    
    i = 0

    while(i < 2):
        print('')
        service = CreateNewService(cfg, i)
        if service:
            if service == 'loop':
                return service

            sync[numbers[i]] = service
            i = i + 1
        else:
            #failed to create service
            continue

    return sync

def ReregisterSync(sync, cfg):
    for first_second in ['first', 'second']:
        service = sync[first_second]
        serverGen = ValidateService(service, cfg)
        if(serverGen):
            sync[first_second]['servergen'] = serverGen
            logging.info('Servergen updated!')

    return sync

def EditSync(sync, cfg):
    logging.info('Editing sync "{}"...'.format(sync['name']))
    ui.PrintSyncDetails(sync)

    while(True):
        menu = ['SAVE changes', 'DISCARD changes', 'Name', 'Parent dataset ("{}")'.format(sync['first']['nickname']), 'Child dataset ("{}")'.format(sync['second']['nickname'])]
        DONE = 1
        CANCEL = 2
        NAME = 3
        PARENT_DATASET = 4
        CHILD_DATASET = 5

        choice = ui.Options('Choose an option to edit:', menu)

        if(choice == NAME):
            print('Current name: "{}"'.format(sync['name']))
            sync['name'] = ui.GetName()
            print('')

        elif(choice == DONE):
            menu = ['Re-register SYNC', 'DO NOT re-register', 'BACK']
            choice = ui.Options('Would you like to re-register this sync?', menu)
            if(choice == 1):
                sync = ReregisterSync(sync, cfg)
            elif(choice == 3):
                continue

            ui.PrintSyncDetails(sync)
            return sync

        elif(choice == CANCEL):
            menu = ['DISCARD changes', 'BACK']
            choice = ui.Options('Are you sure you want to discard your edits?', menu)
            if(choice == 1):
                return False

        else:
            if(choice == PARENT_DATASET):
                first_second = 'first'
                i = 0
            elif(choice == CHILD_DATASET):
                first_second = 'second'
                i = 1

            service = sync[first_second]
            while True:

                DONE = 1
                TYPE = 2
                NICKNAME = 3

                if(service['type'] == 'AGOL'):
                    ImportAGOL()

                    menu = ['DONE', 'Type', 'Nickname', 'URL']
                    URL = 4


                    choice = ui.Options('What would you like to edit in "{}"'.format(service['nickname']), menu)

                    if(choice == URL):
                        print('Current layer URL: {}/{}'.format(service['serviceUrl'], service['layerId']))
                        url, layerId = ui.GetAgolURL()
                        if not url:
                            continue
                        service['serviceUrl'] = url
                        service['layerId'] = layerId
                        print('')

                elif(service['type'] == 'SDE'):
                    ImportSDE()

                    menu = ['DONE', 'Type', 'Nickname', 'SDE Connection', 'Featureclass']
                    SDE_CONNECT = 4
                    FEATURECLASS = 5

                    choice = ui.Options('What would you like to edit in "{}"'.format(service['nickname']), menu)

                    if(choice == SDE_CONNECT):
                        print('Current .sde file: {}'.format(service['sde_connect']))
                        sde_connect, hostname, database = GetSdeFilepath()
                        service['sde_connect'] = sde_connect
                        service['hostname'] = hostname
                        service['database'] = database

                        print('')

                    elif(choice == FEATURECLASS):
                        print('Current featureclass: {}'.format(service['featureclass']))
                        fcName = ui.GetFcName()
                        if fcName:
                            service['featureclass'] = fcName

                        print('')


                if (choice == TYPE):
                    #create a whole new service
                    service = CreateNewService(cfg, i)
                    print('')
                    if (service == False):
                        continue
                    elif (service == 'loop'):
                        break

                elif (choice == NICKNAME):
                    print('Current nickname: {}'.format(service['nickname']))
                    nickname = ui.GetNickname()
                    service['nickname'] = nickname
                    print('')

                elif (choice == DONE):
                    if(ValidateService(service, cfg)):
                        sync[first_second] = service
                        print('')
                        break

def CleanAttributes(dict_in):
    #turns all keys to lower case, removes unwanted attributes
    dict_in = {k.lower(): v for k, v in dict_in.items()}

    remove_keys = ['sde_state_id', 'objectid']
    dict_in = {k: v for k, v in dict_in.items() if k not in remove_keys}

    return dict_in
    
def CleanDelta(dict_in, srid):
    #cleans attributes and adds srid to geometry
    dict_in['attributes'] = CleanAttributes(dict_in['attributes'])
    dict_in['geometry']['spatialReference'] = {'wkid': srid}

    return dict_in

def ExtractChanges(service, cfg):
    #wrapper for SQL/AGOL extract changes functions

    #ui.Break()
    logging.info('Extracting changes from {}...'.format(service['nickname']))#, 1)
             
    if(service['type'] == 'SDE'):
        ImportSDE()
        
        deltas, data, srid = sde.ExtractChanges(service, cfg)
    
    elif(service['type'] == 'AGOL'):
        ImportAGOL()
        
        deltas, data, srid = agol.ExtractChanges(service, cfg)

    for (index, add) in enumerate(deltas['adds']):
        deltas['adds'][index] = CleanDelta(add, srid)

    for (index, update) in enumerate(deltas['updates']):
        deltas['updates'][index] = CleanDelta(update, srid)

    return deltas, data

def ApplyEdits(service, cfg, deltas, sync_num, data=None):
    #wrapper for SQL/AGOL extract changes functions

    #ui.Break()

    if (len(deltas['adds']) + len(deltas['updates']) + len(deltas['deleteIds'])) < 1:
        logging.info('No edits to apply to {}.'.format(service['nickname']))#, 1)
        backup = False
        
    else:
        logging.info('Applying edits to {}...'.format(service['nickname']))#, 1)

        #ask to create backup first
        options = ['Yes', 'No']
        choice = ui.Options('Would you like to make a backup of {} before continuing?'.format(service['nickname']), options)

        backup = (choice == 1)
        
    if(service['type'] == 'SDE'):
        ImportSDE()
        
        return sde.ApplyEdits(service, cfg, deltas, sync_num, backup, data=data)

    elif(service['type'] == 'AGOL'):
        ImportAGOL()

        return agol.ApplyEdits(service, cfg, deltas, sync_num, backup, data=data)

def GetGlobalIds(dict_in):
    #pulls global ids from adds or updates dictionary, returns as set
    return {add['attributes']['globalid'] for add in dict_in}

def ResolveConflicts(FIRST_deltas, SECOND_deltas, first_name, second_name):
    #Finds all conflicting edits. Resolves conflicts by user input. Returns revised SECOND_deltas and FIRST_deltas

    #ui.Break()
    logging.info('Checking for conflicts...')
    #From here on, we will work only with global ids

    SECOND_updated = GetGlobalIds(SECOND_deltas['updates'])
    FIRST_updated = GetGlobalIds(FIRST_deltas['updates'])
    
    #remove deletes that have already occured in destination, and store as a set
    SECOND_deleted = set(SECOND_deltas['deleteIds']).difference(FIRST_deltas['deleteIds'])
    FIRST_deleted = set(FIRST_deltas['deleteIds']).difference(SECOND_deltas['deleteIds'])

    #find update/delete conflictions
    FIRST_updated_SECOND_deleted = FIRST_updated.intersection(SECOND_deleted)
    SECOND_updated_FIRST_deleted = SECOND_updated.intersection(FIRST_deleted)

    #find update/update conflictions
    both_updated = FIRST_updated.intersection(SECOND_updated)

    #calculate sum of conflicts
    total_conflicts = len(FIRST_updated_SECOND_deleted) + len(SECOND_updated_FIRST_deleted) + len(both_updated)

    if(total_conflicts < 1):
        logging.info('No conflicts found.')
    else:
        
        #this will loop back if "more info" is chosen
        while True:
            #display sum of conflicts
            #prompt user to resolve all one way, resolve manually, show more info, or cancel
            logging.debug('{} conflicts found.'.format(total_conflicts))
            prompt = '{} conflicts found. Choose conflict resolution:'.format(total_conflicts)
            menu = ['Prioritize {} Changes'.format(first_name), 'Prioritize {} Changes'.format(second_name), 'Choose for each conflict', 'More info', 'Cancel']
            choice = ui.Options(prompt, menu)

            #in update/delete conflicts, update will either become add or be removed
            FIRST_updated -= FIRST_updated_SECOND_deleted
            SECOND_updated -= SECOND_updated_FIRST_deleted
            
            #print(choice)
            #sets to store global ids of objects being moved from updates to adds
            FIRST_new_adds = set()
            SECOND_new_adds = set()

            #if all in favor of FIRST:
            if (choice == 1):
            
                logging.info('Keeping edits from "{}"'.format(first_name))
                
                #turn updates that were deleted in destination into adds
                FIRST_new_adds = FIRST_updated_SECOND_deleted
                
                #remove deletes that were chosen to be ignored
                SECOND_deleted -= FIRST_updated_SECOND_deleted

                #remove updates that were chosen to be ignored
                SECOND_updated -= both_updated

                #exit while loop
                break

            #same for all in favor of SECOND:
            if (choice == 2):
            
                logging.info('Keeping edits from "{}"'.format(second_name))
                
                #same as above
                SECOND_new_adds = SECOND_updated_FIRST_deleted         
                FIRST_deleted -= SECOND_updated_FIRST_deleted
                FIRST_updated -= both_updated
                break

            #if manual:
            if (choice == 3):
                
                logging.info('Proceding with manual conflict resolution')
                
                #run through all conflict lists, print out conflict, prompt to resolve in favor of FIRST or SECOND
                menu = ['Keep update from {}'.format(first_name), 'Keep delete from {}'.format(second_name)]
                #for update/delete conflicts:
                for conflict in FIRST_updated_SECOND_deleted:
                    prompt = 'Object "{}" was updated in {} and deleted in {}. Choose:'.format(conflict, first_name, second_name)
                    choice = ui.Options(prompt, menu)
                    
                    #if in favor of update: update -> add, delete removed
                    if (choice == 1):
                        FIRST_new_adds.add(conflict)
                        SECOND_deleted.remove(conflict)
                    #if in favor of delete: update removed (already done above)

                menu = ['Keep delete from {}'.format(first_name), 'Keep update from {}'.format(second_name)]
                
                for conflict in SECOND_updated_FIRST_deleted:
                    prompt = 'Object "{}" was deleted in {} and updated in {}. Choose:'.format(conflict, first_name, second_name)
                    choice = ui.Options(prompt, menu)
                    
                    #if in favor of update: update -> add, delete removed
                    if (choice == 2):
                        SECOND_new_adds.add(conflict)
                        FIRST_deleted.remove(conflict)
                    #if in favor of delete: update removed (already done above)
                    

                #for update/update conflicts:
                menu = ['Keep update from {}'.format(first_name), 'Keep update from {}'.format(second_name)]

                for conflict in both_updated:
                    prompt = 'Object "{}" was updated in both {} and {}. Choose:'.format(conflict, first_name, second_name)
                    choice = ui.Options(prompt, menu)
                    #losing update removed
                    if(choice == 1):
                        SECOND_updated.remove(conflict)
                    elif(choice == 2):
                        FIRST_updated.remove(conflict)

                break

            #for more info, print out all conflicts
            if (choice == 4):
                
                print("Conflicts:")  
                print("both updated: {}".format(both_updated))
                print("{} updated {} deleted: {}".format(first_name, second_name, FIRST_updated_SECOND_deleted))
                print("{} updated {} deleted: {}".format(second_name, first_name, SECOND_updated_FIRST_deleted))

                #no break, loops back around and asks again

            if (choice == 5):
                #to cancel, return false
                return False, False
                

            
                
        #build new json objects:

        #lists to store new updates
        revisedSECONDUpdates = []
        revisedFIRSTUpdates = []

        #run through old updates and add them to new updates or adds
        for update in SECOND_deltas['updates']:
            GUID = update['attributes']['globalid']
            if GUID in SECOND_updated:
                revisedSECONDUpdates.append(update)
            if GUID in SECOND_new_adds:
                SECOND_deltas['adds'].append(update)

        for update in FIRST_deltas['updates']:
            GUID = update['attributes']['globalid']
            if GUID in FIRST_updated:
                revisedFIRSTUpdates.append(update)
            if GUID in FIRST_new_adds:
                FIRST_deltas['adds'].append(update)

        #overwrite old updates
        FIRST_deltas['updates'] = revisedFIRSTUpdates
        SECOND_deltas['updates'] = revisedSECONDUpdates

    #overwrite old deletes (even if no conflicts, because deletes are checked for uniqueness above)
    FIRST_deltas['deleteIds'] = list(FIRST_deleted)
    SECOND_deltas['deleteIds'] = list(SECOND_deleted)
       
    return FIRST_deltas, SECOND_deltas


