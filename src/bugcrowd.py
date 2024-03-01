

import requests
import time
import logging
import json

# Configure logging
logging.basicConfig(filename='debug/debug.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def bugcrowd():
    headers = {'Accept': 'application/json'}
    page = 0
    feed = {}

    while True:
        response = requests.get(f'https://bugcrowd.com/engagements.json?page={page}', headers=headers)
        data = response.json()

        if(data['engagements'] == []):
            return feed

        for program in data['engagements']:
            program_handle = program['briefUrl']
            temp = {
                'name': program['name'],
                'submission_state': program['accessStatus'],
                'handle': program_handle,
                'scope': []
            }

            program_url = f'https://bugcrowd.com/{program_handle}/target_groups'
            program_response = requests.get(program_url, headers=headers)
            program_data = program_response.json()

            for _data in program_data['groups']:
                target_group_url = _data['targets_url']
                is_in_scope = _data['in_scope']
                if is_in_scope:
                    target_group_response = requests.get(f'https://bugcrowd.com{target_group_url}')

                    for target in target_group_response.json()['targets']:
                        scope_type = target['category']
                        if(scope_type in ('api', 'website')):
                            if target['name'] is not None and all(char not in target['name'] for char in (' ', '{', '}', '<', '>', '%')) and '.' in target['name']:
                                temp['scope'].append(target['name'])

                            if target['ipAddress'] is not None and all(char not in target['ipAddress'] for char in (' ', '{', '}', '<', '>', '%')) and '.' in target['ipAddress']:
                                temp['scope'].append(target['ipAddress'])

            feed[program_handle] = temp

        page = page + 1

def main():
    start_time = time.time()
    feed = bugcrowd()
    end_time = time.time()
    logging.info(f"Bugcrowd Execution Time: {end_time - start_time}")

    for program in feed.values():
        for url in program['scope']:
            print(url)

    with open('debug/bugcrowd.json', 'w') as file:
        json.dump(feed, file)

if __name__ == "__main__":
    main()
