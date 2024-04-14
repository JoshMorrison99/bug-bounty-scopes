import re
from datetime import timedelta
import subprocess

def normalize(url: str) -> set:
    '''Takes in a scope written by the program manager and returns a list of normalized domains'''
    normalized_urls = set()
    DOMAIN_REGEX = '^(\*\.|[a-z0-9-]+\.)+[a-z]{2,}$'

    # Case 1: Make domain lowercase
    url = url.lower()

    # Case 2: Remove http:// and https:// from domain
    url = url.replace('http://', '').replace('https://', '')

    # Case 3: Remove whitespace
    url = url.replace('\t', '').replace(' ', '')

    # Case 4: Separate scope with commas. Example: *.buddypress.org,bbpress.org,profiles.wordpress.org
    comma_urls = url.split(',')
    for url in comma_urls:
        normalized_urls.add(url)

    # Case 5: Separate Regex based url scope. Example: (online|portal).vfsevisa.com or [online|portal].vfsevisa.com
    if(url.startswith('(') or url.startswith('[')):
        components = url.split('|')
        domain = url.split(')')[-1]
        domain = url.split(']')[-1]
        for component in components:
            component = component.replace('(', '').replace(')', '').replace('[', '').replace(']', '')
            normalized_urls.add(component + domain)

    # Case 6: Separate Regex based url scope. Example: *.doctolib.(fr|com) or *.doctolib.[fr|com]
    if(url.endswith(')') or url.endswith(']')):
        components = url.split('|')
        domain = url.split('(')[0]
        domain = url.split('[')[0] 
        for component in components:
            component = component.replace('(', '').replace(')', '').replace('[', '').replace(']', '')
            normalized_urls.add(domain + component)

    normalized_urls_ret = set()
    for url in normalized_urls:
        if(re.match(DOMAIN_REGEX, url)):
            normalized_urls_ret.add(url)

    return normalized_urls_ret

def notify(tool, elapsed_time, message):
    """
    Takes in the tool used, the elapsed time in seconds and a message to
    send to the notify tool that will send a Discord Webhook message in the format - HH:MM:SS
    """
    
    elapsed_time_timedelta = timedelta(seconds=elapsed_time)
    hours = int(elapsed_time_timedelta.total_seconds() // 3600)
    minutes = int((elapsed_time_timedelta.total_seconds() // 60) % 60)
    seconds = int(elapsed_time_timedelta.total_seconds() % 60)
    
    p1 = subprocess.Popen(['echo',f"{tool} Execution Time: {hours}:{minutes}:{seconds} - {message}"], stdout=subprocess.PIPE)
    subprocess.run(['notify'], stdin=p1.stdout)
    
    