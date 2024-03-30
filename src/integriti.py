import requests
import configparser
import time
import logging
import json

# Configure logging
logging.basicConfig(filename='logs/debug.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def integriti(api_token):
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {api_token}'
        }
    url = 'https://api.intigriti.com/external/researcher/v1/programs'
    feed = {}

    response = requests.get(url, headers=headers)
    data = response.json()

    for program in data['records']:
        program_handle = program['handle']
        program_id = program['id']
        temp = {
            'name': program['name'],
            'submission_state': "TODO",
            'handle': program_handle,
            'in-scope': [],
            'out-of-scope': []
        }

        program_url = f'https://api.intigriti.com/external/researcher/v1/programs/{program_id}'
        program_response = requests.get(program_url, headers=headers)
        program_data = program_response.json()
        if(program_response.status_code == 200):
            for _ in program_data['domains']:
                for content in program_data['domains']['content']:
                    scope_url = content['endpoint'].replace('http://', '')
                    scope_url = content['endpoint'].replace('https://', '')
                    asset_type = content['type']['value']
                    asset_status = content['tier']['value']
                    if(asset_status != 'Out Of Scope'):
                        if (asset_type == 'Url' or asset_type == 'Wildcard'):
                            if scope_url is not None and all(char not in scope_url for char in (' ', '{', '}', '<', '>', '%')) and '.' in scope_url:
                                if(scope_url not in temp['in-scope']):
                                    temp['in-scope'].append(scope_url)
                    else:
                        # Out-Of-Scope Target
                        if (asset_type == 'Url' or asset_type == 'Wildcard'):
                            if scope_url is not None and all(char not in scope_url for char in (' ', '{', '}', '<', '>', '%')) and '.' in scope_url:
                                if(scope_url not in temp['out-of-scope']):
                                    temp['out-of-scope'].append(scope_url)
                    

            if(temp['in-scope']):
                feed[program_handle.replace(' ', '-')] = temp

    return feed

def main():
    config = configparser.ConfigParser()
    config.read('config.ini')

    if 'integriti' in config:
        api_token = config['integriti']['API_TOKEN']
        feed = integriti(api_token)

        with open('feeds/integriti.json', 'w') as file:
            json.dump(feed, file)

if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    logging.info(f"Integriti Execution Time: {end_time - start_time}")
