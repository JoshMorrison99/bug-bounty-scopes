import requests
import configparser
import time
import logging
import json

# Configure logging
logging.basicConfig(filename='debug/debug.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
                'scope': []
            }

            program_url = f'https://api.hackerone.com/v1/hackers/programs/{program_handle}/structured_scopes'
            program_response = requests.get(program_url, auth=(api_username, api_token), headers=headers)
            program_data = program_response.json()

            for _data in program_data['data']:
                asset_type = _data['attributes']['asset_type']
                if asset_type in ('URL', 'WILDCARD'):
                    if _data['attributes']['asset_identifier'] is not None and all(char not in _data['attributes']['asset_identifier'] for char in (' ', '{', '}', '<', '>', '%')) and '.' in _data['attributes']['asset_identifier']:
                        temp['scope'].append(_data['attributes']['asset_identifier'])

            feed[program_handle] = temp

        if 'next' in data['links']:
            url = data['links']['next']
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

        for program in feed.values():
            for url in program['scope']:
                print(url)

        with open('debug/hackerone.json', 'w') as file:
            json.dump(feed, file)
    else:
        print("Error: 'hackerone' section not found in the config file.")

if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    logging.info(f"HackerOne Execution Time: {end_time - start_time}")
