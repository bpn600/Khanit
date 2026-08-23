import sqlite3
from datetime import datetime
import os
from kivy.utils import platform

class KhanitDatabase:
    """Database handler for Khanit calculator history"""
    def __init__(self, db_name='khanit.db'):
        """Initialize database connection and create table if not exists"""
        # Get the appropriate database path based on platform
        self.db_path = self.get_database_path(db_name)
        self.conn = None
        self.cursor = None

    def get_database_path(self, db_name):
        """Get the appropriate writable database path for the current platform"""
        try:
            if platform == 'ios':
                # iOS: Use the app's Documents directory which is writable
                # Get the home directory and construct Documents path
                home = os.path.expanduser('~')
                documents_path = os.path.join(home, 'Documents')

                # Create app-specific folder if it doesn't exist
                app_folder = os.path.join(documents_path, 'KhanitCalculator')

                # Ensure the directory exists
                try:
                    os.makedirs(app_folder, exist_ok=True)
                    # Test if we can write to this path
                    test_file = os.path.join(app_folder, 'test_write.tmp')
                    with open(test_file, 'w') as f:
                        f.write('test')
                    os.remove(test_file)
                    print(f"Successfully created writable directory: {app_folder}")
                    return os.path.join(app_folder, db_name)
                except (OSError, IOError) as e:
                    print(f"Cannot write to Documents directory: {e}")
                    # Fallback to a temporary directory
                    temp_dir = os.path.join(home, 'tmp')
                    os.makedirs(temp_dir, exist_ok=True)
                    return os.path.join(temp_dir, db_name)

            elif platform == 'android':
                # Android: Use the app's private storage which is writable
                # Try multiple possible Android storage locations
                possible_paths = [
                    # App-specific external storage (most reliable)
                    os.path.join('/storage/emulated/0/Android/data',
                                 'org.khanit.calculator', 'files'),
                    # Internal app storage
                    os.path.join(os.environ.get('ANDROID_PRIVATE', ''), 'files'),
                    # Fallback to app's data directory
                    os.path.join(os.path.dirname(__file__), 'data')
                ]

                for path in possible_paths:
                    try:
                        os.makedirs(path, exist_ok=True)
                        # Test if we can write to this path
                        test_file = os.path.join(path, 'test_write.tmp')
                        with open(test_file, 'w') as f:
                            f.write('test')
                        os.remove(test_file)
                        # If successful, use this path
                        app_folder = path
                        print(f"Using Android storage path: {app_folder}")
                        return os.path.join(app_folder, db_name)
                    except (OSError, IOError):
                        continue

                # If all paths fail, use a last resort location
                fallback_path = os.path.join(os.path.dirname(__file__), 'data')
                os.makedirs(fallback_path, exist_ok=True)
                return os.path.join(fallback_path, db_name)

            else:
                # Desktop: Use the script directory
                db_path = os.path.join(os.path.dirname(__file__), db_name)
                # Ensure the directory exists and is writable
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
                return db_path

        except Exception as e:
            print(f"Error setting up database path: {e}")
            # Ultimate fallback - use a temporary directory
            import tempfile
            temp_dir = tempfile.gettempdir()
            return os.path.join(temp_dir, db_name)

    def connect(self):
        """Establish the SQLite database connection."""
        try:
            # Close existing connection.
            if self.conn:
                try:
                    self.conn.close()
                except Exception:
                    pass

                self.conn = None
                self.cursor = None

            # Make sure database directory exists.
            db_dir = os.path.dirname(self.db_path)

            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)

            # Open database.
            self.conn = sqlite3.connect(
                self.db_path,
                timeout=10
            )

            self.conn.execute("PRAGMA foreign_keys = ON")
            self.conn.execute("PRAGMA journal_mode = WAL")
            self.conn.execute("PRAGMA synchronous = NORMAL")

            self.cursor = self.conn.cursor()

            # IMPORTANT:
            # create_table() must NOT call connect().
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS log_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lim_expression TEXT,
                    lim_result TEXT,
                    nep_expression TEXT,
                    nep_result TEXT,
                    eng_expression TEXT,
                    eng_result TEXT,
                    timestamp TEXT
                )
            """)

            self.conn.commit()

            return True

        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            self.conn = None
            self.cursor = None
            return False

    def ensure_connection(self):
        """Ensure database connection is active, reconnect if needed"""
        try:
            # Check if connection exists and is alive
            if self.conn:
                try:
                    # Test connection with a simple query
                    self.cursor.execute('SELECT 1')
                    return True
                except (sqlite3.Error, AttributeError):
                    # Connection is dead, create new one
                    try:
                        self.conn.close()
                    except:
                        pass
                    self.conn = None
                    self.cursor = None

            # Create new connection
            return self.connect()

        except Exception as e:
            print(f"Error ensuring connection: {e}")
            return False

    def create_table(self):
        """Create the history table if it does not exist."""
        try:
            if not self.ensure_connection():
                return False

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS log_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lim_expression TEXT,
                    lim_result TEXT,
                    nep_expression TEXT,
                    nep_result TEXT,
                    eng_expression TEXT,
                    eng_result TEXT,
                    timestamp TEXT
                )
            """)
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error creating table: {e}")
            return False

    def insert_history(self, lim_data, nep_data, eng_data):
        """
        Insert calculation history into database

        Args:
            lim_data: Tuple (expression, result) for Limbu
            nep_data: Tuple (expression, result) for Nepali
            eng_data: Tuple (expression, result) for English
        """
        try:
            if not self.ensure_connection():
                print("Failed to connect to database for insert")
                return False

            # Ensure table exists
            # self.create_table()

            self.cursor.execute('''
                INSERT INTO log_history 
                (lim_expression, lim_result, nep_expression, nep_result, eng_expression, eng_result, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                lim_data[0], lim_data[1],
                nep_data[0], nep_data[1],
                eng_data[0], eng_data[1],
                datetime.now().strftime('%d-%m-%Y | %H:%M:%S')
            ))
            self.conn.commit()
            # print("History inserted successfully")
            return True
        except sqlite3.Error as e:
            print(f"Error inserting history: {e}")
            # Try to reconnect and retry once
            try:
                self.conn = None
                if self.ensure_connection():
                    return self.insert_history(lim_data, nep_data, eng_data)
            except:
                pass
            return False

    def get_all_history(self):
        """Retrieve all history records"""
        try:
            if not self.ensure_connection():
                return []

            self.cursor.execute('''
                SELECT * FROM log_history 
                ORDER BY timestamp DESC
            ''')
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error fetching history: {e}")
            return []

    def get_recent_history(self, limit=10):
        """Get recent history records"""
        try:
            if not self.ensure_connection():
                return []

            self.cursor.execute('''
                SELECT * FROM log_history 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error fetching recent history: {e}")
            return []

    def clear_history(self):
        """Clear all history records"""
        try:
            if not self.ensure_connection():
                return False

            self.cursor.execute('DELETE FROM log_history')
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error clearing history: {e}")
            return False

    def delete_record(self, record_id):
        """Delete a specific record by ID"""
        try:
            if not self.ensure_connection():
                print("Failed to connect to database for delete")
                return False

            self.cursor.execute('DELETE FROM log_history WHERE id = ?', (record_id,))
            self.conn.commit()
            print(f"Record {record_id} deleted successfully")
            return True
        except sqlite3.Error as e:
            print(f"Error deleting record: {e}")
            return False

    def close(self):
        """Close database connection"""
        if self.conn:
            try:
                # Commit any pending changes
                self.conn.commit()
                self.conn.close()
            except:
                pass
            finally:
                self.conn = None
                self.cursor = None

    def __del__(self):
        """Destructor to ensure connection is closed"""
        self.close()