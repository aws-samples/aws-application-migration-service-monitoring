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

import boto3
import botocore.exceptions
import json
import os
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

cw_logs = boto3.client('logs')
sns = boto3.client('sns')

def open_file(file_name):
    """'
    :param file_name: name of file to open
    :return dictionary from JSON file
    """
    try:
        if type(file_name) is str:
            with open(file_name, 'r') as json_data:
                data = json.load(json_data)
            return data
        else:
            raise TypeError('The parameter `file_name` should be a path represented as a string.')
    except FileNotFoundError as err:
        raise FileNotFoundError('The file {} was not found, check the file name passed to the function.'.format(file_name))

def source_server_validation(mgnsourcedetails):
    """
    :param event: event received by the lambda function
    :param sourceserverid: MGN source server id
    :return True | False: return True if the event should be processed
    """
    skip_processing= ['TESTING', 'READY_FOR_CUTOVER', 'CUTTING_OVER', 'CUTOVER', 'DISCONNECTED']
    sourceserverid = mgnsourcedetails['items'][0]['arn']
    logger.info("The current state of source server "+ sourceserverid + " is " + mgnsourcedetails['items'][0]['lifeCycle']['state'])
  
    if mgnsourcedetails['items'][0]['lifeCycle']['state'] not in skip_processing:
        return True
    else:
        return False

def get_event_type(event):
    """
    :param event: event being processed
    :return String (str) Event Type Name
    """
    try:
        if 'detail-type' in event:
            if 'Stalled' in event['detail-type']:
                return 'Stalled'
            elif 'LagDuration' in event['detail']['configuration']['metrics'][0]['metricStat']['metric']['name']:
                return 'LagDuration'
            elif 'ElapsedReplicationDuration' in event['detail']['configuration']['metrics'][0]['metricStat']['metric']['name']:
                return 'ElapsedReplicationDuration'
        elif 'eventName' in event:
            return 'DisconnectFromService'
        else:
            raise ValueError('The Event Received Is Not Parsable')
    except ValueError as err:
        print('A ValueError Occured, please see the details below:')
        print(err)
    except Exception as err:
        print('An Error Occured, please see the details below:')
        print(err)

def get_source_details(account, sourceserverid, region):
    """
    :param account: Account ID where Event Originated
    :type account: String

    :return respone: return the detail of the source server looked up from the target account
    """
    try:
        boto_sts=boto3.client('sts', region_name=region)

        # Get Temporary Credentials for Target Account
        stsresponse = boto_sts.assume_role(
            RoleArn='arn:aws:iam::' + account + ':role/MGN-Monitoring-Generic-Central-Account-Lambda-Role',
            RoleSessionName='mgn-event-session'+account
        )
        credentials=stsresponse['Credentials']
                
        # Create MGN Client with Temporary Credentials from Target Account
        client = boto3.client('mgn',
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
            region_name=region
        )
        
        # Describe MGN source server in Target Account by Source Server ID
        response = client.describe_source_servers(
            filters = {
                    'sourceServerIDs': [sourceserverid]
            }
        )
        return response
    except botocore.exceptions.ClientError as err:
        raise err

def describe_log_stream(log_group, log_stream):
    """
    :param log_group: CloudWatch Log Group
    :param log_stream: CloudWatch Log Stream
    :return response['logStreams'][0] - most recent log stream
    """
    response = cw_logs.describe_log_streams(
            logGroupName=log_group,
            logStreamNamePrefix=log_stream,
        )

    if not len(response['logStreams']) > 0:
        cw_logs.create_log_stream(
            logGroupName=log_group,
            logStreamName=log_stream,
        )
        return {}
    return response['logStreams'][0]


def put_log_events(message, log_stream_name):
    """
    :param message: Event string - put to CloudWatch Log Group
    :type event: String
    :return source_server_id: 
    """
    now = datetime.now()
    curr_date_time = now.strftime("%Y-%m-%dT%H:%M:%S")
    millisec = int((datetime.utcnow() - datetime(1970, 1, 1)).total_seconds() * 1000)

    log_stream_info = describe_log_stream(os.environ.get('EventsCLoudWatchLogGroup'), log_stream_name)
    upload_sequence_token = log_stream_info.get('uploadSequenceToken')

    put_log_params = {
        'logGroupName': os.environ.get('EventsCLoudWatchLogGroup'),
        'logStreamName':log_stream_name,
        'logEvents':[
            {
                'timestamp': millisec,
                'message': message
            },
        ]
    }

    if upload_sequence_token:
        put_log_params['sequenceToken'] = upload_sequence_token

    response = cw_logs.put_log_events(**put_log_params)
    
    return response

def get_server_fqdn(event, mgnsourceserver):
    """
    :param mgnsourceserver: Source server details from Target Account MGN
    :type mgnsourceserver: Dictionary
    :return fqdn: 
    """
    try:
        if 'arn' not in mgnsourceserver:
            server_details = get_source_details(event['account'], mgnsourceserver)
        else:
            mgnsourceserver = parse_source_serverid(mgnsourceserver)
            server_details = get_source_details(event['account'], mgnsourceserver)

        fqdn = server_details['items'][0]['sourceProperties']['identificationHints']['fqdn']
        
        return fqdn
    except TypeError as err:
        raise TypeError('The `event` must be a dict and `mgnsourceserver` must be a string')
    except Exception as err:
        print('An Error Occurred: ' + str(err))
def parse_source_serverid(arn):
    """
    :param event: get the source server ID if it is formatted as an entire ARN
    :type event: Dictionary
    :return source_server_id: 
    """
    sourceserverid = arn.split('/',1)[1] 

    return sourceserverid

def info_log_event(event, log_stream_name):
    """
    :param event: The processed event that will be logged
    :type event: Dictionary
    : type log_group_name: String
    : type log_stream_name: String
    : return : None
    """
    log_str = 'INFO: ' + str(event.get_event_attributes())
    put_log_events(log_str, log_stream_name)

def warn_log_event(event, log_stream_name):
    """
    :param event: The processed event that will be logged
    :type event: Dictionary
    : type log_group_name: String
    : type log_stream_name: String
    : return : None
    """
    log_str = 'WARN: ' + str(event.get_event_attributes())
    put_log_events(log_str, log_stream_name)

def critical_log_event(event, log_stream_name):
    """
    :param event: The processed event that will be logged
    : type event: Dictionary
    : type log_group_name: String
    : type log_stream_name: String
    : return : None
    """

    log_str = 'CRITICAL: ' + str(event.get_event_attributes())
    print(log_str)
    put_log_events(log_str, log_stream_name)

def write_to_cw_logs(event):
    log_stream_name = str(os.environ.get('EventsCLoudWatchLogGroup'))+"-MGN-Events"
    if event.get_event_severity() == 'Critical':
        critical_log_event(event, log_stream_name)
    elif event.get_event_severity() == 'Major':
        warn_log_event(event, log_stream_name)
    else:
        info_log_event(event, log_stream_name)


def format_messages(event):
    """
    :param event: event to be formatted
    : return : message - to be sent via SNS
    """
    if 'Stalled' in event.get_event_type():
        message = '''
            Hello, \n
            The Hostname {} in AWS Account {} in the region {} is experiencing stalled data replication. \n
            This is a {} event which occured on {}.            
        '''.format(event.get_server_fqdn(), event.get_aws_account_id(), event.get_aws_region(), event.get_event_severity(), event.get_time_stamp())
        return message
    elif 'LagDuration' in event.get_event_type():
        message = '''
            Hello, \n
            The Hostname {} in AWS Account {} in the region {} is experiencing lag in replication. \n
            This is a {} event which occured on {}.       
        '''.format(event.get_server_fqdn(), event.get_aws_account_id(), event.get_aws_region(), event.get_event_severity(), event.get_time_stamp())
        return message
    elif 'ElapsedReplicationDuration' in event.get_event_type():
        message = '''
            Hello, \n
            The Hostname {} in AWS Account {} in the region {} has exceeded the replication threshold of 90 days. \n
            This is a {} event which occured on {}. 
        '''.format(event.get_server_fqdn(), event.get_aws_account_id(), event.get_aws_region(), event.get_event_severity(), event.get_time_stamp())
        return message
    elif 'DisconnectFromService' in event.get_event_type():
        message = '''
            Hello, \n
            The Hostname {} in AWS Account {} in the region {} has been disconnected from the AWS MGN service. \n
            This is a {} event which occured on {}. 
        '''.format(event.get_server_fqdn(), event.get_aws_account_id(), event.get_aws_region(), event.get_event_severity(), event.get_time_stamp())
        return message
    else:
        raise RuntimeError('The event provided does not contain a valid event type.')

def publish_event_to_sns_topic(event):
    """
    :param event: event to be formatted and published to SNS
    : return : response (from SNS API call)
    """
    message = format_messages(event)
    response = sns.publish(
        TopicArn=os.environ['EventsSNSTopic'],
        Message=message
    )
    return response