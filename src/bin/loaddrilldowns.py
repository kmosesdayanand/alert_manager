#!/usr/bin/env python
# coding=utf-8

import os
import sys
import json
import re
import urllib.parse
from string import Template as StringTemplate

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
class loaddrilldowns(GeneratingCommand):

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

        incident_data = {}

        if collect_data_results == '1':
            service.namespace['owner'] = "Nobody"
            collection = service.kvstore["incident_results"]

            query = json.dumps({'incident_id': self.incident_id})
            data = collection.data.query(query=query)

            if data:
                fields_list = data[0].get("fields", [])
                if fields_list:
                    incident_data = fields_list[0]
                    for k, v in incident_data.items():
                        incident_data[k] = urllib.parse.quote(str(v))

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
                fields_list = event.get("fields", [])
                if fields_list:
                    incident_data = fields_list[0]

            for k, v in incident_data.items():
                incident_data[k] = urllib.parse.quote(str(v))

        # Get Incident
        collection = service.kvstore["incidents"]
        query = json.dumps({'incident_id': self.incident_id})
        data = collection.data.query(query=query)

        if not data:
            self.logger.warning("No incident found for incident_id=%s", self.incident_id)
            return

        alert = data[0].get('alert')

        # Get Incident Settings
        collection = service.kvstore["incident_settings"]
        query = json.dumps({'alert': alert})
        data = collection.data.query(query=query)

        if not data:
            self.logger.warning("No incident_settings found for alert=%s", alert)
            return

        drilldown_references = data[0].get('drilldowns', '')

        if not drilldown_references:
            return

        drilldown_references = drilldown_references.split()

        query_prefix = '{ "$or": [ '
        for drilldown_reference in drilldown_references:
            query_prefix += '{ "name": "' + drilldown_reference + '" } '
        query_prefix = query_prefix + '] }'

        collection = service.kvstore["drilldown_actions"]
        query = query_prefix.replace("} {", "}, {")
        data = collection.data.query(query=query)

        class FieldTemplate(StringTemplate):
            idpattern = r'[a-zA-Z][_a-zA-Z0-9.]*'

        for drilldown_action in data:
            url = drilldown_action.get("url", "")
            label = drilldown_action.get("label", "")

            url = re.sub(r'(?<=\w)\$', '', url)
            url = FieldTemplate(url).safe_substitute(incident_data)

            yield {"label": label, "url": url}


dispatch(loaddrilldowns, sys.argv, sys.stdin, sys.stdout, __name__)
