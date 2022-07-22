##WELCOME TO THE LEJANZ AGOL/SDE SYNC TOOL
##Inspired by Nick Neubel
##Copyright 2021-2022 Leo Janzen
##
##Terminology:
##    service: the featureclass or feature service
##    sync: a pair of services registered with this tool
##    deltas: edits extracted from or applied to a service

import json
import sys
from src import ui_functions as ui
from src import sync_functions
from datetime import datetime

logging = ui.logging
# logging.basicConfig(
    # level=logging.DEBUG,
    # format="%(message)s",
    # handlers=[
        # logging.FileHandler("sync.log"),
        # logging.StreamHandler(sys.stdout)
    # ]
# )

#sys.stdout = ui.logger
#sys.stderr = ui.logger

#load configuration file
def LoadConfig():
    logging.debug('Loading config...')#, 2)
    try:
        from config import config
    except:
        logging.error('Error loading config!')
        return False
        #TODO: make config builder?

    logging.debug('Config loaded.')#, 2, indent=4)
    
    return config
        
def LogJson(filename, jsn): 
    file = open('json_logs\{}.json'.format(filename), 'w')
    json.dump(jsn, file, indent=4)
    file.close()

def GetSyncNum():
    try:
        sync_num_file = open('config/syncnum.txt', 'r')
        sync_num = int(sync_num_file.read().strip())
        sync_num_file.close()
    except:
        sync_num = int(raw_input('Enter starting number for sync counter:').strip())

    return sync_num
    
def PrintEdits(deltas, first_service, second_service):
    num_adds = len(deltas['adds'])
    num_updates = len(deltas['updates'])
    num_deletes = len(deltas['deleteIds'])
    print("{} adds, {} updates, and {} deletes will be applied from {} to {}.".format(num_adds,
                                                                                        num_updates,
                                                                                        num_deletes,
                                                                                        first_service['nickname'],
                                                                                        second_service['nickname']))
    return num_adds + num_updates + num_deletes

def main():
    logging.debug('-------------')
    logging.debug('Program start')
    #load config
    cfg = LoadConfig()
    if not cfg:
        return
    #ui.logger.setLogLevel(cfg)

    #load syncs
    syncs = sync_functions.LoadSyncs()
    stuff = ["I'm sorry, Dave.", "I can't do that, Dave.", "What are you doing, Dave?", "Goodbye, Dave."]

    while True:

        #prompt user to select sync
        syncNames = [s['name'] for s in syncs]
        
        #copy syncNames into menu so extras can be added
        #menu = syncNames[:]
        menu = ['Run SYNC', 'View SYNC', 'Create SYNC', 'Re-register SYNC', 'Delete SYNC', 'HELP', 'Exit']
        RUN_SYNC = 1
        VIEW_SYNC = 2
        CREATE_SYNC = 3
        REREGISTER_SYNC = 4
        DELETE_SYNC = 5
        HELP = 6
        EXIT = 7

        #add extras to beginning of menu
        #for index, extra in enumerate(menuExtras):
        #    menu.insert(index, extra)
        
        choice = ui.Options('Select an option:', menu)

        if(choice in [RUN_SYNC, VIEW_SYNC, REREGISTER_SYNC, DELETE_SYNC]):
            if(len(syncs) == 0):
                print('No SYNCs set up!\n')
                continue
            syncNames.append('Back')

        if (choice == VIEW_SYNC): #view sync details
            choice = ui.Options('Choose a SYNC to view:', syncNames, allow_filter=True)
            choice -= 1
            if(choice == len(syncs)): #cancel option
                continue

            sync = syncs[choice]
            ui.PrintSyncDetails(sync)

        elif (choice == CREATE_SYNC): #create new sync
            sync = 'loop'
            while(sync == 'loop'):
                sync = sync_functions.CreateNewSync(cfg)
            if(sync):
                syncs.append(sync)
                sync_functions.WriteSyncs(syncs)
                logging.info('SYNC "{}" created!'.format(sync['name']))
                print('')
                ui.PrintSyncDetails(sync)

        elif (choice == REREGISTER_SYNC):
            choice = ui.Options('Choose a SYNC to re-register:', syncNames, allow_filter=True)
            choice -= 1
            if (choice == len(syncs)):  # cancel option
                continue

            sync = sync_functions.ReregisterSync(syncs[choice], cfg)

            if sync:
                syncs[choice] = sync
                sync_functions.WriteSyncs(syncs)
                print('Sync "{}" re-registered successfuly!\n'.format(sync['name']))
            else:
                logging.info("Failed to re-register sync!")

            


        elif (choice == DELETE_SYNC): #delete sync
            deleteIndex = ui.Options('Choose sync to delete', syncNames, allow_filter=True)
            deleteIndex -= 1
            
            if deleteIndex == len(syncs):  #if cancel is chosen
                continue
                
            nickname = syncs[deleteIndex]['name']

            #ask to confirm
            menu = ['Continue', 'Cancel']
            choice = ui.Options('Deleting sync "{}". Continue?'.format(nickname), menu)

            if choice == 1:
                #remove sync
                syncs.pop(deleteIndex)
                #write updated syncs to json
                sync_functions.WriteSyncs(syncs)
                logging.info('Sync "{}" deleted.'.format(nickname))

        #integrated with apply edits
        #elif (choice == 3): #run backup script
         #   sync_num = GetSyncNum()
         #   BackupFeatureClass(sync_num)
         #   logging.info('Backup script completed.')

        elif (choice == HELP): #help
            import os
            print('Opening help page...\n')
            os.system('START https://doimspp.sharepoint.com/:w:/r/sites/ext-nps-insidernsp/_layouts/15/Doc.aspx?'
                      'sourcedoc=%7B9AA1B96F-0410-43FD-9DA1-A0871BEA142B%7D&file=LSync%20Help.docx&action=default&mobileredirect=true')

        elif (choice == EXIT): #exit
            logging.info('')

            print(stuff.pop(0))
            print('')

            if(len(stuff) == 0):
                return  #ends function main()

            
        elif(choice == RUN_SYNC):

            choice = ui.Options('Choose a SYNC to run:', syncNames, allow_filter=True)
            choice -= 1
            if (choice == len(syncs)):  #cancel option
                continue
                             
            #print sync counter and date
            sync_num = GetSyncNum()
            logging.info('Sync counter: {}'.format(sync_num))
            #ui.printDate()

            #increment sync counter  
            sync_num_file = open('config/syncnum.txt', 'w')
            sync_num_file.write(str(sync_num + 1))
            sync_num_file.close()

            #get sync from syncs.json
            sync = syncs[choice]

            logging.info('Executing sync "{}"...'.format(sync['name']))

            #Extract changes from both services
            first_deltas, first_data = sync_functions.ExtractChanges(sync['first'], cfg)
            second_deltas, second_data = sync_functions.ExtractChanges(sync['second'], cfg)

            if first_deltas == None or second_deltas == None:
                logging.error('Failed to extract changes.')
                #ui.Break()
                continue

            #ui.Break()
    
            #print total number of edits applied to both services
            print('')
            PrintEdits(first_deltas, sync['first'], sync['second'])
            PrintEdits(second_deltas, sync['second'], sync['first'])
            print('')

            #ask user to confirm before applying edits
            menu = ["Continue", "Cancel"]
            cancel_choice = ui.Options('Please review the extracted changes above before continuing.', menu)
            
            if cancel_choice == 2:
                logging.warning('Sync cancelled. No changes were made.\n')
                #ui.Break()
                continue
            
            LogJson('{}_to_{}_before_reconcile'.format(sync['first']['nickname'], sync['second']['nickname']), first_deltas)
            LogJson('{}_to_{}_before_reconcile'.format(sync['second']['nickname'], sync['first']['nickname']), second_deltas)
            
            #reconcile changes
            first_deltas, second_deltas = sync_functions.ResolveConflicts(first_deltas, second_deltas, sync['first']['nickname'], sync['second']['nickname'])

            if not (first_deltas and second_deltas):
                logging.warning('Sync cancelled. No changes were made.\n')
                #ui.Break()
                continue
                
            LogJson('{}_to_{}_final'.format(sync['first']['nickname'], sync['second']['nickname']), first_deltas)
            LogJson('{}_to_{}_final'.format(sync['second']['nickname'], sync['first']['nickname']), second_deltas)
                
            #Apply edits
            second_servergen = sync_functions.ApplyEdits(sync['second'], cfg, first_deltas, sync_num, data=second_data)
            first_servergen = sync_functions.ApplyEdits(sync['first'], cfg, second_deltas, sync_num, data=first_data)

            #ui.Break()

            #check success
            if (second_servergen and first_servergen):    
                #Update servergens
                logging.info('Updating servergen...')
                syncs[choice]['first']['servergen'] = first_servergen
                syncs[choice]['second']['servergen'] = second_servergen

                #record time
                syncs[choice]['last_run'] = str(datetime.now())
                
                sync_functions.WriteSyncs(syncs)
                logging.info('Sync "{}" executed successfully!'.format(sync['name']))
                  
            else:
                logging.error('Edits failed. Changes may have been made.\n')

            logging.info('')
            #ui.Break()
                
                
if __name__ == '__main__':
    main()
