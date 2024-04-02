import requests
import configparser
import time
import logging
import json

# Configure logging
logging.basicConfig(filename='logs/debug.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def hackerone(api_username, api_token):
    headers = {'Accept': 'application/json'}
    url = 'https://api.hackerone.com/v1/hackers/programs'
    feed = {}

    while True:
        response = requests.get(url, auth=(api_username, api_token), headers=headers)
        data = response.json()

        for program in data['data']:
            program_handle = program['attributes']['handle']
            temp = {
                'name': program['attributes']['name'],
                'submission_state': program['attributes']['submission_state'],
                'handle': program_handle,
                'in-scope': [],
                'out-of-scope': []
            }

            program_url = f'https://api.hackerone.com/v1/hackers/programs/{program_handle}/structured_scopes'
            program_response = requests.get(program_url, auth=(api_username, api_token), headers=headers)
            program_data = program_response.json()

            for _data in program_data['data']:

                # Only get items that are in-scope
                in_scope = _data['attributes']['eligible_for_submission']
                scope_type = "in-scope" if in_scope else "out-of-scope"
                temp = target(_data, temp, scope_type)
            
            if(temp['in-scope']):
                feed[program_handle.replace(' ', '-')] = temp

        if 'next' in data['links']:
            url = data['links']['next']
        else:
            break

    return feed

def target(_data, temp, scope_type):
    asset_type = _data['attributes']['asset_type']
    if asset_type in ('URL', 'WILDCARD'):
        scope_url =  _data['attributes']['asset_identifier']
        # Remove http:// and https:// to handle wildward cases like so: https://*.app.spacelift.dev
        scope_url = scope_url.replace('http://', '')
        scope_url = scope_url.replace('https://', '')
        if scope_url is not None and all(char not in scope_url for char in (' ', '{', '}', '<', '>', '%')) and '.' in scope_url:
            if(',' in scope_url):
                scope_urls = scope_url.split(',')
                for url in scope_urls:
                    if(scope_url not in temp[scope_type]):
                        temp[scope_type].append(url)
            else:
                if(scope_url not in temp[scope_type]):
                    temp[scope_type].append(scope_url)
    return temp

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
