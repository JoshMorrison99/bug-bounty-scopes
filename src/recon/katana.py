import os 
import subprocess
import logging
import shlex
import pandas as pd
import time
from db_operations import create_URL_database, get_cursor

# Configure logging
logging.basicConfig(filename='logs/debug.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def run_katana(filename):
    try:
        command = f'katana -list {filename} -js-crawl -crawl-duration 600 -known-files all -headers headers.txt -crawl-scope {filename}'
        args = shlex.split(command)
        results = subprocess.run(args, check=True, text=True, stderr=subprocess.DEVNULL)
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

    # Loop over all the databases and run SQL query to get today's subdomains.
    for file in os.listdir('httpx'):
        filename = file.replace('.csv', '')

        df = pd.read_csv(f'httpx/{file}')
        df['url'].to_csv('temp.txt', index=False, header=False)

        run_katana(filename)

        # Clean up
        os.remove('temp.txt')
        
        # Write to database
        create_URL_database(f"url-db/{filename}.db")
        cursor = get_cursor(f"url-db/{filename}.db")
        with open(f'urls/{filename}-katana.txt') as file:
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



