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
from concurrent.futures import ThreadPoolExecutor

# Constants
MAX_WORKERS = 15

# Configure logging
logging.basicConfig(filename='logs/debug.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def run_httpx(filename):
    try:
        command = f'httpx -list {filename} -csv -asn -threads 250 -silent -stream -rate-limit 300 -retries 0'
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
        futures = [executor.submit(run_httpx, file_path) for file_path in files]


        with tqdm(total=len(futures), desc="Processing") as pbar:
            # Wait for all tasks to complete
            for future in futures:
                results = future.result()  # This will block until each task completes
                csv_data = io.StringIO(results)
                df = pd.read_csv(csv_data)
                columns = ['status_code', 'content_length', 'asn', 'webserver', 'host', 'url', 'tech', 'input']

                extracted_columns = df[columns]

                # Write the extracted columns to a new CSV file
                extracted_columns.to_csv(csv_data, index=False)
                
                for index, row in extracted_columns.iterrows():
                    status_code = row['status_code']
                    webserver = row['webserver']
                    ip = row['host']
                    url = row['url']
                    technology = row['tech']
                    subdomain = row['input']
                    asn = row['asn']
                    content_length = row['content_length']
                    
                    # Write to database
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
                                                        (subdomain, subdomain, ip, asn, status_code, content_length, webserver, technology, subdomain, subdomain, subdomain, subdomain, subdomain, subdomain))
                    cursor.connection.commit()
            pbar.update(1)
    # Close the cursor and connection
    cursor.close()
    conn.close()
        

if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    logging.info(f"HTTPX Execution Time: {end_time - start_time}")



