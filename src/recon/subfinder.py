import json
import subprocess
import concurrent.futures
from concurrent.futures import as_completed
import os
from tqdm import tqdm
from datetime import date
from db_operations import create_database, get_cursor
import logging

# Configure logging
logging.basicConfig(filename='logs/debug.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def run_subfinder(url, program):
    try:
        command = ['subfinder', '-all', '-silent', '-d', url, '-rl', '1']
        output = subprocess.check_output(command, text=True, timeout=300)
        return output, program
    except subprocess.TimeoutExpired:
        logging.error(f'Subfinder took longer than 5 minutes and timed-out on {url}')
        return None, program
    except subprocess.CalledProcessError as e:
        logging.error(f'Subfinder command failed with error code {e.returncode}: {e.output}')
        return None, program
    except Exception as e:
        logging.error(f'Subfinder had an error occur on {url}: {e}')
        return None, program

def main():

    max_workers = 5

    # Loop over all files in the folder
    for filename in os.listdir('feeds'):
        filename_cleaned = filename.replace('.json', '')
        feed = {}
        wildcards = {}  
        print(f"[INFO] Subfinder {filename_cleaned}")
        # Check if the path is a file
        if os.path.isfile(os.path.join('feeds', filename)):
            with open(f'feeds/{filename}', 'r') as file:
                feed = json.load(file)
                bb_program = filename_cleaned
                create_database(f"db/{bb_program}.db")
                cursor = get_cursor(f"db/{bb_program}.db")
                for program in feed:
                   
                    if(program not in wildcards):
                        wildcards[program] = []

                    for subdomain in feed[program]['in-scope']['WILDCARD']:
                        wildcard_domain = (subdomain)
                        wildcards[program].append(wildcard_domain.replace('*.', ''))
                        cursor.execute("INSERT OR REPLACE INTO wildcard_domains (wildcard_domain) VALUES (?)", (wildcard_domain,))
                        
                    for subdomain in feed[program]['in-scope']['URL']:
                        cursor.execute('''INSERT OR REPLACE INTO subdomains 
                                            (id, subdomain, ip, status_code, web_server, technology, program, updated_at, created_at) 
                                            VALUES 
                                            ((SELECT id FROM subdomains WHERE subdomain = ?),
                                            ?,
                                            ?,
                                            ?,
                                            ?,
                                            NULL,
                                            ?,
                                            DATE('now', 'localtime'),
                                            COALESCE((SELECT created_at FROM subdomains WHERE subdomain = ?), DATE('now', 'localtime')))''', 
                                            (subdomain, subdomain, None, None, None, program, subdomain))

        # Collect results asynchronously
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for program in wildcards:
                for subdomain in wildcards[program]:
                    futures.append(executor.submit(run_subfinder, subdomain, program))

            num_futures = len(futures)
            with tqdm(total=num_futures) as pbar:
                completed = 0
                for future in as_completed(futures):
                    subdomains, program = future.result()

                    if(subdomains):
                        subdomains = subdomains.split('\n')
                        for subdomain in subdomains:
                            if(subdomain):
                                cursor.execute('''INSERT OR REPLACE INTO subdomains 
                                                (id, subdomain, ip, status_code, web_server, technology, program, updated_at, created_at) 
                                                VALUES 
                                                ((SELECT id FROM subdomains WHERE subdomain = ?),
                                                ?,
                                                ?,
                                                ?,
                                                ?,
                                                NULL,
                                                ?,
                                                DATE('now', 'localtime'),
                                                COALESCE((SELECT created_at FROM subdomains WHERE subdomain = ?), DATE('now', 'localtime')))''', 
                                                (subdomain, subdomain, None, None, None, program, subdomain))
                        cursor.connection.commit()

                    completed += 1
                    pbar.update(1)
    cursor.connection.commit()
    cursor.close()

if __name__ == '__main__':
    main()
