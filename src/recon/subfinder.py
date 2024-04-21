import json
import subprocess
import concurrent.futures
from concurrent.futures import as_completed
import os
from tqdm import tqdm
from datetime import date
from db_operations import create_database, get_cursor, get_new_subdomains
import logging
import time
from helpers import notify

# Configure logging
logging.basicConfig(filename='logs/debug.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def run_subfinder(url, program, public, vdp):
    try:
        command = ['subfinder', '-all', '-silent', '-d', url, '-rl', '1']
        output = subprocess.check_output(command, text=True, timeout=300)
        return output, program, public, vdp
    except subprocess.TimeoutExpired:
        logging.error(f'Subfinder took longer than 5 minutes and timed-out on {url}')
        return None, program, public, vdp
    except subprocess.CalledProcessError as e:
        logging.error(f'Subfinder command failed with error code {e.returncode}: {e.output}')
        return None, program, public, vdp
    except Exception as e:
        logging.error(f'Subfinder had an error occur on {url}: {e}')
        return None, program, public, vdp

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
                platform = filename_cleaned
                create_database(f"swarm.db")
                cursor = get_cursor(f"swarm.db")
                for program in feed:
                   
                    wildcards.setdefault(program, {})
                    wildcards[program].setdefault('subdomains', [])
                    is_public = feed[program]['public']
                    is_vdp = feed[program]['vdp']
                    for subdomain in feed[program]['in-scope']['WILDCARD']:
                        wildcard_domain = (subdomain)
                        wildcards[program]['subdomains'].append(wildcard_domain.replace('*.', ''))
                        wildcards[program]['public'] = is_public
                        wildcards[program]['vdp'] = is_vdp
                        cursor.execute("INSERT OR REPLACE INTO wildcard_domains (wildcard_domain) VALUES (?)", (wildcard_domain,))
                        
                    for subdomain in feed[program]['in-scope']['URL']:
                        cursor.execute('''INSERT OR REPLACE INTO subdomains 
                                            (id, subdomain, ip, asn, status_code, content_length, web_server, technology, program, recon_source, public, vdp, platform, updated_at, created_at) 
                                            VALUES 
                                            ((SELECT id FROM subdomains WHERE subdomain = ?),
                                            ?,
                                            ?,
                                            ?,
                                            ?,
                                            ?,
                                            ?,
                                            ?,
                                            ?,
                                            ?,
                                            ?,
                                            ?,
                                            ?,
                                            DATE('now', 'localtime'),
                                            COALESCE((SELECT created_at FROM subdomains WHERE subdomain = ?), DATE('now', 'localtime')))''', 
                                            (subdomain, subdomain, None, None, None, None, None, None, program, 'subfinder', is_public, is_vdp, platform, subdomain))

        # Collect results asynchronously
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for program in wildcards:
                for subdomain in wildcards[program]['subdomains']:
                    public = wildcards[program]['public']
                    vdp = wildcards[program]['vdp']
                    futures.append(executor.submit(run_subfinder, subdomain, program, public, vdp))

            num_futures = len(futures)
            with tqdm(total=num_futures) as pbar:
                for future in as_completed(futures):
                    subdomains, program, public, vdp = future.result()

                    if(subdomains):
                        subdomains = subdomains.split('\n')
                        for subdomain in subdomains:
                            if(subdomain):
                                cursor.execute('''INSERT OR REPLACE INTO subdomains 
                                            (id, subdomain, ip, asn, status_code, content_length, web_server, technology, program, recon_source, public, vdp, platform, updated_at, created_at) 
                                            VALUES 
                                            ((SELECT id FROM subdomains WHERE subdomain = ?),
                                            ?,
                                            ?,
                                            ?,
                                            ?,
                                            ?,
                                            ?,
                                            ?,
                                            ?,
                                            ?,
                                            ?,
                                            ?,
                                            ?,
                                            COALESCE((SELECT updated_at FROM subdomains WHERE subdomain = ?), DATE('now', 'localtime')),
                                            COALESCE((SELECT created_at FROM subdomains WHERE subdomain = ?), DATE('now', 'localtime')))''', 
                                            (subdomain, subdomain, None, None, None, None, None, None, program, 'subfinder', is_public, is_vdp, platform, subdomain, subdomain))
                                
                        cursor.connection.commit()

                    pbar.update(1)
    cursor.connection.commit()
    cursor.close()
    

if __name__ == '__main__':
    start_time = time.time()
    main()
    end_time = time.time()
    new_subs = get_new_subdomains("subfinder")
    notify("Subfinder", end_time - start_time, f"number of new subdomains {new_subs}")
    logging.info(f"Subfinder Execution Time: {end_time - start_time}")
    
