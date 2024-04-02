import logging
import requests

# Configure logging
logging.basicConfig(filename='logs/debug.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_latest_resolvers():
    response = requests.get('https://raw.githubusercontent.com/trickest/resolvers/main/resolvers.txt')

    # Check if the request was successful
    if response.status_code == 200:
        # Open a file in write mode and write the content of the response to it
        with open('resolvers.txt', 'w') as file:
            file.write(response.text)
        logging.info("Content written to resolvers.txt successfully.")
    else:
        logging.error("Failed to fetch resolvers.txt from the URL.")
        
get_latest_resolvers()