import csv
import os
import json
import sys

import splunk.rest as rest

_LIB_DIR = os.path.dirname(os.path.abspath(__file__))
_BIN_DIR = os.path.dirname(_LIB_DIR)
_APP_DIR = os.path.dirname(_BIN_DIR)
_APPS_DIR = os.path.dirname(_APP_DIR)
if _LIB_DIR not in sys.path:
    sys.path.append(_LIB_DIR)

from AlertManagerLogger import setupLogger
log = setupLogger('csvlookup')

class CsvLookup(object):

    csv_data    = []

    def __init__(self, file_path = '', lookup_name = '', sessionKey = ''):
        # Reset on init to avoid strange caching effects
        self.csv_data = []

        log.debug("file_path: '{}', lookup_name: '{}'".format(file_path, lookup_name))

        if file_path == '':
            if lookup_name == '':
                raise Exception("No file_path or lookup_name specified.")
            else:
                if sessionKey == '':
                    raise Exception("No sessionKey provided, unable to query REST API.")
                else:
                    # Get csv name from API
                    uri = '/servicesNS/nobody/alert_manager/data/transforms/lookups/{}'.format(lookup_name)
                    serverResponse, serverContent = rest.simpleRequest(uri, sessionKey=sessionKey, method='GET', getargs={'output_mode': 'json'})
                    try:
                        lookup = json.loads(serverContent.decode('utf-8'))
                        file_path = os.path.join(_APPS_DIR, lookup["entry"][0]["acl"]["app"], 'lookups', lookup["entry"][0]["content"]["filename"])
                        log.debug("Got file_path={} from REST API for lookup_name={}".format(file_path, lookup_name))
                    except:
                        log.error("Unable to retrieve lookup.")
                        raise Exception("Unable to retrieve lookup.")
        else:
            log.debug("file_path={} is set, don't have to query the API.".format(file_path))

        if not os.path.exists(file_path):
            log.error("Wasn't able to find file_path={}, aborting.".format(file_path))
            raise Exception("File {} not found.".format(file_path))

        else:
            with open(file_path) as fh:
                reader = csv.DictReader(fh)

                for row in reader:
                    self.csv_data.append(row)

    def lookup(self, input_data, output_fields = None):
        match = {}
        for row in self.csv_data:
            if all(item in row.items() for item in input_data.items()):
                match = row
                break

        if output_fields != None:
            for k in match.keys():
                my_match = match.copy()
                if k not in output_fields:
                    del my_match[k]

        return my_match

    def getData(self):
        return self.csv_data
