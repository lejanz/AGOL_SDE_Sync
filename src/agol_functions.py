import json
import requests
from ui_functions import Debug, Completed, logging
import time
from error import HTTPError, AGOLError, AGOLServiceError, JSONDecodeError, Error

def ParseJSON(jsn):                      #json.loads with error catching
    try:
        return json.loads(jsn)
    except ValueError:                   #catch json decode error and print response for debugging hellp
        logging.error('Error parsing JSON!')
        logging.error('JSON: {}'.format(jsn))
        raise JSONDecodeError('Error parsing JSON!')

def GetToken(url, username, password):
    #returns token for use with further requests

    logging.debug('Getting AGOL token...')#, 2)
    
    url = url + '/sharing/generateToken'
    payload = {'username': username, 'password': password, 'referer': 'www.arcgis.com', 'f': 'json'}

    r = requests.post(url, data=payload)

    response = ParseJSON(r.content)

    if not response.has_key('token'):
        logging.error('No token returned!')
        logging.error(response)
        raise AGOLError('Failed to acquire token.', url)

    logging.debug('Token acquired.')#, 2, indent=4)
    
    return response['token']


def CreateUrl(base_url, params):
    base_url += '?'
    
    for k,v in params.items():
        base_url += '{}={}&'.format(k,v)
        
    base_url += 'f=json'
    
    logging.debug('Created URL: {}'.format(base_url))#, 3)
    
    return base_url
         
                
def ApiCall(url, data, token): #, serverGen):
    #performs async rest api call 

    logging.debug('Sending AGOL API request...')#, 2)

    url = CreateUrl(url, data)
    response = requests.post(url)

    url = ParseJSON(response.content)["statusUrl"] 
    data  = {'token': token}
    url = CreateUrl(url, data)

    while True:
        time.sleep(3)

        logging.debug('Checking status URL...')#, 2, indent=4)
        response = requests.post(url)
        content = ParseJSON(response.content)
        
        logging.debug('Status: {}'.format(content['status']))#, 2, indent=6)
        
        if (content["status"] != 'Pending'):
            break

    if content['status'] == 'Failed':
        raise AGOLServiceError(content, url)

    else:
        logging.debug('Getting result...')#, 2, indent=4)
        
        url = content['resultUrl']
        url = CreateUrl(url, data)

        response = requests.post(url)
        content = ParseJSON(response.content)
        #print(json.dumps(content, indent=4))
        logging.debug('API response received')#, 2, indent=4)

    return content

def CheckService(base_url, layer, token): #, serverGen):
    #returns None if issue with service
    #returns False if service is missing capabilities
    #returns True, serverGen if service is set up correctly

    logging.debug('Checking AGOL service capabilities...')#, 1)

    data = {'token': token, 'returnUpdates': True}

    url = CreateUrl(base_url, data)
    
    response = requests.post(url)

    if(response.status_code !=  200):
        raise HTTPError("HTTP error while checking AGOL service!", url, response.status_code)
        
        #return False, None, None
    

    content = ParseJSON(response.content)

    #print(json.dumps(content, indent=4))
                          
    if(not content.has_key('capabilities')):       #check if service returned capabilities
        if(content.has_key('error')):              #check if service returned an error
            raise AGOLServiceError(content, url)
        else:                                      #raise generic AGOL Error
            raise(AGOLError('AGOL Service did not respond with "capabilities!"', url))
        
    capabilities = content['capabilities']
    capabilities = capabilities.lower()
    
    required = ['update', 'changetracking', 'create', 'delete', 'update', 'editing']  #cabilitities we want


    missing = set(required) - set(capabilities.split(','))   #check that service has all required capabilities
    #for req in required:                 
    #    if not req in capabilities:
    #        missing.append(req)

    if len(missing) > 0:                 #if any capabilities missing, raise exception
        missing = ','.join(missing)
        raise Error('Missing capability(s): {}'.format(missing))
        #return False, None, None

    try:
        serverGens = content["changeTrackingInfo"]['layerServerGens']
    except:
        print('Error extracting server gen from AGOL! URL: {}'.format(url))
        raise
    
    serverGen = [g for g in serverGens if g['id'] == layer]

    try:
        serverGen = serverGen[0]
    except:
        raise AGOLError('Layer {} does not exist'.format(layer), url)
        #return False, None, None

    try:
        srid = content['spatialReference']['wkid']
    except:
        print('Error extracting SRID from AGOL! URL: {}'.format(url))
        raise

    try:
        serviceId = content['serviceItemId']
    except NameError:
        logging.error('Unable to aquire service ID!')
        raise

    logging.debug('Feature service is valid.')#, 1, indent=4)
    
    return serviceId, serverGen, srid

def Backup(base_url, username, serviceId, token, layerId):

    logging.info('Backing up feature service...')
    
    url = '{}/sharing/rest/content/users/{}/export'.format(base_url, username)
    data = {'token': token,
            'itemId': serviceId,
            'exportFormat': 'File Geodatabase',
            'exportParameters': {'layers':[{'id':layerId}]}}

    url = CreateUrl(url, data)

    response = requests.post(url)
    content = ParseJSON(response.content)

    try:
        exportId = content['exportItemId']
    except NameError:
        logging.error('Export failed!')
        return

    exportUrl = '{}/home/item.html?id={}'.format(base_url, exportId)

    logging.info('Backup successful.')
    logging.info('Exported backup can be found in the content folder for {}, or at the following URL:'.format(username))
    logging.info(exportUrl)

def ExtractChanges(service, cfg):
    #extracts changes since specified serverGen and returns them as an object
    
    #aquire token
    token = GetToken(cfg.AGOL_url, cfg.AGOL_username, cfg.AGOL_password)
    
    #check service and aquire data
    serviceId, newServerGen, srid = CheckService(service['serviceUrl'], service['layerId'], token)

    serverGen = service['servergen']

    data  = {'token': token,
            'layers': [service['layerId']],
            'returnInserts': 'true',
            'returnUpdates': 'true',
            'returnDeletes': 'true',
            'layerServerGens': json.dumps([serverGen]),
            'dataFormat': 'json'}
               
    url = service['serviceUrl'] + '/extractChanges'
    
    response = ApiCall(url, data, token)

    try:
        deltas = response['edits'][0]['features']
    except AttributeError:
        raise AGOLError('Unexpected response from AGOL!\n\nResponse:\n{}\n'.format(response), url)
        
    data = {'token': token, 'serviceid': serviceId}

    logging.info('Extracted AGOL changes successfully.')
    #Debug('Success.\n', 0, indent=4)

    return deltas, data, srid

def ApplyEditsInner(url, layer, token, deltas):

    logging.debug('Sending AGOL apply edits API request...')
    
    deltas['id'] = layer
    
    data = {'token': token,
            'edits': json.dumps([deltas]),
            'useGlobalIds': 'true'}

    url += '/applyEdits?f=json'

    #url = CreateUrl(url, data)

    logging.debug('URL: {}'.format(url))#, 3)

    response = requests.post(url, data=data) #, json={'edits': deltas})

    if(response.status_code != 200):
        raise(HTTPError('Error while applying edits!', url, response.status_code))

    content = ParseJSON(response.content)
    content = content[0]

    if content.has_key('error'):
        raise AGOLServiceError(content, url)
       # print('Error: {}\n{}'.format(json.dumps(content['error'], indent=4)))
       # return False
    
    return content

def ApplyEdits(service, cfg, deltas, sync_num, backup, data=None):
    #applies edits to service, returns success boolean

    url = service['serviceUrl']
    layer = service['layerId']
    
    if data == None:
            token = GetToken(cfg.AGOL_url, cfg.AGOL_username, cfg.AGOL_password)
            serviceId, gen, srid = CheckService(service['serviceUrl'], service['layerId'], token)
    else:
        token = data['token']
        serviceId = data['serviceid']

    if backup:
        Backup(cfg.AGOL_url, cfg.AGOL_username, serviceId, token, layer)
    
    #if not agol.ApplyEdits(service['serviceUrl'], service['layerId'], token, deltas):
    #    return Fals

    #calculate numbers of adds 
    numAdds = len(deltas['adds'])
    numUpdates = len(deltas['updates'])
    numDeletes = len(deltas['deleteIds'])

    #rename deleteIds to deletes (AGOL syntax)
    deltas['deletes'] = deltas.pop('deleteIds')

    #apply edits
    content = ApplyEditsInner(url, layer, token, deltas)

    #if not content:
    #   return False

    success = True
    tryAsAdd = []

    successful = {'addResults': 0, 'updateResults': 0, 'deleteResults': 0}
    failed = []
    
    logging.debug('Checking results of apply edits...')

    for results in ['addResults', 'updateResults', 'deleteResults']:
        if (content.has_key(results)):
            for result in content[results]:
                if not result['success']:
                    #check for updates that should have been adds
                    if(results == 'updateResults' and result['error']['code'] == 1019):
                        #print('trying as add')
                        tryAsAdd.append(result['globalId'])
                    else:   
                        print(result['error'])
                        success = False
                        failed.append(result['globalId'])
                else:
                    successful[results] += 1

    if (numAdds + numUpdates + numDeletes) > 0:
        print('')
        logging.info('AGOL apply edit results:')
        Completed('add', numAdds, successful['addResults'])
        Completed('update', numUpdates, successful['updateResults'])
        Completed('delete', numDeletes, successful['deleteResults'])
        print('')

    #try all updates that reported error 1019 as adds
    if len(tryAsAdd) > 0:
        logging.info('Retrying {} failed updates as adds.'.format(len(tryAsAdd)))#, 2)
        
        newAdds = [update for update in deltas['updates'] if update['attributes']['globalid'] in tryAsAdd]

        newDeltas = {'adds': newAdds}

        content = ApplyEditsInner(url, layer, token, newDeltas)

        if not content:
            return False

        successful = 0
        
        logging.debug('Checking result of new add attempts...')
        
        for result in content['addResults']:
            if not result['success']:  
                print(result['error'])
                success = False
                failed.append(result['globalId'])
            else:
                successful += 1

        Completed('new add', len(tryAsAdd), successful)
        
    if not success:
        logging.warning('Warning! Not all edits were applied to AGOL successfully!')
        logging.warning('GUIDs of failed edits:')
        logging.warning(failed)
    
    #aquire new server gen
    ready, newServerGen, srid = CheckService(service['serviceUrl'], service['layerId'], token)
    
    return newServerGen



#token = GetToken('https://nps.maps.arcgis.com', 'REDW_Python', 'Benefit4u!')
#Backup(token)
#CheckService('https://services1.arcgis.com/fBc8EJBxQRMcHlei/arcgis/rest/services/REDW_Sync_test_ln/FeatureServer', 0, token)
#serverGens = GetServerGen(base_url, token)
#serverGens = [{'serverGen': 57940165, 'id': 0, 'minServerGen': 57939871}]
#print(serverGens)
#deltas = ExtractChanges(base_url, 0, serverGens, token)
#deltas['updates'] = deltas['adds']
#deltas['adds'] = []
#print(json.dumps(deltas, indent=4))
#print(ApplyEdits(base_url, 0, token, deltas))
