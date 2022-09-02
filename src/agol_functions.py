import json
import requests
import time

from src.ui_functions import Completed, logging
import src.ui_functions as ui
from src.error import HTTPError, AGOLError, AGOLServiceError, JSONDecodeError, Error, Cancelled
from src.misc_functions import CleanJson


def ParseJSON(jsn):                      # json.loads with error catching
    try:
        return json.loads(jsn)
    except ValueError:                   # catch json decode error and print response for debugging hellp
        logging.error('Error parsing JSON!')
        logging.error('JSON: {}'.format(jsn))
        raise JSONDecodeError('Error parsing JSON!')


def CreateUrl(base_url, params):
    base_url += '?'

    for k, v in params.items():
        base_url += '{}={}&'.format(k, v)

    base_url += 'f=json'

    logging.debug('Created URL: {}'.format(base_url))  # , 3)

    return base_url

class agol:
    def __init__(self, cfg, service=None):
        self.token = None
        self.cfg = cfg
        self.is_valid = False
        self.serviceId = None
        self.srid = None
        self.to_srid = None

        if service is not None:
            if not service['type'] == 'AGOL':
                return False

            self.url = service['serviceUrl']
            self.layer = service['layerId']
            self.servergen = service['servergen']
            self.nickname = service['nickname']

        else: # service is none, create new service
            self.servergen = None
            self.nickname = None

            print('The URL for a AGOL hosted-feature-layer sublayer can be found at nps.maps.arcgis.com.\n'
                  'Browse to the hosted feature layer (the URL to the service will end with "FeatureServer").\n'
                  'Then click on one of the layers on the main page. At the bottom right, the URL for the\n'
                  'sub layer will be displayed. The hosted-feature-layer sublayer URL in the lower right\n'
                  'will end with "Feature Server/x, where x is the sub layer ID. A list of URLs for common\n'
                  'layers can be found at "https://tinyurl.com/48kj9ccf".\n')

            self.url, self.layer = ui.GetAgolURL()

            if not self.url:
                raise Cancelled('')

    def ToDict(self):
        service = {'type': 'AGOL',
                   'serviceUrl': self.url,
                   'layerId': self.layer,
                   'servergen': self.servergen,
                   'nickname': self.nickname}

        return service

    def __str__(self):
        out = ('  Type: AGOL\n'
               '  Nickname: {}\n'
               '  AGOL URL: {}\n'
               '  AGOL layer: {}\n'.format(self.nickname, self.url, self.layer))

        return out

    def GetToken(self):
        # returns token for use with further requests

        logging.debug('Getting AGOL token...')#, 2)

        url = self.cfg.AGOL_url + '/sharing/generateToken'
        payload = {'username': self.cfg.AGOL_username, 'password': self.cfg.AGOL_password, 'referer': 'www.arcgis.com', 'f': 'json'}

        r = requests.post(url, data=payload)

        response = ParseJSON(r.content)

        if 'token' not in response.keys():
            logging.error('No token returned!')
            logging.error(response)
            raise AGOLError('Failed to acquire token.', url)

        logging.debug('Token acquired.')

        self.token = response['token']

    def Connect(self):
        if self.token is None:
            self.GetToken()

    def ApiCall(self, url, data): #, serverGen):
        # performs async rest api call
        if not url:
            url = self.url

        logging.debug('Sending AGOL API request...')

        url = CreateUrl(url, data)
        response = requests.post(url)

        url = ParseJSON(response.content)["statusUrl"]
        data  = {'token': self.token}
        url = CreateUrl(url, data)

        while True:
            time.sleep(3)

            logging.debug('Checking status URL...')
            response = requests.post(url)
            content = ParseJSON(response.content)

            logging.debug('Status: {}'.format(content['status']))

            if (content["status"] != 'Pending'):
                break

        if content['status'] == 'Failed':
            raise AGOLServiceError(content, url)

        else:
            logging.debug('Getting result...')

            url = content['resultUrl']
            url = CreateUrl(url, data)

            response = requests.post(url)
            content = ParseJSON(response.content)
            # print(json.dumps(content, indent=4))
            logging.debug('API response received')

        return content

    def ValidateService(self): #, serverGen):
        # returns None if issue with service
        # returns False if service is missing capabilities
        # returns True, serverGen if service is set up correctly

        self.Connect()

        logging.info('Validating feature service...')

        logging.debug('Checking AGOL service capabilities...')#, 1)
        data = {'token': self.token, 'returnUpdates': True}
        url = CreateUrl(self.url, data)
        response = requests.post(url)

        if response.status_code != 200:
            # raise HTTPError("HTTP error while checking AGOL service!", url, response.status_code)
            logging.error('HTTP Error while checking AGOL service! Check URL.')
            logging.debug('URL: {}'.format(url))
            logging.debug('Status Code: {}'.format(response.status_code))
            return False

        content = ParseJSON(response.content)
        keys = content.keys()

        if 'capabilities' not in keys:       # check if service returned capabilities
            if 'error' in keys:              # check if service returned an error
                raise AGOLServiceError(content, url)
            else:                                      # raise generic AGOL Error
                raise(AGOLError('AGOL Service did not respond with "capabilities!"', url))

        capabilities = content['capabilities']
        capabilities = capabilities.lower()

        required = ['update', 'changetracking', 'create', 'delete', 'update', 'editing']  # cabilitities we want

        missing = set(required) - set(capabilities.split(','))   # check that service has all required capabilities

        if len(missing) > 0:                 # if any capabilities missing, raise exception
            missing = ','.join(missing)
            logging.error('Missing capability(s): {}'.format(missing))
            return False

        try:
            serverGens = content["changeTrackingInfo"]['layerServerGens']
        except:
            logging.error('Error extracting server gen from AGOL! URL: {}'.format(url))
            raise

        serverGen = [g for g in serverGens if g['id'] == self.layer]

        try:
            serverGen = serverGen[0]
        except:
            # raise AGOLError('Layer {} does not exist'.format(self.layer), url)
            logging.error('Layer {} does not exist'.format(self.layer))
            return False

        try:
            srid = content['spatialReference']['wkid']
        except:
            logging.error('Error extracting SRID from AGOL! URL: {}'.format(url))
            raise

        try:
            serviceId = content['serviceItemId']
        except NameError:
            logging.error('Unable to acquire service ID!')
            raise

        logging.info('Feature service is valid.')

        self.is_valid = True
        self.serviceId = serviceId
        self.srid = srid
        return serverGen

    def GetServergen(self):
        return self.ValidateService()

    def UpdateServergen(self, servergen=None):
        if not servergen:
            servergen = self.GetServergen()

        self.servergen = servergen

    def Backup(self, sync_num):
        self.Connect()
        if not self.ValidateService():
            return

        logging.info('Backing up feature service...')

        serverGen = self.ValidateService()

        url = '{}/sharing/rest/content/users/{}/export'.format(self.cfg.AGOL_url, self.cfg.AGOL_username)
        data = {'token': self.token,
                'itemId': self.serviceId,
                'exportFormat': 'File Geodatabase',
                'exportParameters': {'layers':[{'id':self.layer}]}}

        url = CreateUrl(url, data)

        response = requests.post(url)
        content = ParseJSON(response.content)

        try:
            exportId = content['exportItemId']
        except NameError:
            logging.error('Export failed!')
            return

        exportUrl = '{}/home/item.html?id={}'.format(self.cfg.AGOL_url, exportId)

        logging.info('Backup successful.')
        logging.info('Exported backup can be found in the content folder for {}, or at the following URL:'.format(self.cfg.AGOL_username))
        logging.info(exportUrl)

    def ExtractChanges(self):
        # extracts changes since specified serverGen and returns them as an object

        # aquire token
        self.GetToken()

        # check service and acquire data
        # now done in sync.run()
        # newServerGen = self.ValidateService()

        data = {'token': self.token,
                'layers': [self.layer],
                'returnInserts': 'true',
                'returnUpdates': 'true',
                'returnDeletes': 'true',
                'layerServerGens': json.dumps([self.servergen]),
                'dataFormat': 'json'}

        if self.to_srid is not None:
            data['outSR'] = self.to_srid
            srid = self.to_srid
        else:
            srid = self.srid

        url = self.url + '/extractChanges'
        response = self.ApiCall(url, data)

        try:
            deltas = response['edits'][0]['features']
        except AttributeError:
            raise AGOLError('Unexpected response from AGOL!\n\nResponse:\n{}\n'.format(response), url)

        deltas = CleanJson(deltas, srid)

        logging.info('Extracted AGOL changes successfully.')

        return deltas

    def ApplyEditsInner(self, url, layer, deltas):

        logging.debug('Sending AGOL apply edits API request...')

        deltas['id'] = layer

        data = {'token': self.token,
                'edits': json.dumps([deltas]),
                'useGlobalIds': 'true'}

        url += '/applyEdits?f=json'

        # url = CreateUrl(url, data)

        logging.debug('URL: {}'.format(url))  # , 3)

        response = requests.post(url, data=data)  # , json={'edits': deltas})

        if(response.status_code != 200):
            raise(HTTPError('Error while applying edits!', url, response.status_code))

        content = ParseJSON(response.content)
        content = content[0]

        if 'error' in content.keys():
            raise AGOLServiceError(content, url)
            # print('Error: {}\n{}'.format(json.dumps(content['error'], indent=4)))
            # return False

        return content

    def ApplyEdits(self, deltas):
        # applies edits to service, returns success boolean

        if self.token is None:
            self.GetToken()
            self.ValidateService()

        # if backup:
        #    Backup(cfg.AGOL_url, cfg.AGOL_username, serviceId, token, layer)

        # if not agol.ApplyEdits(service['serviceUrl'], service['layerId'], token, deltas):
        #    return Fals

        # calculate numbers of adds
        numAdds = len(deltas['adds'])
        numUpdates = len(deltas['updates'])
        numDeletes = len(deltas['deleteIds'])

        # rename deleteIds to deletes (AGOL syntax)
        deltas['deletes'] = deltas.pop('deleteIds')

        # apply edits
        content = self.ApplyEditsInner(self.url, self.layer, deltas)

        success = True
        tryAsAdd = []

        successful = {'addResults': 0, 'updateResults': 0, 'deleteResults': 0}
        failed = []

        logging.debug('Checking results of apply edits...')

        for results in ['addResults', 'updateResults', 'deleteResults']:
            if results in content.keys():
                for result in content[results]:
                    if not result['success']:
                        # check for updates that should have been adds
                        if (results == 'updateResults') and (result['error']['code'] == 1019):
                            # print('trying as add')
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

        # try all updates that reported error 1019 as adds
        if len(tryAsAdd) > 0:
            logging.info('Retrying {} failed updates as adds.'.format(len(tryAsAdd)))#, 2)

            newAdds = [update for update in deltas['updates'] if update['attributes']['globalid'] in tryAsAdd]
            newDeltas = {'adds': newAdds}

            content = self.ApplyEditsInner(self.url, self.layer, newDeltas)
            if not content:
                return False

            logging.debug('Checking result of new add attempts...')

            successful = 0
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

        # acquire new server gen
        newServerGen = self.GetServergen()

        return newServerGen


