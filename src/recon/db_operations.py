import sqlite3

def create_database(db_name):
    conn = sqlite3.connect(db_name, check_same_thread=False)
    cursor = conn.cursor()

    # Create subdomain table
    cursor.execute('''CREATE TABLE IF NOT EXISTS subdomains
                  (id INTEGER PRIMARY KEY, 
                   subdomain TEXT, 
                   created_at DATE DEFAULT (DATE('now', 'localtime')),
                   UNIQUE(subdomain))''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS wildcard_domains
                  (id INTEGER PRIMARY KEY, 
                   wildcard_domain TEXT UNIQUE)''')
    
    # Create indexes
    cursor.execute('''CREATE INDEX IF NOT EXISTS subdomain_idx ON subdomains (subdomain)''')
    
    conn.commit()
    print(f"SQLite database '{db_name}' created successfully.")

def create_connection(db_name):
    conn = sqlite3.connect(db_name, check_same_thread=False)
    return conn

def create_cursor(conn):
    return conn.cursor()

def get_cursor(db_name):
    conn = create_connection(db_name)
    return create_cursor(conn)
