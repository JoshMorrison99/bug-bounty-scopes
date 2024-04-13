import os 
import subprocess
import logging
import shlex
import sqlite3
import time
import io
from datetime import datetime
from db_operations import create_URL_database, get_cursor

# Configure logging
logging.basicConfig(filename='logs/debug.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def run_katana(filename):
    try:
        command = f'katana -list {filename} -js-crawl -jsluice -crawl-duration 300 -known-files all -headers headers.txt -crawl-scope {filename}'
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


def main():

    conn = sqlite3.connect(f'swarm.db')
    cursor = conn.cursor()

    current_date = datetime.now().strftime('%Y-%m-%d')

    # Get all the subdomains that were added today
    cursor.execute(f"SELECT subdomain FROM subdomains WHERE created_at LIKE '%{current_date}%' AND status_code IS NOT NULL;")

    # Fetch all the results
    results = cursor.fetchall()
    
    with open('temp.txt', 'w') as file:
        for subdomain in results:
            file.write(subdomain[0])

    results = run_katana('temp.txt')

    # Clean up
    os.remove('temp.txt')
    
    # Write to database
    create_URL_database(f"swarm-url.db")
    cursor = get_cursor(f"swarm-url.db")
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
                

if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    logging.info(f"Katana Execution Time: {end_time - start_time}")



