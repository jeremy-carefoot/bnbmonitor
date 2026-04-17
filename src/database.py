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
            search_box TEXT,
            result_ids TEXT
        )
    ''')
    
    # Individual results - shared across searches
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            rating REAL,
            bed_count TEXT,
            room_url TEXT,
            total_price REAL,
            UNIQUE(name, rating, bed_count, room_url, total_price)
        )
    ''')

    # Track notified listings to avoid duplicates
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notified_listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT,
            checkin TEXT,
            checkout TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(room_id, checkin, checkout)
        )
    ''')
    
    conn.commit()
    conn.close()

def is_already_notified(config, room_id, checkin, checkout):
    db_path = get_db_path(config)
    if not os.path.exists(db_path):
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 1 FROM notified_listings 
        WHERE room_id = ? AND checkin = ? AND checkout = ?
    ''', (str(room_id), checkin, checkout))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def mark_as_notified(config, room_id, checkin, checkout):
    db_path = get_db_path(config)
    init_db(config)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO notified_listings (room_id, checkin, checkout)
            VALUES (?, ?, ?)
        ''', (str(room_id), checkin, checkout))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
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
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get result IDs from searches table
    cursor.execute('SELECT result_ids FROM searches WHERE id = ?', (search_id,))
    res = cursor.fetchone()
    
    if not res or not res["result_ids"]:
        conn.close()
        return []

    # Join using the result_ids array
    cursor.execute('''
        SELECT r.name, r.rating, r.bed_count, r.room_url, r.total_price 
        FROM json_each(?) j 
        JOIN results r ON r.id = j.value
    ''', (res["result_ids"],))
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
    
    # Use json_each to join results with searches
    query = '''
        SELECT 
            s.id as search_id, 
            s.timestamp, 
            r.total_price
        FROM searches s
        JOIN json_each(s.result_ids) j
        JOIN results r ON r.id = j.value
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
    init_db(config)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    bnb_url = config["bnb_url"]
    get_total_fn = lambda x: x["price"]["break_down"][-1]["amount"]
    
    result_ids = []
    for item in results:
        rating = item.get("rating", {}).get("value")
        bed_count = ""
        primary_line = item.get("structuredContent", {}).get("primaryLine", [])
        if primary_line:
            bed_count = primary_line[-1].get("body", "")
        
        name = item.get("name")
        room_url = f"{bnb_url}rooms/{item.get('room_id')}"
        total_price = get_total_fn(item)

        # Deduplicate results: Insert if not exists, then get ID
        cursor.execute('''
            INSERT OR IGNORE INTO results (name, rating, bed_count, room_url, total_price)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, rating, bed_count, room_url, total_price))
        
        cursor.execute('''
            SELECT id FROM results 
            WHERE name IS ? AND rating IS ? AND bed_count IS ? AND room_url IS ? AND total_price IS ?
        ''', (name, rating, bed_count, room_url, total_price))
        res_id = cursor.fetchone()[0]
        result_ids.append(res_id)
    
    # Save search with the array of result IDs
    params = config["search_parameters"]
    cursor.execute('''
        INSERT INTO searches (checkin, checkout, adult_count, price_min, price_max, search_box, result_ids)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        params["checkin"],
        params["checkout"],
        params["adult_count"],
        params["price_min"],
        params["price_max"],
        json.dumps(params["search_box"]),
        json.dumps(result_ids)
    ))
    
    conn.commit()
    conn.close()
