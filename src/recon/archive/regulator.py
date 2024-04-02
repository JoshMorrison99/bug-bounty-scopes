import subprocess
import concurrent.futures
from concurrent.futures import as_completed
import os
import tldextract
from datetime import datetime
import requests
import logging
from datetime import date
from tqdm import tqdm, trange
import shutil
from db_operations import get_cursor

# Configure logging
logging.basicConfig(filename='logs/debug.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
MAX_WORKERS = 15
cursor = None

def run_regulator(url_file, domain):
    try:
        command = ['python3', '../regulator/main.py', '-t', domain, '-f', url_file, '-o', f'rules/{domain}.rules']
        subprocess.run(command, check=True, text=True, timeout=300, stderr=subprocess.DEVNULL)
        return f'rules/{domain}.rules', domain
    except subprocess.TimeoutExpired:
        logging.error(f'Regulator for domain {domain} timed out after 5 minutes.')
        return None, domain
    except subprocess.CalledProcessError as e:
        logging.error(f'Regulator encountered an error for domain {domain}: {e}')
        return None, domain
    except Exception as ex:
        logging.error(f'Unexpected error occurred for domain {domain}: {ex}')
        return None, domain

def run_shuffledns(rules, domain):
    try:
        command = f'shuffledns -d {domain} -l {rules} -r resolvers.txt'
        stdout = subprocess.check_output(command, shell=True, text=True, timeout=300, stderr=subprocess.DEVNULL)
        urls = stdout.split('\n')
        return urls
    except subprocess.TimeoutExpired:
        # Handle timeout
        logging.error("ShuffleDNS took longer than 5 minutes and timed out.")
        return None
    except subprocess.CalledProcessError as e:
        # Handle subprocess errors
        logging.error(f"ShuffleDNS encountered an error for domain {domain}.")
        logging.error(f"Command failed with return code {e.returncode}: {e.output}")
        return None
    except Exception as e:
        # Handle other unexpected errors
        logging.error(f"ShuffleDNS had an unexpected error for domain {domain}.")
        logging.exception(e)  # Log the full exception traceback
        return None

def process_regulator_result(future):
    global cursor

    rules, domain = future.result()
    if(rules):
        urls = run_shuffledns(rules, domain)
        if(urls):
            for url in urls:
                if(url):
                    current_date = datetime.now().strftime('%Y-%m-%d')
                    subdomain = (url, current_date)
                    cursor.execute("INSERT OR IGNORE INTO subdomains (subdomain, created_at) VALUES (?,?)", subdomain)
            cursor.connection.commit()

        if os.path.exists(f'{domain}.rules'):
            os.remove(f'{domain}.rules')

def main():

    global cursor

    # delete the rules folder
    if os.path.exists('rules'):
        shutil.rmtree('rules')

    # delete the regulator folder
    if os.path.exists('regulator'):
        shutil.rmtree('regulator')

    os.makedirs('rules', exist_ok=True)
    os.makedirs('regulator', exist_ok=True)

    for bb_program in os.listdir(f'db'):
        bb_program_db = bb_program.replace('.db', '').replace('', '')
        # Get all the wildcard domain
        cursor = get_cursor(f'db/{bb_program_db}.db')
        cursor.execute("SELECT wildcard_domain FROM wildcard_domains WHERE wildcard_domain LIKE '%.%'")
        wildcard_domains = cursor.fetchall()

        # For each wildcard domain, get all the subdomains from the database in order to run regulator on it.
        for wildcard_domain in wildcard_domains:
            cursor.execute("SELECT subdomain FROM subdomains WHERE subdomain LIKE ?", ('%' + wildcard_domain[0],))
            subdomains = cursor.fetchall()

            with open(f'regulator/{wildcard_domain[0]}.txt', 'w') as file:
                for subdomain in subdomains:
                    file.write(subdomain[0] + '\n')
        

        # Loop over all files in the folder
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            for domain in os.listdir('regulator'):
                domain_cleaned = domain.replace('.txt', '')
                future = executor.submit(run_regulator, f'regulator/{domain}', domain_cleaned)
                future.add_done_callback(process_regulator_result)      
                

        logging.info(f'Subdomain Permutations on {bb_program} Finshed.')
        

main()
