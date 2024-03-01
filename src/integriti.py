import requests
import configparser
import time
import logging
import json

# Configure logging
logging.basicConfig(filename='debug/debug.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
            'scope': []
        }

        program_url = f'https://api.intigriti.com/external/researcher/v1/programs/{program_id}'
        program_response = requests.get(program_url, headers=headers)
        program_data = program_response.json()
        if(program_response.status_code == 200):
            for _ in program_data['domains']:
                for content in program_data['domains']['content']:
                    asset_type = content['type']['value']
                    asset_status = content['tier']['value']
                    if asset_type == 'Url' and asset_status != "Out Of Scope":
                        if content['endpoint'] is not None and all(char not in content['endpoint'] for char in (' ', '{', '}', '<', '>', '%')) and '.' in content['endpoint']:
                            temp['scope'].append(content['endpoint'])

            feed[program_handle] = temp

    return feed

def main():
    config = configparser.ConfigParser()
    config.read('config.ini')

    if 'integriti' in config:
        api_token = config['integriti']['API_TOKEN']
        feed = integriti(api_token)

        for program in feed.values():
            for url in program['scope']:
                print(url)

        with open('debug/integriti.json', 'w') as file:
            json.dump(feed, file)

if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    logging.info(f"Integriti Execution Time: {end_time - start_time}")
