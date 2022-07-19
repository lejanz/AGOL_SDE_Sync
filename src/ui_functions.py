import json
import sys
from datetime import datetime
import logging as log

#allows us to print to console and logfile at the same time
# class Logger(object):
    # def __init__(self):
        # self.terminal = sys.stdout
        # self.log = open("logfile.log", "a")
        # self.logLevel = 1

    # def setLogLevel(self, cfg):
        # try:
            # self.logLevel = cfg.log_level
            # if(self.logLevel < 0):
                # self.logLevel = 0
        # except:
            # self.logLevel = 1

    # def write(self, message):
        # self.terminal.write(message)
        # self.log.write("{}".format(message))

    # def debug(self, message, level):
        # self.log.write(message)
        # if(level <= self.logLevel):
            # self.terminal.write(message)

    # def flush(self):
        # self.log.close()

# logger = Logger()

#get logging object
logging = log.getLogger("mylog")
logging.setLevel(log.DEBUG)

#setup STDIO output
formatter = log.Formatter('%(message)s')
stream_handler = log.StreamHandler()
stream_handler.setLevel(log.INFO)
stream_handler.setFormatter(formatter)

#setup file handler
file_formatter = log.Formatter('%(asctime)s |  %(levelname)s: %(message)s')
logFilePath = "sync.log"
file_handler = log.FileHandler(logFilePath)
file_handler.setFormatter(file_formatter)
file_handler.setLevel(log.DEBUG)

#add handlers to logger
logging.addHandler(file_handler)
logging.addHandler(stream_handler)

def printDate():
    print(datetime.now())
    
def Debug(message, messageLevel, indent=0):
    logger.debug('{}{}\n'.format((indent*' '), message), messageLevel)

def Break():
    print('----------------------')

def PrintServiceDetails(service):
    print('  Type: {}'.format(service['type']))
    print('  Nickname: {}'.format(service['nickname']))
    if(service['type'] == 'AGOL'):
        print('  AGOL URL: {}'.format(service['serviceUrl']))
        print('  AGOL layer: {}'.format(service['layerId']))
    else:
        if('sde_connect' in service.keys()):
            print('  SDE connect file: {}'.format(service['sde_connect']))
        print('  SQL Server: {}'.format(service['hostname']))
        print('  SDE featureclass: {}'.format(service['featureclass']))



def Completed(attempt, attempted, completed):
    #prints number of attempted/successful adds, updates, or deletes. 
    
    if attempted > 0:
        
        plural = 's'
        if completed == 1:
            plural = ''

        logging.info('Completed {} {}{} (attempted {})'.format(str(completed), attempt, plural, str(attempted)))

def Options(prompt, menu, allow_filter=False, filter_string = ''):
    #print list of options for user to chose from
    #if allow_filter = true, strings entered will call this function again, filtering results
    logging.debug('Prompting: "{}"'.format(prompt))
    print(prompt)
    
    filtered_menu = [item for item in menu if filter_string.lower() in item.lower()]
    if(len(filtered_menu) < 1):
        print('\nNo results. Clearing filter.\n')
        filtered_menu = menu

    i = 1
    for item in filtered_menu:
        print('  {}. {}'.format(i, item))
        i += 1

    string = ''
    if(allow_filter):
        string = ', or type to filter'

    while True:
        response = unicode(raw_input('Enter selection{}:'.format(string)))
        print('')
        if(response.isnumeric()):
            response = int(response)
            if(response > 0 and response <= len(filtered_menu)):
                logging.debug('User chose: "{}"'.format(menu[response-1]))
                return response
            else:
                print('\nValue out of range!\n')
        elif(allow_filter):
            if(response == ''):
                print('\nClearing filter.\n')
                return Options(prompt, menu, allow_filter=True)
            else:
                return Options(prompt, menu, allow_filter=True, filter_string = response)
        else:
            print('\nInvalid response!\n')




