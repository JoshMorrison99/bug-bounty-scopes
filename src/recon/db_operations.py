import sqlite3
from datetime import datetime

def create_database(db_name):
    conn = sqlite3.connect(db_name, check_same_thread=False)
    cursor = conn.cursor()

    # Create subdomain table
    cursor.execute('''CREATE TABLE IF NOT EXISTS subdomains
                  (id INTEGER PRIMARY KEY, 
                   subdomain TEXT,
                   ip TEXT DEFAULT NULL,
                   asn TEXT DEFAULT NULL,
                   status_code INTEGER DEFAULT NULL,
                   content_length INTEGER DEFAULT NULL,
                   web_server TEXT DEFAULT NULL,
                   technology TEXT DEFAULT NULL,
                   program TEXT DEFAULT NULL,
                   recon_source TEXT DEFAULT NULL,
                   public TEXT DEFAULT NULL,
                   vdp TEXT DEFAULT NULL,
                   platform TEXT DEFAULT NULL,
                   updated_at DATE DEFAULT (DATE('now', 'localtime')),
                   created_at DATE DEFAULT (DATE('now', 'localtime')),
                   UNIQUE(subdomain))''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS wildcard_domains
                  (id INTEGER PRIMARY KEY, 
                  wildcard_domain TEXT UNIQUE)''')
    
    # Create indexes
    cursor.execute('''CREATE INDEX IF NOT EXISTS subdomain_idx ON subdomains (subdomain)''')
    
    conn.commit()
    print(f"SQLite database {db_name} created successfully.")
    
def create_URL_database(db_name):
    conn = sqlite3.connect(db_name, check_same_thread=False)
    cursor = conn.cursor()

    # Create subdomain table
    cursor.execute('''CREATE TABLE IF NOT EXISTS urls
                  (id INTEGER PRIMARY KEY, 
                   url TEXT,
                   updated_at DATE DEFAULT (DATE('now', 'localtime')),
                   created_at DATE DEFAULT (DATE('now', 'localtime')),
                   UNIQUE(url))''')
    
    # Create indexes
    cursor.execute('''CREATE INDEX IF NOT EXISTS url_idx ON urls (url)''')
    
    conn.commit()
    print(f"SQLite database {db_name} created successfully.")

def create_connection(db_name):
    conn = sqlite3.connect(db_name, check_same_thread=False)
    return conn

def create_cursor(conn):
    return conn.cursor()

def get_cursor(db_name):
    conn = create_connection(db_name)
    return create_cursor(conn)

def get_new_subdomains(tool):
    """query to get the number of newly found subdomains by the tool specified"""
    
    conn = sqlite3.connect(f'swarm.db')
    cursor = conn.cursor()

    current_date = datetime.now().strftime('%Y-%m-%d')

    # Get all the subdomains that were added today
    cursor.execute(f"SELECT subdomain FROM subdomains WHERE created_at LIKE '%{current_date}%' AND recon_source LIKE '%{tool}%';")

    # Fetch all the results
    results = cursor.fetchall()
    return len(results)

def get_new_urls():
    """query to get the number of newly found urls"""
    
    conn = sqlite3.connect(f'swarm-urls.db')
    cursor = conn.cursor()

    current_date = datetime.now().strftime('%Y-%m-%d')

    # Get all the subdomains that were added today
    cursor.execute(f"SELECT subdomain FROM subdomains WHERE created_at LIKE '%{current_date}%';")

    # Fetch all the results
    results = cursor.fetchall()
    return len(results)

def get_resolved_subdomains():
    """query to get the number of newly found subdomains that have been resolved"""
    
    conn = sqlite3.connect(f'swarm.db')
    cursor = conn.cursor()

    current_date = datetime.now().strftime('%Y-%m-%d')

    # Get all the subdomains that were added today
    cursor.execute(f"SELECT subdomain FROM subdomains WHERE created_at LIKE '%{current_date}%' AND status_code IS NOT NULL;")

    # Fetch all the results
    results = cursor.fetchall()
    return len(results)

    
    
    