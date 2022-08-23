import json

from src import ui_functions as ui
from src.error import Cancelled

from datetime import datetime

logging = ui.logging

sde = None
agol = None

#import SDE functions
def ImportSDE():
    global sde
    if sde == None:
        logging.debug('Loading SDE functions...')#, 2)
        from src.sde_functions import sde
        logging.debug('SDE functions loaded.')#, 2, indent=4)

#import AGOL functions
def ImportAGOL():
    global agol
    if agol == None:
        logging.debug('Loading AGOL functions...')#, 2)
        from src.agol_functions import agol
        logging.debug('AGOL functions loaded.')#, 2, indent=4)

def GetSyncNum():
    try:
        sync_num_file = open('config/syncnum.txt', 'r')
        sync_num = int(sync_num_file.read().strip())
        sync_num_file.close()
    except:
        sync_num = int(input('Enter starting number for sync counter:').strip())

    return sync_num

# load syncs.json
def LoadSyncs():
    # loads json file containing set up syncs
    logging.debug('Loading syncs...')  # , 2)

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
    logging.debug('Syncs loaded.')  # , 2, indent=4)
    return syncs


# write syncs.json
def WriteSyncs(syncs):
    # writes sync.json with data in syncs
    logging.debug('Updating syncs.json...')  # , 2)

    try:
        json.dumps(syncs)
    except:
        logging.error("Invalid syncs!")
        return

    syncs_file = open('config/syncs.json', 'w')
    json.dump(syncs, syncs_file, indent=4)
    syncs_file.close()

    logging.debug('syncs.json updated.')  # , 2, indent=4)


class sync:
    def __init__(self, cfg, sync_dict=None):
        if sync_dict is not None:
            self.name = sync_dict['name']
            self.cfg = cfg

            first = self.ServiceFromJson(sync_dict['first'])
            second = self.ServiceFromJson(sync_dict['second'])

            self.services = [first, second]

            try:
                self.last_run = sync_dict['last_run']
            except ValueError:
                self.last_run = 'Never run'

        else:  # sync is none

            # UI to create a new sync
            while True:
                logging.debug('Creating sync...')

                self.cfg = cfg
                self.services = [None, None]

                print('A SYNC consists of metadata about two datasets that are kept identical (synchronized)\n'
                      'by applying updates, inserts, and deletions from one to the other, and visa versa. The\n'
                      'datasets can be a feature layer in a AGOL feature service, or a feature class in a SDE\n'
                      'enterprise geodatabase. The SYNC name should generally be the same as the SDE feature\n'
                      'class it is based on., and parenthesis can be used to help identify the type of service\n'
                      'and location. For example: "(SDE/GIS2-SDE/GIS1)" indicates the parent dataset is located\n'
                      'in a SDE geodatabase on server GIS2, and the child is located on server GIS1 in SDE.\n')

                print('Ensure that the two datasets are identical. This tool may not function correctly otherwise.\n')

                self.name = ui.GetName()

                i = 0
                loop = False
                while (i < 2):
                    print('')
                    types = ['SDE', 'AGOL', 'Back']
                    parent_child = ['parent', 'child']

                    serviceType = ui.Options('Enter where your {} dataset is stored:'.format(parent_child[i]), types)
                    SDE = 1
                    AGOL = 2
                    BACK = 3

                    if (serviceType == BACK):  # go back to start of this funtion
                        loop = True
                        break

                    else:
                        try:
                            if (serviceType == SDE):
                                # for SDE services
                                ImportSDE()
                                service = sde(self.cfg)
                            elif serviceType == AGOL:
                                # for AGOL services
                                ImportAGOL()
                                service = agol(self.cfg)
                        except Cancelled:
                            continue

                    print('')
                    service.Connect()
                    serverGen = service.ValidateService()

                    if (serverGen):
                        print('')
                        nickname = ui.GetNickname()

                        service.servergen = serverGen
                        service.nickname = nickname

                        self.services[i] = service

                    else:
                        # invalid service
                        continue

                    i = i + 1

                if not loop:
                    break

            self.UpdateLastRun()

    def ToDict(self):
        sync_dict = {
            'name': self.name,
            'first': self.services[0].ToDict(),
            'second': self.services[1].ToDict(),
            'last_run': self.last_run
        }

        return sync_dict

    def __str__(self):
        first = str(self.services[0])
        second = str(self.services[1])

        out = ('Details of sync "{}":\n'
               'Last run: {}\n'
               'Parent dataset:\n'
               '{}'
               'Child dataset:\n'
               '{}'.format(self.name, self.last_run, first, second))

        #print(out)

        return out

    def run(self):
        # print sync counter and date
        sync_num = GetSyncNum()
        logging.info('Sync counter: {}'.format(sync_num))
        # ui.printDate()

        # increment sync counter
        sync_num_file = open('config/syncnum.txt', 'w')
        sync_num_file.write(str(sync_num + 1))
        sync_num_file.close()

        # get sync from syncs.json
        logging.info('Executing sync "{}"...'.format(self.name))

        try:
            # Extract changes from both services
            first_deltas = self.services[0].ExtractChanges()
            second_deltas = self.services[1].ExtractChanges()

            if not (first_deltas and second_deltas):
                logging.error('Failed to extract changes.')
                return False

            # print total number of edits applied to both services
            print('')
            ui.PrintEdits(first_deltas, self.services[0], self.services[1])
            ui.PrintEdits(second_deltas, self.services[1], self.services[0])
            print('')

            # ask user to confirm before applying edits
            menu = ["Continue", "Cancel"]
            cancel_choice = ui.Options('Please review the extracted changes above before continuing.', menu)

            if cancel_choice == 2:
                logging.warning('Sync cancelled. No changes were made.\n')
                return False

            # reconcile changes
            first_deltas, second_deltas = ResolveConflicts(first_deltas, second_deltas,
                                                           self.services[0].nickname,
                                                           self.services[1].nickname)

            if not (first_deltas and second_deltas):
                logging.warning('Sync cancelled. No changes were made.\n')
                return False

            # Apply edits
            second_servergen = self.ApplyEdits(self.services[1], first_deltas)
            first_servergen = self.ApplyEdits(self.services[0], second_deltas)

            # check success
            if (second_servergen and first_servergen):
                # Update servergens
                logging.info('Updating servergen...')
                self.services[0].UpdateServergen(servergen=first_servergen)
                self.services[1].UpdateServergen(servergen=second_servergen)

                # record time
                self.UpdateLastRun()

                logging.info('Sync "{}" executed successfully!'.format(self.name))
                print('')

                return True

            else:
                logging.error('Edits failed. Changes may have been made.')
                print('')
                return False
            

        except Cancelled as e:
            logging.info(e.message)
            print('')
            return False

    def reregister(self):
        for service in self.services:
            service.Connect()
            serverGen = service.ValidateService()

            if(serverGen):
                service.UpdateServergen(serverGen)
                logging.info('Servergen updated!')
                self.UpdateLastRun()
                return True
            else:
                return False


    def edit(self):
        logging.info('Editing sync "{}"...'.format(self.name))
        print(self)

        while(True):
            menu = ['SAVE changes', 'DISCARD changes', 'Name',
                    'Parent dataset ("{}")'.format(self.services[0].nickname),
                    'Child dataset ("{}")'.format(self.services[1].nickname)]
            DONE = 1
            CANCEL = 2
            NAME = 3
            PARENT_DATASET = 4
            CHILD_DATASET = 5

            choice = ui.Options('Choose an option to edit:', menu)

            if(choice == NAME):
                print('Current name: "{}"'.format(self.name))
                self.name = ui.GetName()
                print('')

            elif(choice == DONE):
                menu = ['Re-register SYNC', 'DO NOT re-register', 'BACK']
                choice = ui.Options('Would you like to re-register this sync?', menu)
                if(choice == 1):
                    self.reregister()
                    print('')
                elif(choice == 3):
                    continue

                print(self)
                return sync

            elif(choice == CANCEL):
                menu = ['DISCARD changes', 'BACK']
                choice = ui.Options('Are you sure you want to discard your edits?', menu)
                if(choice == 1):
                    return False

            else:
                if(choice == PARENT_DATASET):
                    i = 0
                elif(choice == CHILD_DATASET):
                    i = 1

                service = self.services[i]

                # global menu choices
                DONE = 1
                #TYPE = 2
                NICKNAME = 2

                while True:
                    prompt = 'What would you like to edit in "{}"?'.format(service.nickname)

                    if isinstance(service, agol):
                        menu = ['DONE', 'Nickname', 'URL']
                        URL = 3

                        choice = ui.Options(prompt, menu)

                        if(choice == URL):
                            print('Current layer URL: {}/{}'.format(service.url, service.layer))
                            url, layer = ui.GetAgolURL()
                            if not url:
                                continue
                            service.url = url
                            service.layer = layer
                            print('')

                    elif isinstance(service, sde):
                        menu = ['DONE', 'Nickname', 'SDE Connection', 'Featureclass']
                        SDE_CONNECT = 3
                        FEATURECLASS = 4

                        choice = ui.Options(prompt, menu)

                        if(choice == SDE_CONNECT):
                            print('Current .sde file: {}'.format(service.sde_connect))
                            from sde_functions import GetSdeFilepath
                            sde_connect, hostname, database = GetSdeFilepath()
                            service.sde_connect = sde_connect
                            service.hostname = hostname
                            service.database = database

                            print('')

                        elif(choice == FEATURECLASS):
                            print('Current featureclass: {}'.format(service.fcName))
                            fcName = ui.GetFcName()
                            if fcName:
                                service.fcName = fcName

                            print('')

                    # if (choice == TYPE):
                    #     #create a whole new service
                    #     service = CreateNewService(cfg, i)
                    #     print('')
                    #     if (service == False):
                    #         continue
                    #     elif (service == 'loop'):
                    #         break

                    if (choice == NICKNAME):
                        print('Current nickname: {}'.format(service.nickname))
                        nickname = ui.GetNickname()
                        service.nickname = nickname
                        print('')

                    elif (choice == DONE):
                        service.Connect()
                        if service.ValidateService():
                            self.services[i] = service
                            print('')
                            break


    def UpdateLastRun(self):
        self.last_run = str(datetime.now())

    def ServiceFromJson(self, service):
        if service['type'] == 'SDE':
            ImportSDE()
            return sde(self.cfg, service)
        elif service['type'] == 'AGOL':
            ImportAGOL()
            return agol(self.cfg, service)

    @staticmethod
    def ApplyEdits(service, deltas):
    #wrapper for SQL/AGOL extract changes functions
        if (len(deltas['adds']) + len(deltas['updates']) + len(deltas['deleteIds'])) < 1:
            logging.info('No edits to apply to {}.'.format(service.nickname))

        else:
            logging.info('Applying edits to {}...'.format(service.nickname))

        return service.ApplyEdits(deltas)


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


