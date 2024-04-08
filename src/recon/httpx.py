import os 
import subprocess
import sqlite3
from datetime import datetime
import logging
import shlex
import pandas as pd
import time

# Configure logging
logging.basicConfig(filename='logs/debug.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def run_httpx(database):
    try:
        command = f'httpx -list httpx/{database}.txt -csv -o temp.csv -silent'
        args = shlex.split(command)
        subprocess.run(args, check=True, text=True, stderr=subprocess.DEVNULL)
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
    for database in os.listdir('db'):
        database_name = database.replace('.db', '')
        conn = sqlite3.connect(f'db/{database}')
        cursor = conn.cursor()

        current_date = datetime.now().strftime('%Y-%m-%d')

        # Get all the subdomains that were added today
        cursor.execute(f"SELECT subdomain FROM subdomains WHERE created_at LIKE '%{current_date}%';")

        # Fetch all the results
        results = cursor.fetchall()

        with open(f'httpx/{database_name}.txt', 'w') as file:
            for subdomain in results:
                file.write(subdomain[0] + '\n')

        run_httpx(database_name)

        df = pd.read_csv(f'temp.csv')
        columns = ['status_code', 'webserver', 'host', 'url', 'tech', 'input']

        extracted_columns = df[columns]

        # Write the extracted columns to a new CSV file
        extracted_columns.to_csv(f'httpx/{database_name}.csv', index=False)
        
        for index, row in extracted_columns.iterrows():
            status_code = row['status_code']
            webserver = row['webserver']
            ip = row['host']
            url = row['url']
            technology = row['tech']
            subdomain = row['input']
            
            # Write to database
            cursor.execute('''INSERT OR REPLACE INTO subdomains 
                            (id, subdomain, ip, status_code, web_server, technology, program, updated_at, created_at) 
                            VALUES 
                            ((SELECT id FROM subdomains WHERE subdomain = ?),
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            (SELECT program FROM subdomains WHERE subdomain = ?),
                            DATE('now', 'localtime'),
                            COALESCE((SELECT created_at FROM subdomains WHERE subdomain = ?), DATE('now', 'localtime')))''', 
                            (subdomain, subdomain, ip, status_code, webserver, technology, subdomain, subdomain))
            cursor.connection.commit()

        os.remove('temp.csv')
        os.remove(f'httpx/{database_name}.txt')

        # Close the cursor and connection
        cursor.close()
        conn.close()
        

if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    logging.info(f"HTTPX Execution Time: {end_time - start_time}")



