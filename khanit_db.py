import sqlite3
from datetime import datetime
import os
from kivy.utils import platform

class KhanitDatabase:
    def __init__(self, db_name='khanit.db'):
        self.db_path = self.get_database_path(db_name)
        self.conn = None
        self.cursor = None

    def get_database_path(self, db_name):
        try:
            if platform == 'ios':
                home = os.path.expanduser('~')
                documents_path = os.path.join(home, 'Documents')
                app_folder = os.path.join(documents_path, 'KhanitCalculator')
                try:
                    os.makedirs(app_folder, exist_ok=True)
                    test_file = os.path.join(app_folder, 'test_write.tmp')
                    with open(test_file, 'w') as f:
                        f.write('test')
                    os.remove(test_file)
                    print(f"Successfully created writable directory: {app_folder}")
                    return os.path.join(app_folder, db_name)
                except (OSError, IOError) as e:
                    print(f"Cannot write to Documents directory: {e}")
                    temp_dir = os.path.join(home, 'tmp')
                    os.makedirs(temp_dir, exist_ok=True)
                    return os.path.join(temp_dir, db_name)
            elif platform == 'android':
                possible_paths = [
                    os.path.join('/storage/emulated/0/Android/data',
                                 'org.khanit.calculator', 'files'),
                    os.path.join(os.environ.get('ANDROID_PRIVATE', ''), 'files'),
                    os.path.join(os.path.dirname(__file__), 'data')
                ]
                for path in possible_paths:
                    try:
                        os.makedirs(path, exist_ok=True)
                        test_file = os.path.join(path, 'test_write.tmp')
                        with open(test_file, 'w') as f:
                            f.write('test')
                        os.remove(test_file)
                        app_folder = path
                        print(f"Using Android storage path: {app_folder}")
                        return os.path.join(app_folder, db_name)
                    except (OSError, IOError):
                        continue
                fallback_path = os.path.join(os.path.dirname(__file__), 'data')
                os.makedirs(fallback_path, exist_ok=True)
                return os.path.join(fallback_path, db_name)
            else:
                db_path = os.path.join(os.path.dirname(__file__), db_name)
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
                return db_path
        except Exception as e:
            print(f"Error setting up database path: {e}")
            # Ultimate fallback - use a temporary directory
            import tempfile
            temp_dir = tempfile.gettempdir()
            return os.path.join(temp_dir, db_name)

    def connect(self):
        try:
            if self.conn:
                try:
                    self.conn.close()
                except Exception:
                    pass
                self.conn = None
                self.cursor = None
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            self.conn = sqlite3.connect(self.db_path, timeout=10)
            self.conn.execute("PRAGMA foreign_keys = ON")
            self.conn.execute("PRAGMA journal_mode = WAL")
            self.conn.execute("PRAGMA synchronous = NORMAL")
            self.cursor = self.conn.cursor()
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
        try:
            if self.conn:
                try:
                    self.cursor.execute('SELECT 1')
                    return True
                except (sqlite3.Error, AttributeError):
                    try:
                        self.conn.close()
                    except:
                        pass
                    self.conn = None
                    self.cursor = None
            return self.connect()
        except Exception as e:
            print(f"Error ensuring connection: {e}")
            return False

    def create_table(self):
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
        try:
            if not self.ensure_connection():
                print("Failed to connect to database for insert")
                return False
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
            return True
        except sqlite3.Error as e:
            print(f"Error inserting history: {e}")
            try:
                self.conn = None
                if self.ensure_connection():
                    return self.insert_history(lim_data, nep_data, eng_data)
            except:
                pass
            return False

    def get_all_history(self):
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
        if self.conn:
            try:
                self.conn.commit()
                self.conn.close()
            except:
                pass
            finally:
                self.conn = None
                self.cursor = None

    def __del__(self):
        self.close()