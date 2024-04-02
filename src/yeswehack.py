

import requests
import time
import logging
import json

# Configure logging
logging.basicConfig(filename='logs/debug.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
            program_handle = program['business_unit']['name'].lower()
            program_url_slug = program['slug']
            temp = {
                'name': program['title'],
                'submission_state': program['status'],
                'handle': program_handle,
                'in-scope': [],
                'out-of-scope': []
            }

            program_url = f'https://api.yeswehack.com/programs/{program_url_slug}/versions'
            program_response = requests.get(program_url, headers=headers)
            program_data = program_response.json()


            for version_data in program_data['items']:
                for target in version_data['data'].get('scopes', []):
                    scope_type = target['scope_type']
                    if(scope_type in ('web-application', 'ip-address', 'api')):
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
                                    if((split_base + variation) not in temp['in-scope']):
                                        temp['in-scope'].append(split_base + variation)
                            if('[' in target['scope'] and ']' in target['scope'] and '|' in target['scope'] and target['scope'][0] != '['): # Handles cases: www.bookbeat.[se|fi|dk|co.uk|de|pl|dk|ch|at|no|nl|be|es|it|fr]
                                split_base = target['scope'].split('[')[0]
                                split_arr = target['scope'].split('[')[1]
                                split_arr = split_arr.replace(']', '')
                                split_arr = split_arr.split('|')
                                for variation in split_arr:
                                    if((split_base + variation) not in temp['in-scope']):
                                        temp['in-scope'].append(split_base + variation)
                            if('(' in target['scope'] and ')' in target['scope'] and '|' in target['scope'] and target['scope'][0] == '('): # (online|portal|agents|agentuat|surinameuat|surinameopsuat|suriname|thailandevoa).vfsevisa.com
                                split_base = target['scope'].split(')')[1]
                                split_arr = target['scope'].split(')')[0]
                                split_arr = split_arr.replace('(', '')
                                split_arr = split_arr.split('|')
                                for variation in split_arr:
                                    if((variation + split_base) not in temp['in-scope']):
                                        temp['in-scope'].append(variation + split_base)
                            if('|' not in target['scope']):
                                if(target['scope'] not in temp['in-scope']):
                                    temp['in-scope'].append(target['scope'])

                for target in version_data['data'].get('out_of_scope', []):
                    if target is not None and all(char not in target for char in (' ', '{', '}', '<', '>', '%')) and '.' in target:
                        target = target.replace('http://', '')
                        target = target.replace('https://', '')
                        temp['out-of-scope'].append(target)


            if(program_handle in feed):
                for url in temp['in-scope']:
                    if(url not in feed[program_handle]['in-scope']):
                        feed[program_handle.replace(' ', '-')]['in-scope'].append(url)

                for url in temp['out-of-scope']:
                    if(url not in feed[program_handle]['out-of-scope']):
                        feed[program_handle.replace(' ', '-')]['out-of-scope'].append(url)
            else:
                feed[program_handle.replace(' ', '-')] = temp

        page = page + 1

def main():
    start_time = time.time()
    feed = yeswehack()
    end_time = time.time()
    logging.info(f"YesWeHack Execution Time: {end_time - start_time}")

    with open('feeds/yeswehack.json', 'w') as file:
        json.dump(feed, file)

if __name__ == "__main__":
    main()
