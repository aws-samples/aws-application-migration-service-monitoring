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

class ProcessedEvent:
    
    def __init__(self, aws_account_id, aws_region, event_type, time_stamp, source_server_id, source_server_fqdn, event_detail, event_severity):
        self.aws_account_id = aws_account_id
        self.aws_region = aws_region
        self.event_type = event_type
        self.time_stamp = time_stamp
        self.source_server_id = source_server_id
        self.source_server_fqdn = source_server_fqdn
        self.event_severity = event_severity
        self.event_detail = event_detail
    
    def set_aws_account_id(self, aws_account_id):
        self.aws_account_id = aws_account_id

    def get_aws_account_id(self):
        return self.aws_account_id
    
    def set_aws_region(self, aws_region):
        self.aws_region = aws_region
    
    def get_aws_region(self):
        return self.aws_region
    
    def set_event_type(self, event_type):
        self.event_type = event_type
    
    def get_event_type(self):
        return self.event_type
    
    def set_time_stamp(self, time_stamp):
        self.time_stamp = time_stamp
    
    def get_time_stamp(self):
        return self.time_stamp

    def set_source_server_id(self, source_server_id):
        self.source_server_id = source_server_id
    
    def get_source_server_id(self):
        return self.source_server_id
    
    def set_server_fqdn(self, source_server_fqdn):
        self.source_server_fqdn = source_server_fqdn
    
    def get_server_fqdn(self):
        return self.source_server_fqdn
    
    def set_event_severity(self, event_severity):
        self.severity = event_severity
    
    def get_event_severity(self):
        return self.event_severity

    def set_event_detail(self, event_detail):
        self.event_detail = event_detail
    
    def get_event_detail(self):
        return self.event_detail

    def set_event_attributes(self, aws_account_id, aws_region, event_type, time_stamp, source_server_id, source_server_fqdn, event_severity, event_detail):
        self.aws_account_id = aws_account_id
        self.aws_region = aws_region
        self.event_type = event_type
        self.time_stamp = time_stamp
        self.source_server_id = source_server_id
        self.source_server_fqdn = source_server_fqdn
        self.severity = event_severity
        self.event_detail = event_detail

    def get_event_attributes(self):
        return {
            "aws_account_id": self.aws_account_id, 
            "aws_region": self.aws_region,
            "event_type": self.event_type,
            "time_stamp": self.time_stamp,
            "source_server_id": self.source_server_id,
            "source_server_fqdn": self.source_server_fqdn,
            "event_severity": self.event_severity,
            "event_detail": self.event_detail
        }



