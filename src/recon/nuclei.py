import os 
import subprocess
import logging
import shlex
import pandas as pd
import time

# Configure logging
logging.basicConfig(filename='logs/debug.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def run_nuclei(filename):
    try:
        command = f'nuclei -list {filename} -templates nuclei-templates -header headers.txt -rate-limit 20 -headless -stats -scan-strategy host-spray'
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

    # Loop over all the databases and run SQL query to get today's subdomains.
    for file in os.listdir('urls'):
        run_nuclei(f'urls/{file}')

if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    logging.info(f"Nuclei Execution Time: {end_time - start_time}")



