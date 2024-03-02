

import requests
import time
import logging
import json

# Configure logging
logging.basicConfig(filename='debug.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def yeswehack():
    headers = {'Accept': 'application/json'}
    page = 0
    feed = {}

    while True:
        response = requests.get(f'https://api.yeswehack.com/programs?page={page}&resultsPerPage=50', headers=headers)
        data = response.json()

        if(data['items'] == []):
            return feed

        for program in data['items']:
            program_handle = program['slug']
            temp = {
                'name': program['title'],
                'submission_state': program['status'],
                'handle': program_handle,
                'scope': []
            }

            program_url = f'https://api.yeswehack.com/programs/{program_handle}/versions'
            program_response = requests.get(program_url, headers=headers)
            program_data = program_response.json()


            for version_data in program_data['items']:
                for target in version_data['data'].get('scopes', []):
                    scope_type = target['scope_type']
                    if(scope_type in ('web-application', 'ip-address')):
                        if target['scope'] is not None and all(char not in target['scope'] for char in (' ', '{', '}', '<', '>', '%')) and '.' in target['scope']:
                            # Remove http:// and https:// to handle wildward cases like so: https://*.app.spacelift.dev
                            target['scope'] = target['scope'].replace('http://', '')
                            target['scope'] = target['scope'].replace('https://', '')
                            if('(' in target['scope'] and ')' in target['scope'] and '|' in target['scope'] and target['scope'][0] != '('): # Handles cases: *.doctolib.(fr|de|it|com|net)
                                split_base = target['scope'].split('(')[0]
                                split_arr = target['scope'].split('(')[1]
                                split_arr = split_arr.replace(')', '')
                                split_arr = split_arr.split('|')
                                for variation in split_arr:
                                    temp['scope'].append(split_base + variation)
                            elif('[' in target['scope'] and ']' in target['scope'] and '|' in target['scope'] and target['scope'][0] != '['): # Handles cases: www.bookbeat.[se|fi|dk|co.uk|de|pl|dk|ch|at|no|nl|be|es|it|fr]
                                split_base = target['scope'].split('[')[0]
                                split_arr = target['scope'].split('[')[1]
                                split_arr = split_arr.replace(']', '')
                                split_arr = split_arr.split('|')
                                for variation in split_arr:
                                    temp['scope'].append(split_base + variation)
                            elif('(' in target['scope'] and ')' in target['scope'] and '|' in target['scope'] and target['scope'][0] == '('): # (online|portal|agents|agentuat|surinameuat|surinameopsuat|suriname|thailandevoa).vfsevisa.com
                                split_base = target['scope'].split(')')[1]
                                split_arr = target['scope'].split(')')[0]
                                split_arr = split_arr.replace('(', '')
                                split_arr = split_arr.split('|')
                                for variation in split_arr:
                                    temp['scope'].append(variation + split_base)
                            else:
                                temp['scope'].append(target['scope'])

            feed[program_handle] = temp

        page = page + 1

def main():
    start_time = time.time()
    feed = yeswehack()
    end_time = time.time()
    logging.info(f"YesWeHack Execution Time: {end_time - start_time}")
    dedup_scope = set()

    for program in feed.values():
        for url in program['scope']:
            dedup_scope.add(url)

    for url in dedup_scope:
        print(url)

    with open('debug/yeswehack.json', 'w') as file:
        json.dump(feed, file)

if __name__ == "__main__":
    main()
