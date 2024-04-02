import subprocess
import concurrent.futures
from concurrent.futures import as_completed
import os
import logging
import shutil
import shlex
from db_operations import get_cursor

# Configure logging
logging.basicConfig(filename='logs/debug.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
MAX_WORKERS = 15
cursor = None

def run_alterx(domain, program):
    cleaned_domain = domain.split('/')[-1]
    try:
        print(domain)
        out_file = f"rules/{cleaned_domain}"
        command = f"alterx -l {domain} -o {out_file}"
        args = shlex.split(command)
        subprocess.run(args, check=True, text=True, timeout=300)
        return out_file, cleaned_domain, program
    except subprocess.TimeoutExpired:
        logging.error(f'Alterx for domain {program} timed out after 5 minutes.')
        return None, cleaned_domain, program
    except subprocess.CalledProcessError as e:
        logging.error(f'Alterx encountered an error for domain {program}: {e}')
        return None, cleaned_domain, program
    except Exception as ex:
        logging.error(f'Alterx error occurred for domain {program}: {ex}')
        return None, cleaned_domain, program

def run_shuffledns(rules, domain, program):
    try:
        command = f'shuffledns -d {domain} -l {rules} -r resolvers.txt'
        stdout = subprocess.check_output(command, shell=True, text=True, timeout=600, stderr=subprocess.DEVNULL)
        urls = stdout.split('\n')
        return urls, program
    except subprocess.TimeoutExpired:
        # Handle timeout
        logging.error("ShuffleDNS took longer than 10 minutes and timed out.")
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

def process_alterx_result(future):
    global cursor

    rules, domain, program = future.result()
    if(rules):
        subdomains, program = run_shuffledns(rules, domain, program)
        if(subdomains):
            for subdomain in subdomains:
                if(subdomain):
                    cursor.execute('''INSERT OR REPLACE INTO subdomains 
                                                (id, subdomain, ip, status_code, web_server, technology, program, updated_at, created_at) 
                                                VALUES 
                                                ((SELECT id FROM subdomains WHERE subdomain = ?),
                                                ?,
                                                ?,
                                                ?,
                                                ?,
                                                NULL,
                                                ?,
                                                DATE('now', 'localtime'),
                                                COALESCE((SELECT created_at FROM subdomains WHERE subdomain = ?), DATE('now', 'localtime')))''', 
                                                (subdomain, subdomain, None, None, None, program, subdomain))
            cursor.connection.commit()

def main():

    global cursor

    # delete the permutations folder
    if os.path.exists('rules'):
        shutil.rmtree('rules')

    os.makedirs('rules', exist_ok=True)
    
    # delete the alterx folder
    if os.path.exists('alterx'):
        shutil.rmtree('alterx')

    os.makedirs('alterx', exist_ok=True)

    for bb_program in os.listdir(f'db'):
        bb_program_db = bb_program.replace('.db', '').replace('', '')
        # Get all the wildcard domain
        cursor = get_cursor(f'db/{bb_program_db}.db')
        cursor.execute("SELECT wildcard_domain FROM wildcard_domains")
        wildcard_domains = cursor.fetchall()

        # For each wildcard domain, get all the subdomains from the database in order to run alterx on it.
        for wildcard_domain in wildcard_domains:
            wildcard_cleaned = wildcard_domain[0].replace('*.', '')
            cursor.execute("SELECT subdomain, program FROM subdomains WHERE subdomain LIKE ?", ('%' + wildcard_cleaned,))
            subdomains = cursor.fetchall()
            
            mapping = {}
            for subdomain in subdomains:
                program = subdomain[1]
                if(program not in mapping):
                    mapping[program] = []
                mapping[program].append(subdomain[0])
                
            for program in mapping:
                os.makedirs(f'alterx/{program}', exist_ok=True) 
                with open(f'alterx/{program}/{wildcard_cleaned}.txt', 'w') as file:
                    for subdomain in mapping[program]:
                        file.write(subdomain + '\n')
        

        # Loop over all files in the folder
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            for program in os.listdir('alterx'):
                for domain in os.listdir(f'alterx/{program}'):
                    future = executor.submit(run_alterx, f'alterx/{program}/{domain}', program)
                    future.add_done_callback(process_alterx_result)      
                

        logging.info(f'Subdomain Permutations on {bb_program} Finshed.')
        

main()
