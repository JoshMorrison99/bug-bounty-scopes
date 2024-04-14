import os 
import subprocess
import logging
import shlex
import pandas as pd
import time
import sqlite3
from datetime import datetime
from helpers import notify

# Configure logging
logging.basicConfig(filename='logs/debug.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def run_nuclei(filename):
    try:
        command = f'nuclei -list {filename} -templates nuclei-templates -dast -header headers.txt -rate-limit 20 -headless -stats -scan-strategy host-spray'
        args = shlex.split(command)
        subprocess.run(args, check=True, text=True)
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
    
    conn = sqlite3.connect(f'swarm-url.db')
    cursor = conn.cursor()

    current_date = datetime.now().strftime('%Y-%m-%d')

    # Get all the subdomains that were added today
    cursor.execute(f"SELECT url FROM urls WHERE created_at LIKE '%{current_date}%' AND url LIKE '%?%';")

    # Fetch all the results
    results = cursor.fetchall()
    
    with open('temp.txt', 'w') as file:
        for url in results:
            file.write(url[0] + '\n')

    run_nuclei('temp.txt')

if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    notify("Nuclei", end_time - start_time)
    logging.info(f"Nuclei Execution Time: {end_time - start_time}")



