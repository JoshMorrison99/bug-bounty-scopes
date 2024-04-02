import json
import subprocess
import concurrent.futures
from concurrent.futures import as_completed
import os
from tqdm import tqdm
from datetime import datetime
from db_operations import create_database, get_cursor
import logging
import tldextract

# Configure logging
logging.basicConfig(filename='logs/debug.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
CHUNK_SIZE = 1000

def run_subfinder(url, program):
    try:
        command = ['subfinder', '-all', '-silent', '-d', url, '-rl', '1']
        output = subprocess.check_output(command, text=True, timeout=300)
        return output, program
    except subprocess.TimeoutExpired:
        logging.error(f'Subfinder took longer than 5 minutes and timed-out on {url}')
        return None, program
    except subprocess.CalledProcessError as e:
        logging.error(f'Subfinder command failed with error code {e.returncode}: {e.output}')
        return None, program
    except Exception as e:
        logging.error(f'Subfinder had an error occur on {url}: {e}')
        return None, program

def clean_url(url):

    # Extract only the domain and subdomain
    extracted = tldextract.extract(url)
    subdomain = extracted.subdomain
    domain = extracted.domain
    suffix = extracted.suffix
    cleaned_url = f"{subdomain + '.' if subdomain else ''}{domain}.{suffix}"

    # Remove any http:// or https://
    cleaned_url = cleaned_url.replace('http//:', '')
    cleaned_url = cleaned_url.replace('https//:', '')

    # Remove any slashes /
    cleaned_url = cleaned_url.replace('/:', '')

    # Remove regex based domains: contactallerg(y|ie).uzleuven.be
    # Remove any domain with *: uzleuven.*, swiss-backup*.infomaniak.com
    if('(' not in cleaned_url and ')' not in cleaned_url and '*' not in cleaned_url):
        return cleaned_url
    return None


def main():

    max_workers = 5

    # Loop over all files in the folder
    for file_name in os.listdir('feeds'):
        feed = {}
        subfinder_findings = {}  
        print(f"[INFO] Subfinder {file_name.replace('.json', '')}")
        # Check if the path is a file
        if os.path.isfile(os.path.join('feeds', file_name)):
            with open(f'feeds/{file_name}', 'r') as file:
                feed = json.load(file)
                bb_program = file_name.replace('.json', '')
                create_database(f"db/{bb_program}.db")
                cursor = get_cursor(f"db/{bb_program}.db")
                for program in feed:
                    if 'urls' not in feed[program]:
                        feed[program]['urls'] = {}

                    if(program not in subfinder_findings):
                        subfinder_findings[program] = []

                    for url in feed[program]['in-scope']:
                        if url.startswith('*.'):
                            wildcard_domain = clean_url(url[2:])
                            if(wildcard_domain):
                                wildcard_domain = (wildcard_domain)
                                subfinder_findings[program].append(wildcard_domain)
                                cursor.execute("INSERT OR REPLACE INTO wildcard_domains (wildcard_domain) VALUES (?)", (wildcard_domain,))
                        else:
                            url = clean_url(url)
                            if(url):
                                current_date = datetime.now().strftime('%Y-%m-%d')
                                subdomain = (url, current_date)
                                cursor.execute("INSERT OR IGNORE INTO subdomains (subdomain, created_at) VALUES (?,?)", subdomain)

        # Collect results asynchronously
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for program in subfinder_findings:
                for url in subfinder_findings[program]:
                    futures.append(executor.submit(run_subfinder, url, program))

            num_futures = len(futures)
            with tqdm(total=num_futures) as pbar:
                completed = 0
                for future in as_completed(futures):
                    urls, program = future.result()

                    if(urls):
                        urls = urls.split('\n')
                        for url in urls:
                            if(url):
                                current_date = datetime.now().strftime('%Y-%m-%d')
                                subdomain = (url, current_date)
                                cursor.execute("INSERT OR IGNORE INTO subdomains (subdomain, created_at) VALUES (?,?)", subdomain)
                        cursor.connection.commit()

                    completed += 1
                    pbar.update(1)
    cursor.connection.commit()
    cursor.close()

if __name__ == '__main__':
    main()
