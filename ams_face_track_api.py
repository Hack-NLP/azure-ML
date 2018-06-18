
# coding: utf-8

# In[ ]:

#API call script for Face track in Video 
__author__ = 'Mohan Babu'

import os
import json
import time
import sys
import urllib
import datetime
import adal
import requests
from azure.storage.blob import BlockBlobService
from azure.storage.blob import ContentSettings

#public variables
VIDEO_PATH    = 'input_video_path'
OUTPUT_FOLDER = 'results_output_path'
REQUEST_BODY  = './emotion.json'
CONFIG_FILE   = './config.json'

#AMS Endpoints...
ams_auth_endpoint = 'https://login.microsoftonline.com/'
ams_rest_endpoint = 'REST_API_endpoint'

# public defaults for authentication and resource endpoints
AZURE_RESOURCE_ENDPOINT = 'Resource_endpoint'
PROCESSOR_NAME          = 'Azure Media Face Detector'

# AMS Headers
json_only_acceptformat = 'application/json'
json_acceptformat      = 'application/json;odata=verbose'
xml_acceptformat       = 'application/atom+xml'
xmsversion             = '2.19'
charset                = 'UTF-8'



def uploadCallback(current, total):
    if (current != None):
        print('{0:2,f}/{1:2,.0f} MB'.format(current,total/1024/1024))
        
def translate_job_state(code):
    '''AUX Function to translate the (numeric) state of a Job.

    Args:
        nr (int): A valid number to translate.

    Returns:
        HTTP response. JSON body.
    '''
    code_description = ""
    if code == "0":
        code_description = "Queued"
    if code == "1":
        code_description = "Scheduled"
    if code == "2":
        code_description = "Processing"
    if code == "3":
        code_description = "Finished"
    if code == "4":
        code_description = "Error"
    if code == "5":
        code_description = "Canceled"
    if code == "6":
        code_description = "Canceling"

    return code_description

def get_url(access_token, endpoint=ams_rest_endpoint, flag=True):
    return do_ams_get_url(endpoint, access_token, flag)

def do_ams_get_url(endpoint, access_token, flag=True):
    '''Do an AMS GET request to retrieve the Final AMS Endpoint and return JSON.
    Args:
        endpoint (str): Azure Media Services Initial Endpoint.
        access_token (str): A valid Azure authentication token.
        flag  (str): A Flag to follow the redirect or not.

    Returns:
        HTTP response. JSON body.
    '''
    headers = {"Content-Type": json_acceptformat,
               "Accept": json_acceptformat,
               "Accept-Charset" : charset,
               "Authorization": "Bearer " + access_token,
               "x-ms-version" : xmsversion}
    body = ''
    response = requests.get(endpoint, headers=headers, allow_redirects=flag)
    if flag:
        if response.status_code == 301:
            response = requests.get(response.headers['location'], data=body, headers=headers)
    return response

def get_access_token(tenant_id, application_id, application_secret):
    '''get an Azure access token using the adal library.

    Args:
        tenant_id (str): Tenant id of the user's account.
        application_id (str): Application id of a Service Principal account.
        application_secret (str): Application secret (password) of the Service Principal account.

    Returns:
        An Azure authentication token string.
    '''
    context = adal.AuthenticationContext(ams_auth_endpoint + tenant_id, api_version=None)
    token_response = context.acquire_token_with_client_credentials(AZURE_RESOURCE_ENDPOINT, application_id, application_secret)
    return token_response.get('accessToken')

def get_access_token_with_rest_end(tenant_id, application_id, account_key):
    # Get the access token...
    access_token = get_access_token(tenant_id, application_id, account_key)
    
    # Get AMS redirected url
    response = get_url(access_token)
    if (response.status_code == 200):
        ams_redirected_rest_endpoint = str(response.url)
    else:
        print("GET Status: " + str(response.status_code) + " - Getting Redirected URL ERROR." + str(response.content))
        exit(1)
    return access_token, ams_redirected_rest_endpoint

def do_ams_post(endpoint, path, body, access_token, rformat="json"):
    '''Do a AMS HTTP POST request and return JSON.
    Args:
        endpoint (str): Azure Media Services Initial Endpoint.
        path (str): Azure Media Services Endpoint Path.
        body  (str): Azure Media Services Content Body.
        access_token (str): A valid Azure authentication token.
        rformat (str): A required JSON Accept Format.
        ds_min_version (str): A required DS MIN Version.

    Returns:
        HTTP response. JSON body.
    '''
    content_acceptformat = json_acceptformat
    acceptformat = json_acceptformat
    if rformat == "json_only":
        content_acceptformat = json_only_acceptformat
    if rformat == "xml":
        content_acceptformat = xml_acceptformat
        acceptformat = xml_acceptformat + ",application/xml"
    headers = {"Content-Type": content_acceptformat,
               "Accept": acceptformat,
               "Accept-Charset" : charset,
               "Authorization": "Bearer " + access_token,
               "x-ms-version" : xmsversion}
    response = requests.post(endpoint, data=body, headers=headers, allow_redirects=False)
    # AMS response to the first call can be a redirect,
    # so we handle it here to make it transparent for the caller...
    if response.status_code == 301:
        redirected_url = ''.join([response.headers['location'], path])
        response = requests.post(redirected_url, data=body, headers=headers)
    return response

def do_ams_patch(endpoint, path, body, access_token):
    '''Do a AMS PATCH request and return JSON.
    Args:
        endpoint (str): Azure Media Services Initial Endpoint.
        path (str): Azure Media Services Endpoint Path.
        body  (str): Azure Media Services Content Body.
        access_token (str): A valid Azure authentication token.

    Returns:
        HTTP response. JSON body.
    '''
    headers = {"Content-Type": json_acceptformat,
               "Accept": json_acceptformat,
               "Accept-Charset" : charset,
               "Authorization": "Bearer " + access_token,
               "x-ms-version" : xmsversion}
    response = requests.patch(endpoint, data=body, headers=headers, allow_redirects=False)
    # AMS response to the first call can be a redirect,
    # so we handle it here to make it transparent for the caller...
    if response.status_code == 301:
        redirected_url = ''.join([response.headers['location'], path])
        response = requests.patch(redirected_url, data=body, headers=headers)
    return response

def do_ams_delete(endpoint, path, access_token):
    '''Do a AMS DELETE request and return JSON.
    Args:
        endpoint (str): Azure Media Services Initial Endpoint.
        path (str): Azure Media Services Endpoint Path.
        access_token (str): A valid Azure authentication token.

    Returns:
        HTTP response. JSON body.
    '''
    headers = {"Accept": json_acceptformat,
               "Accept-Charset" : charset,
               "Authorization": 'Bearer ' + access_token,
               "x-ms-version" : xmsversion}
    response = requests.delete(endpoint, headers=headers, allow_redirects=False)
    # AMS response to the first call can be a redirect,
    # so we handle it here to make it transparent for the caller...
    if response.status_code == 301:
        redirected_url = ''.join([response.headers['location'], path])
        response = requests.delete(redirected_url, headers=headers)
    return response

def do_ams_get(endpoint, path, access_token):
    '''Do a AMS HTTP GET request and return JSON.
    Args:
        endpoint (str): Azure Media Services Initial Endpoint.
        path (str): Azure Media Services Endpoint Path.
        access_token (str): A valid Azure authentication token.

    Returns:
        HTTP response. JSON body.
    '''
    headers = {"Content-Type": json_acceptformat,
               "Accept": json_acceptformat,
               "Accept-Charset" : charset,
               "Authorization": "Bearer " + access_token,
               "x-ms-version" : xmsversion}
    body = ''
    response = requests.get(endpoint, headers=headers, allow_redirects=False)
    # AMS response to the first call can be a redirect,
    # so we handle it here to make it transparent for the caller...
    if response.status_code == 301:
        redirected_url = ''.join([response.headers['location'], path])
        response = requests.get(redirected_url, data=body, headers=headers)
    return response

def do_ams_get_url(endpoint, access_token, flag=True):
    '''Do an AMS GET request to retrieve the Final AMS Endpoint and return JSON.
    Args:
        endpoint (str): Azure Media Services Initial Endpoint.
        access_token (str): A valid Azure authentication token.
        flag  (str): A Flag to follow the redirect or not.

    Returns:
        HTTP response. JSON body.
    '''
    headers = {"Content-Type": json_acceptformat,
               "Accept": json_acceptformat,
               "Accept-Charset" : charset,
               "Authorization": "Bearer " + access_token,
               "x-ms-version" : xmsversion}
    body = ''
    response = requests.get(endpoint, headers=headers, allow_redirects=flag)
    if flag:
        if response.status_code == 301:
            response = requests.get(response.headers['location'], data=body, headers=headers)
    return response

def get_url(access_token, endpoint=ams_rest_endpoint, flag=True):
    '''Get Media Services Final Endpoint URL.
    Args:
        access_token (str): A valid Azure authentication token.
        endpoint (str): Azure Media Services Initial Endpoint.
        flag (bol): flag.

    Returns:
        HTTP response. JSON body.
    '''
    return do_ams_get_url(endpoint, access_token, flag)

def encode_mezzanine_asset(access_token, processor_id, asset_id, output_assetname, json_profile):
    '''Get Media Service Encode Mezanine Asset.

    Args:
        access_token (str): A valid Azure authentication token.
        processor_id (str): A Media Service Processor ID.
        asset_id (str): A Media Service Asset ID.
        output_assetname (str): A Media Service Asset Name.
        json_profile (str): A Media Service JSON Profile.

    Returns:
        HTTP response. JSON body.
    '''
    path = '/Jobs'
    endpoint = ''.join([ams_rest_endpoint, path])
    assets_path = ''.join(["/Assets", "('", asset_id, "')"])
    assets_path_encoded = urllib.parse.quote(assets_path, safe='')
    endpoint_assets = ''.join([ams_rest_endpoint, assets_path_encoded])
    body = '{"Name":"' + output_assetname + '","InputMediaAssets":[{"__metadata":{"uri":"' + endpoint_assets + '"}}],"Tasks":[{"Configuration":\'' + json_profile + '\',"MediaProcessorId":"' + \
           processor_id + '","TaskBody":"<?xml version=\\"1.0\\" encoding=\\"utf-16\\"?><taskBody><inputAsset>JobInputAsset(0)</inputAsset><outputAsset assetCreationOptions=\\"0\\" assetName=\\"' \
           + output_assetname + '\\">JobOutputAsset(0)</outputAsset></taskBody>"}]}'
    return do_ams_post(endpoint, path, body, access_token)

def create_media_asset(access_token, name, options="0"):
    '''Create Media Service Asset.

    Args:
        access_token (str): A valid Azure authentication token.
        name (str): Media Service Asset Name.
        options (str): Media Service Options.

    Returns:
        HTTP response. JSON body.
    '''
    path = '/Assets'
    endpoint = ''.join([ams_rest_endpoint, path])
    body = '{"Name": "' + name + '", "Options": "' + str(options) + '"}'
    return do_ams_post(endpoint, path, body, access_token)

def create_media_assetfile(access_token, parent_asset_id, name, is_primary="false", is_encrypted="false", encryption_scheme="None", encryptionkey_id="None"):
    '''Create Media Service Asset File.

    Args:
        access_token (str): A valid Azure authentication token.
        parent_asset_id (str): Media Service Parent Asset ID.
        name (str): Media Service Asset Name.
        is_primary (str): Media Service Primary Flag.
        is_encrypted (str): Media Service Encryption Flag.
        encryption_scheme (str): Media Service Encryption Scheme.
        encryptionkey_id (str): Media Service Encryption Key ID.

    Returns:
        HTTP response. JSON body.
    '''
    path = '/Files'
    endpoint = ''.join([ams_rest_endpoint, path])
    if encryption_scheme == "StorageEncryption":
        body = '{             "IsEncrypted": "' + is_encrypted + '",             "EncryptionScheme": "' + encryption_scheme + '",             "EncryptionVersion": "' + "1.0" + '",             "EncryptionKeyId": "' + encryptionkey_id + '",             "IsPrimary": "' + is_primary + '",             "MimeType": "video/mp4",             "Name": "' + name + '",             "ParentAssetId": "' + parent_asset_id + '"         }'
    else:
        body = '{             "IsPrimary": "' + is_primary + '",             "MimeType": "video/mp4",             "Name": "' + name + '",             "ParentAssetId": "' + parent_asset_id + '"         }'
    return do_ams_post(endpoint, path, body, access_token)

def create_asset_accesspolicy(access_token, name, duration, permission="1"):
    '''Create Media Service Asset Access Policy.

    Args:
        access_token (str): A valid Azure authentication token.
        name (str): A Media Service Asset Access Policy Name.
        duration (str): A Media Service duration.
        permission (str): A Media Service permission.

    Returns:
        HTTP response. JSON body.
    '''
    path = '/AccessPolicies'
    endpoint = ''.join([ams_rest_endpoint, path])
    body = '{"Name": "' + str(name) + '", "DurationInMinutes": "' + duration + '","Permissions": "' + permission + '"     }'
    return do_ams_post(endpoint, path, body, access_token)

def create_sas_locator(access_token, asset_id, accesspolicy_id):
    '''Create Media Service SAS Locator.

    Args:
        access_token (str): A valid Azure authentication token.
        asset_id (str): Media Service Asset ID.
        accesspolicy_id (str): Media Service Access Policy ID.

    Returns:
        HTTP response. JSON body.
    '''
    path = '/Locators'
    endpoint = ''.join([ams_rest_endpoint, path])
    body = '{         "AccessPolicyId":"' + accesspolicy_id + '",         "AssetId":"' + asset_id + '",         "Type":1     }'
    return do_ams_post(endpoint, path, body, access_token)

def update_media_assetfile(access_token, parent_asset_id, asset_id, content_length, name):
    '''Update Media Service Asset File.

    Args:
        access_token (str): A valid Azure authentication token.
        parent_asset_id (str): A Media Service Asset Parent Asset ID.
        asset_id (str): A Media Service Asset Asset ID.
        content_length (str): A Media Service Asset Content Length.
        name (str): A Media Service Asset name.

    Returns:
        HTTP response. JSON body.
    '''
    path = '/Files'
    full_path = ''.join([path, "('", asset_id, "')"])
    full_path_encoded = urllib.parse.quote(full_path, safe='')
    endpoint = ''.join([ams_rest_endpoint, full_path_encoded])
    body = '{         "ContentFileSize": "' + str(content_length) + '",         "Id": "' + asset_id + '",         "MimeType": "video/mp4",         "Name": "' + name + '",         "ParentAssetId": "' + parent_asset_id + '"     }'
    return do_ams_patch(endpoint, full_path_encoded, body, access_token)

def delete_sas_locator(access_token, oid):
    '''Delete Media Service SAS Locator.

    Args:
        access_token (str): A valid Azure authentication token.
        oid (str): Media Service SAS Locator OID.

    Returns:
        HTTP response. JSON body.
    '''
    path = '/Locators'
    return helper_delete(access_token, oid, path)

def delete_asset_accesspolicy(access_token, oid):
    '''Delete Media Service Asset Access Policy.

    Args:
        access_token (str): A valid Azure authentication token.
        oid (str): Media Service Asset Access Policy OID.

    Returns:
        HTTP response. JSON body.
    '''
    path = '/AccessPolicies'
    return helper_delete(access_token, oid, path)

def list_media_job(access_token, oid=""):
    '''List Media Service Job(s).

    Args:
        access_token (str): A valid Azure authentication token.
        oid (str): Media Service Job OID.

    Returns:
        HTTP response. JSON body.
    '''
    path = '/Jobs'
    return helper_list(access_token, oid, path)

def list_media_processor(access_token, oid=""):
    '''List Media Service Processor(s).

    Args:
        access_token (str): A valid Azure authentication token.
        oid (str): Media Service Processor OID.

    Returns:
        HTTP response. JSON body.
    '''
    path = '/MediaProcessors'
    return helper_list(access_token, oid, path)

def helper_list(access_token, oid, path):
    '''Helper Function to list a URL path.

    Args:
        access_token (str): A valid Azure authentication token.
        oid (str): An OID.
        path (str): A URL Path.

    Returns:
        HTTP response. JSON body.
    '''
    if oid != "":
        path = ''.join([path, "('", oid, "')"])
    endpoint = ''.join([ams_rest_endpoint, path])
    return do_ams_get(endpoint, path, access_token)

def helper_delete(access_token, oid, path):
    '''Helper Function to delete a Object at a URL path.

    Args:
        access_token (str): A valid Azure authentication token.
        oid (str): An OID.
        path (str): A URL Path.

    Returns:
        HTTP response. JSON body.
    '''
    full_path = ''.join([path, "('", oid, "')"])
    full_path_encoded = urllib.parse.quote(full_path, safe='')
    endpoint = ''.join([ams_rest_endpoint, full_path_encoded])
    return do_ams_delete(endpoint, full_path_encoded, access_token)

def list_media_asset(access_token, oid=""):
    '''List Media Service Asset(s).

    Args:
        access_token (str): A valid Azure authentication token.
        oid (str): Media Service Asset OID.

    Returns:
        HTTP response. JSON body.
    '''
    path = '/Assets'
    return helper_list(access_token, oid, path)

def upload_video(access_token, NAME, sto_account_name, VIDEO_PATH):
    ### create an asset
    print("Creating a Media Asset")
    response = create_media_asset(access_token, NAME)
    if (response.status_code == 201):
        resjson = response.json()
        asset_id = str(resjson['d']['Id'])
        print("POST Status.............................: " + str(response.status_code))
        print("Media Asset Name........................: " + NAME)
        print("Media Asset Id..........................: " + asset_id)
    else:
        print("POST Status.............................: " + str(response.status_code) + " - Media Asset: '" + NAME + "' Creation ERROR." + str(response.content))
        
    ### create an assetfile
    print("Creating a Media Assetfile (for the video file)")
    response = create_media_assetfile(access_token, asset_id, NAME+".mp4", "false", "false")
    if (response.status_code == 201):
        resjson = response.json()
        video_assetfile_id = str(resjson['d']['Id'])
        print("POST Status.............................: " + str(response.status_code))
        print("Media Assetfile Name....................: " + str(resjson['d']['Name']))
        print("Media Assetfile Id......................: " + video_assetfile_id)
        print("Media Assetfile IsPrimary...............: " + str(resjson['d']['IsPrimary']))
    else:
        print("POST Status: " + str(response.status_code) + " - Media Assetfile: '" + VIDEO_NAME + "' Creation ERROR." + str(response.content))

    ### create an asset write access policy for uploading
    print("Creating an Asset Write Access Policy")
    duration = "5" #in minutes
    response = create_asset_accesspolicy(access_token, "8k_UploadPolicy", duration, "2")
    if (response.status_code == 201):
        resjson = response.json()
        write_accesspolicy_id = str(resjson['d']['Id'])
        print("POST Status.............................: " + str(response.status_code))
        print("Asset Access Policy Id..................: " + write_accesspolicy_id)
        print("Asset Access Policy Duration/min........: " + str(resjson['d']['DurationInMinutes']))
    else:
        print("POST Status: " + str(response.status_code) + " - Asset Write Access Policy Creation ERROR." + str(response.content))

    ### create a sas locator
    print("Creating a write SAS Locator")
    response = create_sas_locator(access_token, asset_id, write_accesspolicy_id)
    if (response.status_code == 201):
        resjson = response.json()
        saslocator_id = str(resjson['d']['Id'])
        saslocator_baseuri = str(resjson['d']['BaseUri'])
        sto_asset_name = os.path.basename(os.path.normpath(saslocator_baseuri))
        saslocator_cac = str(resjson['d']['ContentAccessComponent'])
        print("POST Status.............................: " + str(response.status_code))
        print("SAS URL Locator StartTime...............: " + str(resjson['d']['StartTime']))
        print("SAS URL Locator Id......................: " + saslocator_id)
        print("SAS URL Locator Base URI................: " + saslocator_baseuri)
        print("SAS URL Locator Content Access Component: " + saslocator_cac)
    else:
        print("POST Status: " + str(response.status_code) + " - SAS URL Locator Creation ERROR." + str(response.content))

    ### Use the Azure Blob Blob Servic library from the Azure Storage SDK.
    block_blob_service = BlockBlobService(account_name=sto_account_name, sas_token=saslocator_cac[1:])
    
    ### Start upload the video file
    print("Uploading the Video File")
    VIDEO_NAME = NAME+".mp4"
    with open(VIDEO_PATH, mode='rb') as file:
        video_content = file.read()
        video_content_length = len(video_content)
        
    response = block_blob_service.create_blob_from_path(
        sto_asset_name,
        VIDEO_NAME,
        VIDEO_PATH,
        max_connections=5,
        content_settings=ContentSettings(content_type='video/mp4'),
        progress_callback=uploadCallback,
    )
    
    if (response == None):
        print("PUT Status..............................: 201")
        print("Video File Uploaded.....................: OK")
        
    ### update the assetfile metadata after uploading
    print("Updating the Video Assetfile")
    response = update_media_assetfile(access_token, asset_id, video_assetfile_id, video_content_length, VIDEO_NAME)
    if (response.status_code == 204):
        print("MERGE Status............................: " + str(response.status_code))
        print("Assetfile Content Length Updated........: " + str(video_content_length))
    else:
        print("MERGE Status............................: " + str(response.status_code) + " - Assetfile: '" + VIDEO_NAME + "' Update ERROR." + str(response.content))
    
    ### delete the locator, so that it can't be used again
    print("Deleting the Locator")
    response = delete_sas_locator(access_token, saslocator_id)
    if (response.status_code == 204):
        print("DELETE Status...........................: " + str(response.status_code))
        print("SAS URL Locator Deleted.................: " + saslocator_id)
    else:
        print("DELETE Status...........................: " + str(response.status_code) + " - SAS URL Locator: '" + saslocator_id + "' Delete ERROR." + str(response.content))

    ### delete the asset access policy
    print("Deleting the Acess Policy")
    response = delete_asset_accesspolicy(access_token, write_accesspolicy_id)
    if (response.status_code == 204):
        print("DELETE Status...........................: " + str(response.status_code))
        print("Asset Access Policy Deleted.............: " + write_accesspolicy_id)
    else:
        print("DELETE Status...........................: " + str(response.status_code) + " - Asset Access Policy: '" + write_accesspolicy_id + "' Delete ERROR." + str(response.content))

    ### get the media processor for Face Detecion
    print("Getting the Media Processor for Face Detection")
    response = list_media_processor(access_token)
    if (response.status_code == 200):
        resjson = response.json()
        print("GET Status..............................: " + str(response.status_code))
        for mp in resjson['d']['results']:
            if(str(mp['Name']) == PROCESSOR_NAME):
                processor_id = str(mp['Id'])
                print("MEDIA Processor Id......................: " + processor_id)
                print("MEDIA Processor Name....................: " + PROCESSOR_NAME)
    else:
        print("GET Status: " + str(response.status_code) + " - Media Processors Listing ERROR." + str(response.content))
        
    return processor_id, asset_id

def get_face_track_emotion(access_token, processor_id, asset_id, sto_account_name, sto_accountKey, ASSET_FINAL_NAME):
    
    #input request parameters
    with open(REQUEST_BODY, mode='r') as file:
            configuration_emotion = file.read()    
            
    response = encode_mezzanine_asset(access_token, processor_id, asset_id, ASSET_FINAL_NAME, configuration_emotion)
    #print(response.json()," in track")
    if (response.status_code == 201):
        resjson = response.json()
        job_id = str(resjson['d']['Id'])
        print("POST Status.............................: " + str(response.status_code))
        print("Media Job Id............................: " + job_id)
    else:
        print("POST Status.............................: " + str(response.status_code) + " - Media Job Creation ERROR." + str(response.content))

    ### list a media job
    print("Getting the Media Job Status")
    flag = 1
    while(flag):
        try:
            response = list_media_job(access_token, job_id)
            if (response.status_code == 200):
                resjson = response.json()
                job_state = str(resjson['d']['State'])
                if (resjson['d']['EndTime'] != None):
                    joboutputassets_uri = resjson['d']['OutputMediaAssets']['__deferred']['uri']
                    flag = 0
                print("GET Status..............................: " + str(response.status_code))
                print("Media Job Status........................: " + translate_job_state(job_state))
        except:
            print("GET Status..............................: " + str(response.status_code) + " - Media Job: '" + asset_id + "' Listing ERROR." + str(response.content))
            time.sleep(180)
            continue
        time.sleep(180)
        
    ## getting the output Asset id
    print("Getting the Indexed Media Asset Id")
    response = get_url(access_token, joboutputassets_uri, False)
    if (response.status_code == 200):
        resjson = response.json()
        face_asset_id = resjson['d']['results'][0]['Id']
        print("GET Status..............................: " + str(response.status_code))
        print("Indexed Media Asset Id..................: " + face_asset_id)
    else:
        print("GET Status..............................: " + str(response.status_code) + " - Media Job Output Asset: '" + job_id + "' Getting ERROR." + str(response.content))

    # Get Asset by using the list_media_asset method and the Asset ID
    response = list_media_asset(access_token,face_asset_id)
    if (response.status_code == 200):
        resjson = response.json()
        # Get the container name from the Uri
        outputAssetContainer = resjson['d']['Uri'].split('/')[3]
        print(outputAssetContainer)

    ### Use the Azure Blob Blob Service library from the Azure Storage SDK to download just the output JSON file
    block_blob_service = BlockBlobService(account_name=sto_account_name,account_key=sto_accountKey)
    generator = block_blob_service.list_blobs(outputAssetContainer)
    for blob in generator:
        print(blob.name)
        if (blob.name.endswith(".json")):
            print("\n\n##### Output Results ######")
            blobText = block_blob_service.get_blob_to_text(outputAssetContainer, blob.name)
            #print(blobText.content)
            print('Results saved as JSON')
            block_blob_service.get_blob_to_path(outputAssetContainer, blob.name,  OUTPUT_FOLDER + blob.name+'.json')
        else:
            block_blob_service.get_blob_to_path(outputAssetContainer, blob.name, OUTPUT_FOLDER + blob.name+'.json')


def main():    
    # Load Azure app defaults
    try:
        with open(CONFIG_FILE) as configFile:
            configData = json.load(configFile)
    except FileNotFoundError:
        print("ERROR: Expecting config.json in examples folder")
        sys.exit()
        
    account_name     = configData['accountName']
    account_key      = configData['accountKey']
    sto_account_name = configData['sto_accountName']
    sto_accountKey   = configData['sto_accountKey']
    tenant_id        = configData['tenant_id']
    application_id   = configData['application_id']
    
    #Initialization...
    print ("\n-----------------------= AMS Py =----------------------")
    print ("Azure Media Analytics - Face Detector Test")
    print ("-------------------------------------------------------\n")
    
    #step 1: Get Access Token
    access_token, ams_redirected_rest_endpoint = get_access_token_with_rest_end(tenant_id, application_id, account_key)
    
    #setp 2: Upload video
    #setup path for input video
    NAME = os.path.basename(VIDEO_PATH)[:-4]
    ASSET_FINAL_NAME = 'analysed_'+NAME
    processor_id, asset_id= upload_video(access_token, NAME, sto_account_name, VIDEO_PATH)
    
    #step 3: Get face detection with Emotion
    get_face_track_emotion(access_token, processor_id, asset_id, sto_account_name, sto_accountKey, ASSET_FINAL_NAME)
    

    
if __name__ == '__main__':
    main()

