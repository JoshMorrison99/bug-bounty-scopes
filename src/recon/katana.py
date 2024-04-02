import os 
import subprocess
import logging
import shlex
import pandas as pd

# Configure logging
logging.basicConfig(filename='logs/debug.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def run_katana(filename):
    try:
        command = f'katana -list temp.txt -js-crawl -crawl-duration 600 -known-files all -headers headers.txt -crawl-scope scopes/{filename}-in.txt -crawl-out-scope scopes/{filename}-out.txt -o urls/{filename}-katana.txt'
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
    for file in os.listdir('httpx'):
        filename = file.replace('.csv', '')

        df = pd.read_csv(f'httpx/{file}')
        df['url'].to_csv('temp.txt', index=False, header=False)

        run_katana(filename)

        # Clean up
        os.remove('temp.txt')

main()



