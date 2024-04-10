import json
import subprocess
import concurrent.futures
from concurrent.futures import as_completed
import os
from tqdm import tqdm
from datetime import date
from db_operations import create_database, get_cursor
import logging
import shlex
import shutil
import time

# Configure logging
logging.basicConfig(filename='logs/debug.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def run_dnsx(filename, program):
    try:
        command = f"dnsx -l {filename} -r resolvers.txt -resp-only -ptr -silent"
        args = shlex.split(command)
        output = subprocess.check_output(args, text=True, timeout=1800)
        return output, program, filename
    except subprocess.TimeoutExpired:
        logging.error(f'DNSx took longer than 30 minutes and timed-out on {filename}')
        return None, program, filename
    except subprocess.CalledProcessError as e:
        logging.error(f'DNSx command failed with error code {e.returncode}: {e.output}')
        return None, program, filename
    except Exception as e:
        logging.error(f'DNSx had an error occur on {filename}: {e}')
        return None, program, filename

def main():

    max_workers = 3

    # Loop over all files in the folder
    for filename in os.listdir('feeds'):
        filename_cleaned = filename.replace('.json', '')
        feed = {}
        cidrs = {}  
        print(f"[INFO] DNSx {filename_cleaned}")
        # Check if the path is a file
        if os.path.isfile(os.path.join('feeds', filename)):
            with open(f'feeds/{filename}', 'r') as file:
                feed = json.load(file)
                platform = filename_cleaned
                create_database(f"swarm.db")
                cursor = get_cursor(f"swarm.db")
                for program in feed:
                    
                    is_public = feed[program]['public']
                    is_vdp = feed[program]['vdp']

                    if(program not in cidrs):
                        cidrs[program] = []

                    for ip_address in feed[program]['in-scope']['IP_ADDRESS']:
                        cidrs[program].append(ip_address)
                        
                    for cidr in feed[program]['in-scope']['CIDR']:
                        cidrs[program].append(cidr)

        # Collect results asynchronously
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for program in cidrs:
                if(cidrs[program]):
                    filename = f'temp-{program}-dnsx'
                    with open(f'temp-{program}-dnsx', 'w') as file:
                        for cidr in cidrs[program]:
                            file.write(cidr + '\n')
                    futures.append(executor.submit(run_dnsx, filename, program))

            num_futures = len(futures)
            with tqdm(total=num_futures) as pbar:
                completed = 0
                for future in as_completed(futures):
                    subdomains, program, filename = future.result()
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
                                            DATE('now', 'localtime'),
                                            COALESCE((SELECT created_at FROM subdomains WHERE subdomain = ?), DATE('now', 'localtime')))''', 
                                            (subdomain, subdomain, None, None, None, None, None, None, program, 'dnsx', is_public, is_vdp, platform, subdomain))
                        cursor.connection.commit()
                        
                    if(os.path.exists(filename)):
                        os.remove(filename)

                    completed += 1
                    pbar.update(1)
    cursor.connection.commit()
    cursor.close()

if __name__ == '__main__':
    start_time = time.time()
    main()
    end_time = time.time()
    logging.info(f"DNSX Execution Time: {end_time - start_time}")
