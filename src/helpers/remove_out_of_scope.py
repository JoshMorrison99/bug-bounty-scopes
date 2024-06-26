import os 
import json
import sqlite3
import re
import logging
from tqdm import tqdm

# Configure logging
logging.basicConfig(filename='logs/debug.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    logging.info('Removing out-of-scope subdomains')
    for file_name in os.listdir('feeds'):
        with open(f'feeds/{file_name}', 'r') as file:
            feed = json.load(file)

            out_of_scopes = set()

            for program in feed:
                for _, urls in feed[program]['out-of-scope'].items():
                    if(urls == []):
                        continue
                    for url in urls:
                        regex_url = url.replace('.', r'\.').replace('*', '.*')
                        out_of_scopes.add(regex_url)
                

            # Connect to the SQLite database
            conn = sqlite3.connect(f'swarm.db')
            cursor = conn.cursor()

            # Fetch all URLs from the database
            cursor.execute('SELECT subdomain FROM subdomains')
            urls = cursor.fetchall()

            # Compile regex patterns outside the loop
            compiled_patterns = [re.compile(pattern) for pattern in out_of_scopes]

            # Batch delete operation
            delete_data = [(url_tuple[0],) for url_tuple in tqdm(urls) if any(pattern.match(url_tuple[0]) for pattern in compiled_patterns)]
            cursor.executemany('DELETE FROM subdomains WHERE subdomain=?', delete_data)

            # Commit the changes and close the connection
            conn.commit()

            # Vacuum the database to release unused space and optimize file size
            cursor.execute('VACUUM')

            # Commit the vacuum operation
            conn.commit()

            conn.close()

main()
