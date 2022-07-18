from . import ui_functions as ui
import json
from error import HTTPError, AGOLServiceError, AGOLError, JSONDecodeError

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
        syncs = []

    try:
        syncs = json.load(syncs_file)
    except:
        logging.error('Invalid sync file!')
        syncs = []

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

def CreateNewSync(cfg):
    #UI to create a new sync
    logging.debug('Creating sync...')
    print('Please ensure that the two copies you are setting up for sync are currently identical!\nThis tool may not function correctly otherwise!\n')

    name = raw_input('Please enter a name for this sync:')

    numbers = ['first', 'second']

    sync = {'name': name, 'first': {}, 'second': {}}
    
    i = 0
    while(i < 2): 
        print('\nEnter the details for your {} service:\n').format(numbers[i])

        types = ['SDE', 'AGOL', 'Cancel']

        serviceType = ui.Options('Select service type:', types)

        if(serviceType == 3):
            print("Cancelling\n")
            return False

        elif(serviceType == 1):
            #for SDE services

            ImportSDE()

            #get details
            sde_connect = raw_input('Enter path to .sde file:')

            try:
                hostname, database = sde.GetServerFromSDE(sde_connect)
            except Exception as e:
                print("Unable to open .sde file")
                continue
            
            #hostname = raw_input('Enter SDE hostname (i.e. inpredwgis2):')
            #database = raw_input('Enter SDE database name (i.e. redw):')
            fcName = raw_input('Enter featureclass name:')

            print('')

            #check that featureclass exists in sde table registry 
            connection = sde.Connect(hostname, database, cfg.SQL_username, cfg.SQL_password)

            if not connection:
                continue

            if(sde.CheckFeatureclass(connection, fcName)):
                
                #get current information
                stateId = sde.GetCurrentStateId(connection)
                globalIds = sde.GetGlobalIds(connection, fcName)

                logging.info('Featureclass valid!')#, 1)

                nickname = raw_input('Enter a nickname for this feature service (used in conflict resolution):')

                service = {'servergen': {'stateId': stateId, 'globalIds': globalIds},
                           'type': 'SDE',
                           'featureclass': fcName,
                           'sde_connect': sde_connect,
                           'hostname': hostname,
                           'database': database,
                           'nickname': nickname}
            else:
                continue
            
        else:
            #for AGOL services
            ImportAGOL()
            
            #get service details
            url = raw_input('Enter service url:')
            layerId = int(raw_input('Enter service layer id:'))

            print('')

            #check that service is set up correctly
            token = agol.GetToken(cfg.AGOL_url, cfg.AGOL_username, cfg.AGOL_password)

            try:
                ready, serverGen, srid = agol.CheckService(url, layerId, token)
            except (HTTPError, AGOLServiceError, AGOLError, JSONDecodeError) as e:
                logging.error('Error checking AGOL service!')
                logging.error(e.message)
                continue

            logging.info('Feature service valid!')#, 1)

            nickname = raw_input('Enter a nickname for this feature service (used in conflict resolution):')

            service = {'type': 'AGOL',
                       'serviceUrl': url,
                       'layerId': layerId,
                       'servergen': serverGen,
                       'nickname': nickname}

        sync[numbers[i]] = service
        i = i + 1

    return sync
   

#def BackupFeatureClass(sync_num):
#    ImportSDE()
#    sde.BackupFeatureClass(sync_num)

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

    for add in deltas['adds']:
        add = CleanDelta(add, srid)
        
    for update in deltas['updates']:
        update = CleanDelta(update, srid)

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


