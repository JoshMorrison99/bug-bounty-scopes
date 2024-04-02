import os 
import subprocess
import sqlite3
from datetime import datetime
import logging
import shlex
import pandas as pd

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
            for line in results:
                file.write(line[0] + '\n')

        run_httpx(database_name)

        df = pd.read_csv(f'temp.csv')
        columns = ['status_code', 'content_length', 'webserver', 'host', 'url']

        extracted_columns = df[columns]

        # Write the extracted columns to a new CSV file
        extracted_columns.to_csv(f'httpx/{database_name}.csv', index=False)

        os.remove('temp.csv')
        os.remove(f'httpx/{database_name}.txt')

        # Close the cursor and connection
        cursor.close()
        conn.close()

main()



