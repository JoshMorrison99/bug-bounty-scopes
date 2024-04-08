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


def run_dnsx(cidr, program):
    try:
        command = f"dnsx -l {cidr} -r resolvers.txt -resp-only -ptr -silent"
        args = shlex.split(command)
        output = subprocess.check_output(args, text=True, timeout=600)
        return output, program
    except subprocess.TimeoutExpired:
        logging.error(f'DNSx took longer than 10 minutes and timed-out on {cidr}')
        return None, program
    except subprocess.CalledProcessError as e:
        logging.error(f'DNSx command failed with error code {e.returncode}: {e.output}')
        return None, program
    except Exception as e:
        logging.error(f'DNSx had an error occur on {cidr}: {e}')
        return None, program

def main():

    max_workers = 3
    
    # delete the alterx folder
    if os.path.exists('dnsx'):
        shutil.rmtree('dnsx')

    os.makedirs('dnsx', exist_ok=True)

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
                bb_program = filename_cleaned
                create_database(f"db/{bb_program}.db")
                cursor = get_cursor(f"db/{bb_program}.db")
                for program in feed:

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
                    filename = f'dnsx/temp-{program}-dnsx'
                    with open(f'dnsx/temp-{program}-dnsx', 'w') as file:
                        for cidr in cidrs[program]:
                            file.write(cidr + '\n')
                    futures.append(executor.submit(run_dnsx, filename, program))

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
    start_time = time.time()
    main()
    end_time = time.time()
    logging.info(f"DNSX Execution Time: {end_time - start_time}")
