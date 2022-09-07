##WELCOME TO THE LEJANZ AGOL/SDE SYNC TOOL
##Inspired by Nick Neubel
##Copyright 2021-2022 Leo Janzen
##
##Terminology:
##    service: the featureclass or feature service
##    sync: a pair of services registered with this tool
##    deltas: edits extracted from or applied to a service

# TODO: add checks for libraries and library versions

import json
from src import ui_functions as ui
from src import sync_functions
from src.error import Cancelled
from src.test_requirements import TestRequirements

logging = ui.logging


# load configuration file
def LoadConfig():
    logging.debug('Loading config...')
    try:
        from config import config
    except:
        logging.error('Error loading config!')
        return False
        # TODO: make config builder?

    logging.debug('Config loaded.')
    
    return config

        
def LogJson(filename, jsn): 
    file = open('json_logs\\{}.json'.format(filename), 'w')
    json.dump(jsn, file, indent=4)
    file.close()


def GetSyncNum():
    try:
        sync_num_file = open('config/syncnum.txt', 'r')
        sync_num = int(sync_num_file.read().strip())
        sync_num_file.close()
    except:
        sync_num = int(input('Enter starting number for sync counter:').strip())

    return sync_num


def main():
    tr = TestRequirements()
    tr.test_requirements()

    logging.debug('-------------')
    logging.debug('Program start')
    # load config
    cfg = LoadConfig()
    if not cfg:
        return

    # load syncs
    syncs = sync_functions.LoadSyncs()
    stuff = ["I'm sorry, Dave.", "I can't do that, Dave.", "What are you doing, Dave?", "Goodbye, Dave."]

    while True:

        # prompt user to select sync
        syncNames = [s['name'] for s in syncs]
        
        # copy syncNames into menu so extras can be added
        menu = syncNames[:]
        menuExtras = ['Create SYNC', 'HELP', 'Exit', 'Re-order SYNCs']

        # add extras to beginning of menu
        for index, extra in enumerate(menuExtras):
            menu.insert(index, extra)

        CREATE_SYNC = 1
        HELP = 2
        EXIT = 3
        REORDER = 4

        choice = ui.Options('Select a SYNC:', menu)

        if (choice == CREATE_SYNC):  # create new sync
            try:
                sync = sync_functions.sync(cfg)
            except Cancelled:
                print('')
                continue

            if(sync):
                syncs.append(sync.ToDict())
                sync_functions.WriteSyncs(syncs)
                logging.info('SYNC "{}" created!'.format(sync.name))
                print('')
                print(sync)

        elif (choice == HELP):  # help
            import os
            print('Opening help page...\n')
            os.system('START https://doimspp.sharepoint.com/:w:/r/sites/ext-nps-insidernsp/_layouts/15/Doc.aspx?'
                      'sourcedoc=%7B9AA1B96F-0410-43FD-9DA1-A0871BEA142B%7D&file=LSync%20Help.docx&action=default&mobileredirect=true')

        elif (choice == EXIT):  # exit
            logging.info('')

            print(stuff.pop(0))
            print('')

            if(len(stuff) == 0):
                return  # ends function main()

        elif (choice == REORDER):
            print('Current order:')
            for i, name in enumerate(syncNames):
                i = str(i + len(menuExtras) + 1)
                print("{}. {}".format(i, name))

            print('Enter the OLD sync numbers in the NEW order in which you would like them, separated by commas, or type "quit" to cancel:')
            while True:
                new_order = input('Enter numbers:')
                if new_order.lower() == 'quit':
                    print('')
                    break

                new_order = new_order.split(',')
                if len(new_order) != len(syncs):
                    print('Incorrect number of entries!')
                    continue

                new_sync_nums = []
                done = True
                for num in new_order:
                    try:
                        num = int(num)
                    except ValueError:
                        print('Invalid entry: "{}"'.format(num))
                        done = False
                        break

                    if (num < (len(menuExtras) + 1)) or (num > len(menu)):
                        print('Entry out of range: {}'.format(num))
                        done = False
                        break

                    if num in new_sync_nums:
                        print('Duplicate entries: {}'.format(num))
                        done = False
                        break

                    new_sync_nums.append(num)

                if done:
                    new_syncs = []
                    for num in new_sync_nums:
                        new_syncs.append(syncs[num - len(menuExtras) - 1])
                    syncs = new_syncs
                    sync_functions.WriteSyncs(syncs)
                    print('Successfully reordered syncs!\n')
                    break

        else:
            sync_index = choice - len(menuExtras) - 1
            sync = sync_functions.sync(cfg, syncs[sync_index])
            n = sync.name

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
                sync.Backup(sync_num)
                print('')

            if (choice == VIEW_SYNC):  # view sync details
                print(sync)

            elif (choice == EDIT_SYNC):
                success = sync.edit()

                if success:
                    syncs[sync_index] = sync.ToDict()
                    logging.info('Edits applied to "{}"!'.format(sync.name))
                    sync_functions.WriteSyncs(syncs)
                else:
                    sync = sync_functions.sync(cfg, syncs[sync_index])  # reacquire from json just in case
                    logging.info('Changes reverted.')

                print('')

            elif (choice == REREGISTER_SYNC):
                # ask to confirm
                print('Re-register ONLY if you are sure that your two datasets are currently IDENTICAL!\n')
                menu = ['Continue', 'Cancel']
                choice = ui.Options('Re-registering sync "{}". Continue?'.format(sync.name), menu)

                if choice == 1:
                    success = sync.reregister()
                    if success:
                        syncs[sync_index] = sync.ToDict()
                        sync_functions.WriteSyncs(syncs)
                        logging.info('Sync "{}" re-registered successfully!'.format(sync.name))
                    else:
                        logging.info("Failed to re-register sync!")

                    print('')

            elif (choice == DELETE_SYNC):  # delete sync
                nickname = sync.name

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
                success = sync.run()

                # update syncs.json on success
                if success:
                    syncs[sync_index] = sync.ToDict()
                    sync_functions.WriteSyncs(syncs)
                    logging.info('')

                
if __name__ == '__main__':
    main()
