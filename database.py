import sqlite3
from tkinter import messagebox

DB_NAME = "sim_data.db"

import sqlite3
from tkinter import messagebox

DB_NAME = "sim_data.db"

def setup_database():
# ... (function body remains the same as date_time handling is in insert) ...
    # Ensure S3 column and tables exist (implementation remains the same)
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Ensure S3 column exists in 'laps' table
        cursor.execute("PRAGMA table_info(laps)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'sector_3' not in columns:
            try:
                cursor.execute("ALTER TABLE laps ADD COLUMN sector_3 REAL")
            except sqlite3.OperationalError:
                # Table might not exist yet, proceed to creation
                pass
        
        # Table creation is essential, so run it regardless
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY,
                car_model TEXT NOT NULL,
                track_name TEXT NOT NULL,
                date_time TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now')),
                best_lap_time REAL,
                theoretical_lap_time REAL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS laps (
                id INTEGER PRIMARY KEY,
                session_id INTEGER,
                lap_number INTEGER NOT NULL,
                lap_time REAL NOT NULL,
                sector_1 REAL,
                sector_2 REAL,
                sector_3 REAL,
                cuts INTEGER,
                is_valid INTEGER,
                FOREIGN KEY (session_id) REFERENCES sessions (id)
            )
        """)
        conn.commit()
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Failed to initialize database: {e}")
    finally:
        if conn: conn.close()


# MODIFIED FUNCTION SIGNATURE AND IMPLEMENTATION

def save_session_data(raw_data, best_lap_ms, theoretical_ms, all_laps_data, session_datetime):
    """Saves the session summary and all laps (valid and invalid) to the database."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # ... (summary data extraction remains the same) ...
        track = raw_data.get("track", "Unknown Track").replace("ks_", "").replace("-", " ")
        car = raw_data.get("players", [{}])[0].get("car", "Unknown Car").replace("ks_", "").replace("_", " ")

        date_time_to_save = session_datetime if session_datetime else sqlite3.Timestamp.now().isoformat()

        # 1. Insert into sessions table (unchanged)
        cursor.execute("""
            INSERT INTO sessions (car_model, track_name, best_lap_time, theoretical_lap_time, date_time)
            VALUES (?, ?, ?, ?, ?)
        """, (car.title(), track.title(), best_lap_ms, theoretical_ms, date_time_to_save))

        session_id = cursor.lastrowid

        # 2. Insert all laps into laps table
        lap_inserts = []
        for lap in all_laps_data: # LOOPING over ALL laps
            # Safely extract S3, defaulting to None if the array only has 2 elements
            s3_time = lap['sectors'][2] if len(lap['sectors']) > 2 else None

            lap_inserts.append((
                session_id,
                lap['lap_number'],
                lap['time'],
                lap['sectors'][0],
                lap['sectors'][1],
                s3_time,
                lap['cuts'],
                lap['is_valid'] # This column now stores 0 for invalid laps
            ))

        cursor.executemany("""
            INSERT INTO laps (session_id, lap_number, lap_time, sector_1, sector_2, sector_3, cuts, is_valid)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, lap_inserts)

        conn.commit()
        return True

    except sqlite3.Error as e:
        messagebox.showerror("Database Save Error", f"Failed to save session: {e}")
        return False
    finally:
        if conn: conn.close()

# --- Database Reading Functions for Viewer ---

def get_unique_cars_and_tracks():
    """Fetches unique car models and tracks for filtering."""
    cars, tracks = ['All Cars'], ['All Tracks']
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT car_model FROM sessions ORDER BY car_model")
        cars.extend([row[0] for row in cursor.fetchall()])
        cursor.execute("SELECT DISTINCT track_name FROM sessions ORDER BY track_name")
        tracks.extend([row[0] for row in cursor.fetchall()])
    except:
        pass # Return defaults on error
    finally:
        if conn: conn.close()
    return cars, tracks

def get_sessions(car_filter='All Cars', track_filter='All Tracks'):
    """Fetches sessions based on filters."""
    sql = "SELECT id, car_model, track_name, best_lap_time, theoretical_lap_time, date_time FROM sessions WHERE 1=1"
    params = []
    if car_filter != 'All Cars':
        sql += " AND car_model = ?"
        params.append(car_filter)
    if track_filter != 'All Tracks':
        sql += " AND track_name = ?"
        params.append(track_filter)
    sql += " ORDER BY date_time DESC"

    conn = None
    records = []
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(sql, params)
        records = cursor.fetchall()
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Error reading sessions: {e}")
    finally:
        if conn: conn.close()
    return records

def get_laps_for_session(session_id):
    """Fetches all lap details for a given session ID."""
    laps = []
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT lap_number, lap_time, sector_1, sector_2, sector_3, cuts, is_valid
            FROM laps
            WHERE session_id = ?
            ORDER BY lap_number ASC
        """, (session_id,))
        laps = cursor.fetchall()
    except sqlite3.Error:
        pass # Returning an empty list on error is safer
    finally:
        if conn: conn.close()
    return laps

def get_session_count():
    """Gets the total number of sessions for the status bar."""
    count = -1
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sessions")
        count = cursor.fetchone()[0]
    except:
        count = -1
    finally:
        if conn: conn.close()
    return count

def delete_session_by_id(session_id):
    """
    Deletes a session and all associated lap records from the database.
    Returns True on success, False otherwise.
    """
    if not session_id:
        return False
        
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Start transaction
        conn.isolation_level = None # Autocommit off
        cursor.execute("BEGIN")

        # 1. Delete all laps associated with the session
        cursor.execute("DELETE FROM laps WHERE session_id = ?", (session_id,))

        # 2. Delete the session record itself
        cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

        conn.commit()
        return True

    except sqlite3.Error as e:
        if conn: conn.rollback()
        messagebox.showerror("Database Error", f"Failed to delete session {session_id}: {e}")
        return False
    finally:
        if conn: conn.close()