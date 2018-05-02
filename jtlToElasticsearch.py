# Copyright (C) 2018 Jakub Pustelnik
#
# Script is using python-jtl to read data from jmeter jtl file to calculate test summary data 
# and sends it to elasticsearch. Can be used instead of elasticsearch listener.
#
# jtl file data:
# timeStamp - in milliseconds since 1/1/1970
# elapsed - in milliseconds
# label - sampler label
# responseCode - e.g. 200, 404
# responseMessage - e.g. OK
# threadName
# dataType - e.g. text
# success - true or false
# failureMessage - if any
# bytes - number of bytes in the sample
# sentBytes - number of bytes sent for the sample
# grpThreads - number of active threads in this thread group
# allThreads - total number of active threads in all groups
# URL
# Filename - if Save Response to File was used
# latency - time to first response
# connect - time to establish connection
# encoding
# SampleCount - number of samples (1, unless multiple samples are aggregated)
# ErrorCount - number of errors (0 or 1, unless multiple samples are aggregated)
# Hostname - where the sample was generated
# IdleTime - number of milliseconds of 'Idle' time (normally 0)
# Variables, if specified

from jtl import create_parser
import functools
from elasticsearch import Elasticsearch
import argparse

def jtl_to_json_summary(build_name, passed, filename):
    parser = create_parser(filename)
    samples = 0
    not_ok_resp_code = 0
    successes = 0
    sample_count_sum = 0
    response_time = []

    for sample in parser.itersamples():
        samples += 1
        sample_count_sum += sample.sample_count 

        response_time.append(sample.elapsed_time.total_seconds()*1000)
        try:
            if int(sample.response_code) != 200:
                not_ok_resp_code += 1
        except Exception:
            not_ok_resp_code += 1
        
        if sample.success:
            successes += 1
    
    avg_response_time = functools.reduce(lambda x, y: x + y, response_time) / len(response_time)
    min_response_time = min(response_time)
    max_response_time = max(response_time)

    doc = {
        "samples": samples,
        "successes": successes,
        "invalidRespCode": not_ok_resp_code,
        "sampleCountSum":sample_count_sum,
        "avgRespTime": avg_response_time,
        "minRespTime": min_response_time,
        "maxRespTime": max_response_time,
        "passed": passed,
        "buildName": build_name,
    }
    return doc

def json_to_elasticsearch(json_str, host, port=9200):
    es = Elasticsearch([{'host': host, 'port': port}])
    es.index(body=json_str, index='jmeter', doc_type='jmeter')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Sends jmetter test summary to elasticsearch')
    parser.add_argument('--buildName', type=str)
    parser.add_argument('--passed', type=bool)
    parser.add_argument('--file', type=str)
    parser.add_argument('--elasticsearchHost', type=str)

    args = parser.parse_args()
    json = jtl_to_json_summary(args.buildName, args.passed, args.file)
    print(json)
    json_to_elasticsearch(json, host=args.elasticsearchHost)

