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
        menu = syncNames[:]
        menuExtras = ['Create SYNC', 'HELP', 'Exit']

        # add extras to beginning of menu
        for index, extra in enumerate(menuExtras):
            menu.insert(index, extra)

        CREATE_SYNC = 1
        HELP = 2
        EXIT = 3


        choice = ui.Options('Select a SYNC:', menu)

        if (choice == CREATE_SYNC): #create new sync
            sync = 'loop'
            while(sync == 'loop'):
                sync = sync_functions.CreateNewSync(cfg)

            if(sync):
                syncs.append(sync)
                sync_functions.WriteSyncs(syncs)
                logging.info('SYNC "{}" created!'.format(sync['name']))
                print('')
                ui.PrintSyncDetails(sync)

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

        else:
            sync_index = choice - len(menuExtras) - 1
            sync = syncs[sync_index]
            n = sync['name']

            menu = ['Run "{}"'.format(n), 'Backup "{}"'.format(n), 'View "{}"'.format(n), 'Edit "{}"'.format(n), 'Re-register "{}"'.format(n), 'Delete "{}"'.format(n), 'Back']
            RUN_SYNC = 1
            BACKUP_SYNC = 2
            VIEW_SYNC = 3
            EDIT_SYNC = 4
            REREGISTER_SYNC = 5
            DELETE_SYNC = 6
            BACK = 7

            choice = ui.Options('Select an option:', menu)

            if (choice == BACKUP_SYNC):
                sync_num = GetSyncNum()

                for service in [sync['first'], sync['second']]:
                    sync_functions.BackupService(service, cfg, sync_num)

                print('')

            if (choice == VIEW_SYNC):  # view sync details
                ui.PrintSyncDetails(sync)

            elif (choice == EDIT_SYNC):
                import copy
                sync = copy.deepcopy(sync)  # make a copy of sync so we do not alter the original

                sync = sync_functions.EditSync(sync, cfg)

                if(sync):
                    syncs[sync_index] = sync
                    logging.info('Edits applied to "{}"!'.format(sync['name']))
                    sync_functions.WriteSyncs(syncs)
                else:
                    logging.info('Changes reverted.')

                print('')

            elif (choice == REREGISTER_SYNC):
                # ask to confirm
                print('Re-register ONLY if you are sure that your two datasets are currently IDENTICAL!\n')
                menu = ['Continue', 'Cancel']
                choice = ui.Options('Re-registering sync "{}". Continue?'.format(sync['name']), menu)

                if choice == 1:
                    sync = sync_functions.ReregisterSync(sync, cfg)
                    if sync:
                        syncs[sync_index] = sync
                        sync_functions.WriteSyncs(syncs)
                        logging.info('Sync "{}" re-registered successfuly!'.format(sync['name']))
                    else:
                        logging.info("Failed to re-register sync!")

                    print('')

            elif (choice == DELETE_SYNC):  # delete sync
                nickname = sync['name']

                # ask to confirm
                menu = ['Continue', 'Cancel']
                choice = ui.Options('Deleting sync "{}". Continue?'.format(nickname), menu)

                if choice == 1:
                    # remove sync
                    syncs.pop(sync_index)
                    # write updated syncs to json
                    sync_functions.WriteSyncs(syncs)
                    logging.info('Sync "{}" deleted.'.format(nickname))
                    print('')

            elif (choice == BACK):
                continue

            elif (choice == RUN_SYNC):
                # print sync counter and date
                sync_num = GetSyncNum()
                logging.info('Sync counter: {}'.format(sync_num))
                # ui.printDate()

                # increment sync counter
                sync_num_file = open('config/syncnum.txt', 'w')
                sync_num_file.write(str(sync_num + 1))
                sync_num_file.close()

                # get sync from syncs.json
                logging.info('Executing sync "{}"...'.format(sync['name']))

                # Extract changes from both services
                first_deltas, first_data = sync_functions.ExtractChanges(sync['first'], cfg)
                second_deltas, second_data = sync_functions.ExtractChanges(sync['second'], cfg)

                if first_deltas == None or second_deltas == None:
                    logging.error('Failed to extract changes.')
                    # ui.Break()
                    continue

                # ui.Break()

                # print total number of edits applied to both services
                print('')
                ui.PrintEdits(first_deltas, sync['first'], sync['second'])
                ui.PrintEdits(second_deltas, sync['second'], sync['first'])
                print('')

                # ask user to confirm before applying edits
                menu = ["Continue", "Cancel"]
                cancel_choice = ui.Options('Please review the extracted changes above before continuing.', menu)

                if cancel_choice == 2:
                    logging.warning('Sync cancelled. No changes were made.\n')
                    # ui.Break()
                    continue

                # LogJson('{}_to_{}_before_reconcile'.format(sync['first']['nickname'], sync['second']['nickname']), first_deltas)
                # LogJson('{}_to_{}_before_reconcile'.format(sync['second']['nickname'], sync['first']['nickname']), second_deltas)

                # reconcile changes
                first_deltas, second_deltas = sync_functions.ResolveConflicts(first_deltas, second_deltas,
                                                                              sync['first']['nickname'],
                                                                              sync['second']['nickname'])

                if not (first_deltas and second_deltas):
                    logging.warning('Sync cancelled. No changes were made.\n')
                    # ui.Break()
                    continue

                #LogJson('{}_to_{}_final'.format(sync['first']['nickname'], sync['second']['nickname']), first_deltas)
                #LogJson('{}_to_{}_final'.format(sync['second']['nickname'], sync['first']['nickname']), second_deltas)

                # Apply edits
                second_servergen = sync_functions.ApplyEdits(sync['second'], cfg, first_deltas, sync_num,
                                                             data=second_data)
                first_servergen = sync_functions.ApplyEdits(sync['first'], cfg, second_deltas, sync_num,
                                                            data=first_data)

                # ui.Break()

                # check success
                if (second_servergen and first_servergen):
                    # Update servergens
                    logging.info('Updating servergen...')
                    syncs[sync_index]['first']['servergen'] = first_servergen
                    syncs[sync_index]['second']['servergen'] = second_servergen

                    # record time
                    syncs[sync_index]['last_run'] = str(datetime.now())

                    sync_functions.WriteSyncs(syncs)
                    logging.info('Sync "{}" executed successfully!'.format(sync['name']))

                else:
                    logging.error('Edits failed. Changes may have been made.\n')

                logging.info('')
                # ui.Break()
                
if __name__ == '__main__':
    main()
