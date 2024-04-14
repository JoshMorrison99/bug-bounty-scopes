import os 
import subprocess
import logging
import shlex
import sqlite3
import time
import io
from tqdm import tqdm
from datetime import datetime
from db_operations import create_URL_database, get_cursor
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(filename='logs/debug.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
MAX_WORKERS = 3

def run_katana(filename):
    try:
        command = f'katana -list {filename} -js-crawl -jsluice -crawl-duration 600 -known-files all -headers headers.txt -crawl-scope {filename}'
        args = shlex.split(command)
        results = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
    results = run_katana(file_path)
    file = io.StringIO(results)
    for url in file:
        cursor.execute('''INSERT OR REPLACE INTO urls 
                        (id, url, updated_at, created_at) 
                        VALUES 
                        ((SELECT id FROM urls WHERE url = ?),
                        ?,
                        DATE('now', 'localtime'),
                        COALESCE((SELECT created_at FROM urls WHERE url = ?), DATE('now', 'localtime')))''', 
                        (url, url, url))
    cursor.connection.commit()

def main():

    conn = sqlite3.connect(f'swarm.db')
    cursor = conn.cursor()

    current_date = datetime.now().strftime('%Y-%m-%d')

    # Get all the subdomains that were added today
    cursor.execute(f"SELECT subdomain FROM subdomains WHERE created_at LIKE '%{current_date}%' AND status_code IS NOT NULL;")

    # Fetch all the results
    results = cursor.fetchall()
    
    count = 0
    file = open(f'katana/temp-{count}.txt', 'w')
    for index, subdomain in enumerate(results):
        file.write(subdomain[0] + '\n')
        if (index + 1) % 50 == 0:
            file.close()
            count = count + 1
            file = open(f'katana/temp-{count}.txt', 'w')
            
    # Write to database
    create_URL_database(f"swarm-url.db")
    cursor = get_cursor(f"swarm-url.db")
    
    folder_path = "katana"
    files = [os.path.join(folder_path, file) for file in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, file))]
    
                
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
    logging.info(f"Katana Execution Time: {end_time - start_time}")



