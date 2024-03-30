

import requests
import time
import logging
import json

# Configure logging
logging.basicConfig(filename='logs/debug.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
            program_handle = program['briefUrl'][1:] # remove the forward slash at beginning of each handle
            temp = {
                'name': program['name'],
                'submission_state': program['accessStatus'],
                'handle': program_handle,
                'in-scope': [],
                'out-of-scope': []
            }

            program_url = f'https://bugcrowd.com/{program_handle}/target_groups'
            program_response = requests.get(program_url, headers=headers)
            program_data = program_response.json()
            for _data in program_data['groups']:
                target_group_url = _data['targets_url']
                in_scope = _data['in_scope']
                is_in_scope = "in-scope" if in_scope else "out-of-scope"
                temp = target(target_group_url, temp, is_in_scope)

            if(temp['in-scope']):
                feed[program_handle.replace(' ', '-')] = temp

        page = page + 1

def target(target_group_url, temp, is_in_scope):
    scope_ip = None
    target_group_response = requests.get(f'https://bugcrowd.com{target_group_url}')
    for target in target_group_response.json()['targets']:
        scope_url = target['name'].replace('http://', '')
        scope_url = target['name'].replace('https://', '')

        if target['ipAddress'] is not None:
            scope_ip = target['ipAddress'].replace('http://', '')
            scope_ip = target['ipAddress'].replace('https://', '')

        scope_type = target['category']
        if(scope_type in ('api', 'website')):
            if scope_url is not None and all(char not in scope_url for char in (' ', '{', '}', '<', '>', '%')) and '.' in scope_url:
                if(scope_url not in temp[is_in_scope]):
                    temp[is_in_scope].append(scope_url.replace('\t', ''))

            if scope_ip is not None and all(char not in scope_ip for char in (' ', '{', '}', '<', '>', '%')) and '.' in scope_ip:
                if(scope_ip not in temp[is_in_scope]):
                    temp[is_in_scope].append(scope_ip)

    return temp

def main():
    start_time = time.time()
    feed = bugcrowd()
    end_time = time.time()
    logging.info(f"Bugcrowd Execution Time: {end_time - start_time}")

    with open('feeds/bugcrowd.json', 'w') as file:
        json.dump(feed, file)

if __name__ == "__main__":
    main()
