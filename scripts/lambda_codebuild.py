"""
This function kicks off a code build job
"""
from __future__ import print_function
import traceback
import httplib
import urlparse
import json
import botocore
import boto3
import logging

def log_config(event, loglevel=None, botolevel=None):
    if 'ResourceProperties' in event.keys():
        if 'loglevel' in event['ResourceProperties'] and not loglevel:
            loglevel = event['ResourceProperties']['loglevel']
        if 'botolevel' in event['ResourceProperties'] and not botolevel:
            botolevel = event['ResourceProperties']['botolevel']
    if not loglevel:
        loglevel = 'warning'
    if not botolevel:
        botolevel = 'error'
    # Set log verbosity levels
    loglevel = getattr(logging, loglevel.upper(), 20)
    botolevel = getattr(logging, botolevel.upper(), 40)
    mainlogger = logging.getLogger()
    mainlogger.setLevel(loglevel)
    logging.getLogger('boto3').setLevel(botolevel)
    logging.getLogger('botocore').setLevel(botolevel)
    # Set log message format
    logfmt = '[%(requestid)s][%(asctime)s][%(levelname)s] %(message)s \n'
    mainlogger.handlers[0].setFormatter(logging.Formatter(logfmt))
    return logging.LoggerAdapter(mainlogger, {'requestid': event['RequestId']})

# initialise logger
logger = log_config({"RequestId": "CONTAINER_INIT"})
logger.info('Logging configured')
# set global to track init failures
init_failed = False

try:
    # Place initialization code here
    logger.info("Container initialization completed")
except Exception as e:
    logger.error(e, exc_info=True)
    init_failed = e

def lambda_handler(event, context):
    """
    Main Lambda Handling function
    """
    global logger
    global account_id
    logger = log_config(event)
    logger.debug(event)

    # Setup base response
    response = get_response_dict(event)

    account_id = context.invoked_function_arn.split(":")[4]
    print(account_id)


    # CREATE UPDATE (want to avoid rebuilds unless something changed)
    if event['RequestType'] in ("Create", "Update"):
        try:
            logger.debug("Kicking off Build")
            execute_build(event)
        except Exception, exce:
            logger.error("Build threw exception" + exce.message)
            # Signal back that we failed
            return send_response(event, get_response_dict(event), "FAILED", exce.message)
        else: 
            # We want codebuild to send the signal
            logger.info("Build Kicked off ok CodeBuild should signal back")
            return
    elif event['RequestType'] == "Delete":
        try:
            # DELETE (Let CFN delete the artifacts etc as per normal)
            # Cleanup the images in the repository
            logger.debug("Cleaning up repositories and images")
            cleanup_images(event)
        except Exception,exce:
            # Signal back that we failed
            logger.error("exception: " + exce.message)
            response['PhysicalResourceId'] = "1233244324"
            return send_response(event, response, "FAILED", exce.message)
        
        # signal success to CFN
        logger.info("Cleanup complete signal back")
        response['PhysicalResourceId'] = "1233244324"
        return send_response(event, response)
    else: # Invalid RequestType
        logger.error("Invalid request type send error signal to cfn: " + event['RequestType'] + " (expecting: Create, Update, Delete )" )
        return send_response(event, response, "FAILED", "Invalid RequestType: Create, Update, Delete")


def cleanup_images(event):
    """
    loop over and delete images in each repo
    """
    properties = event['ResourceProperties']
    for repository in ['AWXTaskRegistry','AWXWebRegistry','RabbitMQRegistry','MemcachedRegistry', 'SidecarRegistry']:
        logger.debug("Cleaning Up: " + repository)
        logger.debug("Trying to cleanup: " + properties[repository])
        cleanup_images_repo(properties[repository])


def cleanup_images_repo(repository):
    """
    Delete Container images
    """
    ecr_client = boto3.client('ecr')
    response = ecr_client.describe_images(
        registryId=globals()['account_id'],
        repositoryName=repository
    )
    
    imageIds = []
    for imageDetail in response['imageDetails']:
        imageIds.append(
            {
                'imageDigest': imageDetail['imageDigest'],
            }
        )

    if len(imageIds):
        # delete images
        logger.debug("Deleting images")
        response = ecr_client.batch_delete_image(
            registryId=globals()['account_id'],
            repositoryName=repository,
            imageIds=imageIds
        )


def execute_build(event):
    """
    Kickoff CodeBuild Project
    """
    build = boto3.client('codebuild')
    project_name = event["ResourceProperties"]["BuildProjectName"]
    signal_url = event["ResponseURL"]
    stack_id = event["StackId"]
    request_id = event["RequestId"]
    logical_resource_id = event["LogicalResourceId"]
    url = urlparse.urlparse(event['ResponseURL'])
    response = build.start_build(
        projectName = project_name,
        environmentVariablesOverride = [
            { 'name' : 'url_path',                'value' : url.path },
            { 'name' : 'url_query',               'value' : url.query },
            { 'name' : 'cfn_signal_url',          'value' : signal_url },
            { 'name' : 'cfn_stack_id',            'value' : stack_id },
            { 'name' : 'cfn_request_id',          'value' : request_id },
            { 'name' : 'cfn_logical_resource_id', 'value' : logical_resource_id }
        ]
    )
    return response

def get_response_dict(event):
    """
    Setup Response object for CFN Signal
    """
    response = {
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId'],
        'Status': 'SUCCESS'
    }
    # print json.dumps(response)
    return response

def send_response(event, response, status=None, reason=None):
    if status is not None:
        response['Status'] = status

    if reason is not None:
        response['Reason'] = reason

    if 'ResponseURL' in event and event['ResponseURL']:
        url = urlparse.urlparse(event['ResponseURL'])
        body = json.dumps(response)
        https = httplib.HTTPSConnection(url.hostname)
        https.request('PUT', url.path + '?' + url.query, body)
        logger.info("Sent CFN Response")

    return response