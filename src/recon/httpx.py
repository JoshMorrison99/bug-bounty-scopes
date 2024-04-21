import os 
import subprocess
import sqlite3
from datetime import datetime
import logging
import shlex
import pandas as pd
import time
from tqdm import tqdm
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
from db_operations import get_resolved_subdomains
from helpers import notify, notify_debug

# Constants
MAX_WORKERS = 15

# Configure logging
logging.basicConfig(filename='logs/debug.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def run_httpx(filename):
    try:
        command = f'httpx.exe -list {filename} -threads 300 -rate-limit 250 -csv -asn -silent -stream'
        args = shlex.split(command)
        results = subprocess.run(args, stdout=subprocess.PIPE, text=True)
        return results.stdout
    except subprocess.CalledProcessError as e:
        # Handle subprocess errors
        logging.error(f"HTTPX encountered an error.")
        logging.error(f"Command failed with return code {e.returncode}: {e.output}")
        return None
    except Exception as e:
        # Handle other unexpected errors
        logging.error(f"HTTPX had an unexpected error.")
        logging.exception(e)  # Log the full exception traceback
        return None

def main():

    conn = sqlite3.connect(f'swarm.db')
    cursor = conn.cursor()

    current_date = datetime.now().strftime('%Y-%m-%d')

    # Get all the subdomains that were added today
    cursor.execute(f"SELECT subdomain FROM subdomains WHERE created_at LIKE '%2024-04-13%';")
    #cursor.execute(f"SELECT subdomain FROM subdomains WHERE created_at LIKE '%{current_date}%';")

    # Fetch all the results
    results = cursor.fetchall()

    # count = 0
    # file = open(f'httpx/temp-{count}.txt', 'w')
    # for index, subdomain in enumerate(results):
    #     file.write(subdomain[0] + '\n')
    #     if (index + 1) % 100 == 0:
    #         file.close()
    #         count = count + 1
    #         file = open(f'httpx/temp-{count}.txt', 'w')
            
    folder_path = "httpx"
    files = [os.path.join(folder_path, file) for file in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, file))]
    # Create a ThreadPoolExecutor
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit tasks to process each file concurrently
        futures = [executor.submit(run_httpx, file_path) for file_path in files]

        num_futures = len(futures)
        count = 0
        with tqdm(total=num_futures) as pbar:
            for future in as_completed(futures):
                notify_debug(f'[HTTPX2] - {count}/{num_futures}')
                
                df = pd.read_csv(io.StringIO(future.result()))
                columns = ['status_code', 'content_length', 'asn', 'webserver', 'host', 'url', 'tech', 'input']
                extracted_columns = df[columns]
                for _, row in extracted_columns.iterrows():
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    notify_debug(f'[HTTPX] - {current_time} - subdomain resolved: {row["input"]}')
                    status_code = row['status_code']
                    content_length = row['content_length']
                    asn = row['asn']
                    webserver = row['webserver']
                    ip = row['host']
                    technology = row['tech']
                    subdomain = row['input']
                    
                    
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
                            (SELECT program FROM subdomains WHERE subdomain = ?),
                            (SELECT recon_source FROM subdomains WHERE subdomain = ?),
                            (SELECT public FROM subdomains WHERE subdomain = ?),
                            (SELECT vdp FROM subdomains WHERE subdomain = ?),
                            (SELECT platform FROM subdomains WHERE subdomain = ?),
                            DATE('now', 'localtime'),
                            COALESCE((SELECT created_at FROM subdomains WHERE subdomain = ?), DATE('now', 'localtime')))''', 
                            (subdomain, subdomain, ip, asn, status_code, content_length, webserver, technology, subdomain,subdomain, subdomain, subdomain, subdomain, subdomain))
                cursor.connection.commit()
                pbar.update(1) 
                count = count + 1   
                
    # Close the cursor and connection
    cursor.close()
    conn.close()
        

if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    num_subs = get_resolved_subdomains()
    notify("HTTPX", end_time - start_time, f"number of resolved subdomains {num_subs}")
    logging.info(f"HTTPX Execution Time: {end_time - start_time}")



