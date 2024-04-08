import requests
import configparser
import time
import logging
import json
from helpers import normalize

# Configure logging
logging.basicConfig(filename='logs/debug.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def hackerone(api_username, api_token):
    headers = {'Accept': 'application/json'}
    url = 'https://api.hackerone.com/v1/hackers/programs'
    feed = {}

    while True:
        response = requests.get(url, auth=(api_username, api_token), headers=headers)
        h1 = response.json()

        for program in h1['data']:

            if('handle' not in program['attributes']):
                continue
            
            program_handle = program['attributes']['handle']
            program_object = {
                'name': program['attributes']['name'],
                'submission_state': program['attributes']['submission_state'],
                'handle': program_handle,
                'in-scope': {
                    'WILDCARD': [],
                    'URL': [],
                    'IP_ADDRESS': [],
                    'CIDR': [],
                },
                'out-of-scope': {
                    'WILDCARD': [],
                    'URL': [],
                    'IP_ADDRESS': [],
                    'CIDR': [],
                }
            }

            program_url = f'https://api.hackerone.com/v1/hackers/programs/{program_handle}/structured_scopes'

            while True:
                program_response = requests.get(program_url, auth=(api_username, api_token), headers=headers)
                data = program_response.json()

                for program_data in data['data']:

                    # Classify item as in-scope or out-of-scope
                    is_in_scope = program_data['attributes']['eligible_for_submission']
                    scope_type = "in-scope" if is_in_scope else "out-of-scope"

                    # Asset type can be: 'DOWNLOADABLE_EXECUTABLES', 'OTHER', 'OTHER_APK', 'GOOGLE_PLAY_APP_ID', 'WILDCARD', 'HARDWARE', 'IP_ADDRESS', 'TESTFLIGHT', 'CIDR', 'APPLE_STORE_APP_ID', 'SMART_CONTRACT', 'OTHER_IPA', 'SOURCE_CODE', 'URL', 'WINDOWS_APP_STORE_APP_ID'
                    asset_type = program_data['attributes']['asset_type']
                    if asset_type in ('URL', 'WILDCARD', 'IP_ADDRESS', 'CIDR', 'OTHER'):
                        scope_url =  program_data['attributes']['asset_identifier']
                        
                        if(asset_type in ('URL', 'WILDCARD', 'OTHER')):
                            normalized_urls = normalize(scope_url)

                            for scope_url in normalized_urls:
                                if(scope_url.startswith('*.')):
                                    program_object[scope_type]['WILDCARD'].append(scope_url)
                                else:
                                    program_object[scope_type]['URL'].append(scope_url)

                        if(asset_type in ('IP_ADDRESS', 'CIDR')):
                            if('/' in scope_url):
                                program_object[scope_type]['CIDR'].append(scope_url)
                            else:
                                program_object[scope_type]['IP_ADDRESS'].append(scope_url)

                if 'next' in data['links']:
                    program_url = data['links']['next']
                else:
                    break
                
            # Only add program_object if there are value in the [in-scope] section
            if(program_object['in-scope']):
                feed[program_handle] = program_object

        if 'next' in h1['links']:
            url = h1['links']['next']
        else:
            break

    return feed

def main():
    config = configparser.ConfigParser()
    config.read('config.ini')

    if 'hackerone' in config:
        api_username = config['hackerone']['API_USERNAME']
        api_token = config['hackerone']['API_TOKEN']
        feed = hackerone(api_username, api_token)

        logging.info(f"Number of Programs in HackerOne is {len(feed)}")
        with open('feeds/hackerone.json', 'w') as file:
            json.dump(feed, file)
    else:
        print("Error: 'hackerone' section not found in the config file.")

if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    logging.info(f"HackerOne Execution Time: {end_time - start_time}")
