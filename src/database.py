import sqlite3
import os
import json

def get_db_path(config):
    return config.get("database_file", "bnb_monitor.db")

def init_db(config):
    db_path = get_db_path(config)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Searches metadata
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            checkin TEXT,
            checkout TEXT,
            adult_count INTEGER,
            price_min REAL,
            price_max REAL,
            search_box TEXT
        )
    ''')
    
    # Individual results
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            search_id INTEGER,
            name TEXT,
            rating REAL,
            bed_count TEXT,
            room_url TEXT,
            total_price REAL,
            FOREIGN KEY (search_id) REFERENCES searches (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def list_searches(config):
    db_path = get_db_path(config)
    if not os.path.exists(db_path):
        print("Database does not exist yet.")
        return []
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT id, timestamp, checkin, checkout, adult_count, price_min, price_max FROM searches ORDER BY timestamp ASC')
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_results_by_search_id(config, search_id):
    db_path = get_db_path(config)
    if not os.path.exists(db_path):
        return []
    
    conn = sqlite3.connect(db_path)
    # Return as list of dicts to match scraper output format
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT name, rating, bed_count, room_url, total_price FROM results WHERE search_id = ?', (search_id,))
    rows = cursor.fetchall()
    conn.close()
    
    return rows

def get_all_results_with_metadata(config):
    db_path = get_db_path(config)
    if not os.path.exists(db_path):
        return []
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    query = '''
        SELECT 
            s.id as search_id, 
            s.timestamp, 
            r.total_price
        FROM searches s
        JOIN results r ON s.id = r.search_id
        ORDER BY s.timestamp ASC
    '''
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return rows

def reset_db(config):
    db_path = get_db_path(config)
    if os.path.exists(db_path):
        os.remove(db_path)
    init_db(config)
    print("Database has been reset.")

def save_search_results(config, results):
    db_path = get_db_path(config)
    init_db(config)  # Ensure tables exist
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    params = config["search_parameters"]
    cursor.execute('''
        INSERT INTO searches (checkin, checkout, adult_count, price_min, price_max, search_box)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        params["checkin"],
        params["checkout"],
        params["adult_count"],
        params["price_min"],
        params["price_max"],
        json.dumps(params["search_box"])
    ))
    
    search_id = cursor.lastrowid
    
    # Extract total price logic from results
    get_total_fn = lambda x: x["price"]["break_down"][-1]["amount"]
    bnb_url = config["bnb_url"]

    for item in results:
        # Some items might have missing ratings or other fields
        rating = item.get("rating", {}).get("value")
        bed_count = ""
        primary_line = item.get("structuredContent", {}).get("primaryLine", [])
        if primary_line:
            bed_count = primary_line[-1].get("body", "")

        cursor.execute('''
            INSERT INTO results (search_id, name, rating, bed_count, room_url, total_price)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            search_id,
            item.get("name"),
            rating,
            bed_count,
            f"{bnb_url}rooms/{item.get('room_id')}",
            get_total_fn(item)
        ))
    
    conn.commit()
    conn.close()
