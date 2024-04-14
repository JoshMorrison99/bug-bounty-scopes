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
from helpers import notify

# Constants
MAX_WORKERS = 5

# Configure logging
logging.basicConfig(filename='logs/debug.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def run_httpx(filename):
    try:
        command = f'httpx -list {filename} -csv -asn -silent -stream'
        args = shlex.split(command)
        results = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
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

def process_file(file_path, cursor):
    results = run_httpx(file_path)
    df = pd.read_csv(io.StringIO(results))
    columns = ['status_code', 'content_length', 'asn', 'webserver', 'host', 'url', 'tech', 'input']
    extracted_columns = df[columns]
    
    for _, row in extracted_columns.iterrows():
        insert_into_database(row, cursor)

def insert_into_database(row, cursor):
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
                        (row['input'], row['input'], row['host'], row['asn'], row['status_code'], row['content_length'], row['webserver'], row['tech'], row['input'], row['input'], row['input'], row['input'], row['input'], row['input']))
    cursor.connection.commit()


def main():

    conn = sqlite3.connect(f'swarm.db')
    cursor = conn.cursor()

    current_date = datetime.now().strftime('%Y-%m-%d')

    # Get all the subdomains that were added today
    cursor.execute(f"SELECT subdomain FROM subdomains WHERE created_at LIKE '%{current_date}%';")

    # Fetch all the results
    results = cursor.fetchall()

    count = 0
    file = open(f'httpx/temp-{count}.txt', 'w')
    for index, subdomain in enumerate(results):
        file.write(subdomain[0] + '\n')
        if (index + 1) % 1000 == 0:
            file.close()
            count = count + 1
            file = open(f'httpx/temp-{count}.txt', 'w')
            
    folder_path = "httpx"
    files = [os.path.join(folder_path, file) for file in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, file))]
    # Create a ThreadPoolExecutor
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit tasks to process each file concurrently
        futures = [executor.submit(process_file, file_path, cursor) for file_path in files]

        num_futures = len(futures)
        with tqdm(total=num_futures) as pbar:
            for _ in as_completed(futures):
                pbar.update(1)
                
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



