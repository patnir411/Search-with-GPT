# storage.py
import sqlite3
import os

class SQLiteStorage:
    def __init__(self, db_name='web_content.db', table_name='web_content'):
        self.db_name = db_name
        self.table_name = table_name
        self.conn = None
        self.cursor = None
        self.initialize_db()

    def initialize_db(self):
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        self.cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                url TEXT PRIMARY KEY,
                content TEXT
            )
        ''')
        self.conn.commit()

    def add(self, url, content):
        try:
            self.cursor.execute(f"INSERT OR REPLACE INTO {self.table_name} (url, content) VALUES (?, ?)", (url, content))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error adding content: {e}")
            return False

    def get(self, url):
        try:
            self.cursor.execute(f"SELECT content FROM {self.table_name} WHERE url = ?", (url,))
            result = self.cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            print(f"Error retrieving content: {e}")
            return None

    def delete(self, url):
        try:
            self.cursor.execute(f"DELETE FROM {self.table_name} WHERE url = ?", (url,))
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error deleting content: {e}")

    def list_all(self):
        try:
            self.cursor.execute(f"SELECT url FROM {self.table_name}")
            return [row[0] for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error listing all URLs: {e}")
            return []

    def list_with_prefix(self, prefix):
        try:
            self.cursor.execute(f"SELECT url FROM {self.table_name} WHERE url LIKE ?", (f"{prefix}%",))
            return [row[0] for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error listing URLs with prefix: {e}")
            return []

    def clear_all(self):
        try:
            self.cursor.execute(f"DELETE FROM {self.table_name}")
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error clearing all content: {e}")

    def __del__(self):
        if self.conn:
            self.conn.close()

storage = SQLiteStorage()