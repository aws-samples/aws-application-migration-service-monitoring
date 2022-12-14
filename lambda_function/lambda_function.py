#########################################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.                    #
# SPDX-License-Identifier: MIT-0                                                        #
#                                                                                       #
# Permission is hereby granted, free of charge, to any person obtaining a copy of this  #
# software and associated documentation files (the "Software"), to deal in the Software #
# without restriction, including without limitation the rights to use, copy, modify,    #
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to    #
# permit persons to whom the Software is furnished to do so.                            #
#                                                                                       #
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,   #
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A         #
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT    #
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION     #
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE        #
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.                                #
#########################################################################################

from events.event_mapping import ProcessedEvent
import utils

def process_event_types(event):
    """
    This function determines the event type recieved and processes calls the correct processing function
    :param : event - the event recieved by the function
    :return : processed_event - a new formatted event extracting details from the event
    """
    try:
        if 'detail-type' in event:
            if 'Stalled' in event['detail-type']:
                processed_event = process_stalled_event(event)
                return processed_event
            elif 'LagDuration' in event['detail']['configuration']['description']:
                processed_event = process_cloudwatch_alarm(event)
                return processed_event
            elif 'ElapsedReplicationDuration' in event['detail']['configuration']['description']:
                processed_event = process_cloudwatch_alarm(event)
                return processed_event
        elif 'eventName' in event:
            processed_event = process_source_disconnect(event)
            return processed_event
        else:
            raise ValueError('The Event Received Is Not Parsable')
    except ValueError as err:
        print(err)
        raise ValueError
    except Exception as err:
        print(err)
        raise Exception

def process_stalled_event(event):
    """
    This function processes data replication stalled events
    :param : event - the event recieved by the function
    :return : processed_event - a new formatted event extracting details from the event
    """
    event_type = event['detail-type']
    source_server_id = utils.parse_source_serverid(event['resources'][0])
    severity_map = utils.open_file('event_severity.json')
    source = utils.get_source_details(event['account'], source_server_id, event['region'])
    fqdn = source['items'][0]['sourceProperties']['identificationHints']['fqdn']
    event_detail = {
        "state": event['detail']['state']
    }
    processed_event = ProcessedEvent(event['account'], event['region'], event_type, event['time'], source_server_id, fqdn, event_detail, severity_map['Stalled'])

    return processed_event

def process_source_disconnect(event):
    """
    This function processes MGN source server disconnection events
    :param : event - the event recieved by the function
    :return : processed_event - a new formatted event extracting details from the event
    """
    event_type = event['eventName']
    source_server_id = event['requestParameters']['sourceServerID']
    severity_map = utils.open_file('event_severity.json')
    fqdn = event['responseElements']['sourceProperties']['identificationHints']['fqdn']
    event_detail = {
        "state": event['detail']['state']
    }
    processed_event = ProcessedEvent(event['account'], event['region'], event_type, event['time'], source_server_id, fqdn, event_detail, severity_map['Disconnect'])
    return processed_event

def process_cloudwatch_alarm(event):
    """
    This function processes cloudwatch alarm events
    :param : event - the event recieved by the function
    :return : processed_event - a new formatted event extracting details from the event
    """
    event_type=event['detail-type']+" : "+event['detail']['configuration']['metrics'][0]['metricStat']['metric']['name']
    source_server_id = event['detail']['configuration']['metrics'][0]['metricStat']['metric']['dimensions']['SourceServerID']
    severity_map = utils.open_file('event_severity.json')
    mgn_source_details = utils.get_source_details(event['account'], source_server_id, event['region'])
    fqdn = mgn_source_details['items'][0]['sourceProperties']['identificationHints']['fqdn']
    event_detail = {
        "alarm_name": event['detail']['alarmName'],
        "resources": event['resources'][0],
        "state": event['detail']['state'],
        "previous_state": event['detail']['previousState']
    }
    processed_event = ProcessedEvent(event['account'], event['region'], event_type, event['time'], source_server_id, fqdn, event_detail, severity_map['LagDuration'])
    return processed_event

def lambda_handler(event, context):
    
    print(event)
    eventtype = utils.get_event_type(event)
    if eventtype == 'Stalled':
        sourcearn = event['resources'][0]
        sourceserverid = utils.parse_source_serverid(sourcearn)
        accountid = event['account']
        region = event['region']
        response = utils.get_source_details(accountid, sourceserverid, region)
        process_event = utils.source_server_validation(response)
    elif eventtype == 'LagDuration':
        sourcearn = event['resources'][0]
        sourceserverid = event['detail']['configuration']['metrics'][0]['metricStat']['metric']['dimensions']['SourceServerID']
        accountid = event['account']
        region = event['region']
        response = utils.get_source_details(accountid, sourceserverid, region)
        process_event = utils.source_server_validation(response)
    elif eventtype == 'ElapsedReplicationDuration':
        sourcearn = event['resources'][0]
        sourceserverid = event['detail']['configuration']['metrics'][0]['metricStat']['metric']['dimensions']['SourceServerID']
        accountid = event['account']
        region = event['region']
        response = utils.get_source_details(accountid, sourceserverid, region)
        process_event = utils.source_server_validation(response)
    elif eventtype == 'DisconnectFromService':
        sourcearn = event['responseElements']['arn']
        sourceserverid = event['requestParameters']['sourceServerID']
        accountid = event['userIdentity']['accountId']
        region = event['awsRegion']
        response = utils.get_source_details(accountid, sourceserverid, region)
        process_event = True
    else:
        raise NotImplementedError('Event recieved does not have a processor implemented.')
    
    if process_event is True:
        processed_event = process_event_types(event)
        utils.write_to_cw_logs(processed_event)
        utils.publish_event_to_sns_topic(processed_event)
        print(processed_event.get_event_attributes())
    else:
        utils.logger.warn(
            '''The event received is from an MGN source server in a Testing, Cutover, or Disconnected state, \n
            therefore this event will not be processed.'''
        )