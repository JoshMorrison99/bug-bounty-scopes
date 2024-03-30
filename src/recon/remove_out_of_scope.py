import os 
import json
import sqlite3
import re
import logging

# Configure logging
logging.basicConfig(filename='logs/debug.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    logging.info('Removing out-of-scope subdomains')
    for file_name in os.listdir('feeds'):
        with open(f'feeds/{file_name}', 'r') as file:
            feed = json.load(file)

            out_of_scopes = set()

            for program in feed:
                for url in feed[program]['out-of-scope']:
                    out_of_scopes.add(url.replace('.', r'\.').replace('*', '.*'))

            # Connect to the SQLite database
            conn = sqlite3.connect(f'db/{file_name.replace(".json", "")}.db')
            cursor = conn.cursor()

            # Fetch all URLs from the database
            cursor.execute('SELECT subdomain FROM subdomains')
            urls = cursor.fetchall()

            # Filter out URLs that match any of the regex patterns
            filtered_urls = set()
            for url_tuple in urls:
                url = url_tuple[0]  # Extract the URL from the tuple
                should_include = True  # Assume the URL should be included initially
                
                for pattern in out_of_scopes:
                    if re.match(pattern, url):
                        should_include = False  # Set to False if the URL matches any pattern
                        break  # No need to check further once a match is found
                
                if should_include == False:
                    filtered_urls.add(url)  # Add the URL to the filtered list if it should be included

            # Delete filtered URLs from the database
            logging.info(f'Removing {len(filtered_urls)} out-of-scope subdomains from {file_name.replace(".json", "")}')
            for url in filtered_urls:
                cursor.execute('DELETE FROM subdomains WHERE subdomain=?', (url,))

            # Commit the changes and close the connection
            conn.commit()

            # Vacuum the database to release unused space and optimize file size
            cursor.execute('VACUUM')

            # Commit the vacuum operation
            conn.commit()

            conn.close()

main()