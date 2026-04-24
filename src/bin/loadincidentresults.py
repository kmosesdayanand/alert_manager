#!/usr/bin/env python
# coding=utf-8

import os
import sys
import json

_BIN_DIR = os.path.dirname(os.path.abspath(__file__))
_LIB_DIR = os.path.join(_BIN_DIR, 'lib')
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)
_SPLUNKLIB_DIR = os.path.join(_BIN_DIR, 'splunklib')
if _SPLUNKLIB_DIR not in sys.path:
    sys.path.insert(0, _SPLUNKLIB_DIR)

import splunklib.client as client
import splunklib.results as results
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators


@Configuration(type='reporting')
class loadincidentresults2(GeneratingCommand):

    incident_id = Option(require=True)

    def generate(self):
        self.logger.debug("Generating %s events" % self.incident_id)

        service = self.service

        try:
            collect_data_results = service.confs['alert_manager']['settings']['collect_data_results']
        except Exception:
            self.logger.error('Setting "collect_data_results" not found in alert_manager.conf')
            yield {'Error': 'Setting "collect_data_results" not found in alert_manager.conf'}
            return

        try:
            index_data_results = service.confs['alert_manager']['settings']['index_data_results']
        except Exception:
            self.logger.error('Setting "index_data_results" not found in alert_manager.conf')
            yield {'Error': 'Setting "index_data_results" not found in alert_manager.conf'}
            return

        if collect_data_results == '1':
            service.namespace['owner'] = "Nobody"
            collection = service.kvstore["incident_results"]

            query = json.dumps({'incident_id': self.incident_id})
            data = collection.data.query(query=query)

            if not data:
                self.logger.warning("No incident_results found for incident_id=%s", self.incident_id)
                return

            for fields in data[0].get("fields", []):
                yield fields

        elif index_data_results == '1' and collect_data_results == '0':
            try:
                index = service.confs['alert_manager']['settings']['index']
            except Exception:
                self.logger.error('Setting "index" not found in alert_manager.conf')
                yield {'Error': 'Setting "index" not found in alert_manager.conf'}
                return

            service.namespace['owner'] = "Nobody"
            collection = service.kvstore["incidents"]

            query = json.dumps({'incident_id': self.incident_id})
            data = collection.data.query(query=query)

            if not data:
                self.logger.warning("No incidents found for incident_id=%s", self.incident_id)
                return

            earliest_time = data[0].get("alert_time")

            kwargs_oneshot = {"earliest_time": earliest_time, "latest_time": "now"}
            searchquery_oneshot = "search index={} sourcetype=alert_data_results incident_id={} |dedup incident_id".format(
                index, self.incident_id)
            oneshotsearch_results = service.jobs.oneshot(searchquery_oneshot, **kwargs_oneshot)
            reader = results.ResultsReader(oneshotsearch_results)

            events = []
            for result in reader:
                for k, v in result.items():
                    if k == '_raw':
                        events.append(json.loads(v))

            for event in events:
                for fields in event.get("fields", []):
                    yield fields

        else:
            yield {'Error': 'Indexing/KV Store Collection of Results is not enabled. Please enable under Global Settings.'}


dispatch(loadincidentresults2, sys.argv, sys.stdin, sys.stdout, __name__)
