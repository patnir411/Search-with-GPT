# storage.py
import sqlite3
import os
from twikit import Tweet


class SQLiteStorage:
    def __init__(self, db_name):
        self.db_name = db_name
        self.conn = None
        self.cursor = None

    def initialize_db(self):
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()

class UserStorage(SQLiteStorage):
    def __init__(self, db_name):
        super().__init__(db_name)
        self.table_name = 'users'
        self.initialize_db()

    def initialize_db(self):
        super().initialize_db()
        self.cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                user_id TEXT PRIMARY KEY,
                screen_name TEXT,
                created_at TEXT
            )
        """
        )
        self.conn.commit()

    def add_user(self, user: Tweet):
        try:
            self.cursor.execute(
                f"""
                INSERT OR REPLACE INTO {self.table_name} (user_id, screen_name, created_at)
                VALUES (?, ?, ?)
            """,
                (user.id, user.screen_name, user.created_at)
            )
            self.conn.commit()
            print(f"Stored user {user.screen_name}")
        except sqlite3.Error as e:
            print(f"Error adding user: {e}")

class TweetStorage(SQLiteStorage):
    def __init__(self, db_name):
        super().__init__(db_name)
        self.tweet_table_name = 'tweets'
        self.retweet_table_name = 'retweets'
        self.initialize_db()

    def initialize_db(self):
        super().initialize_db()
        self.cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.tweet_table_name} (
                tweet_id TEXT PRIMARY KEY,
                user_id TEXT,
                created_at TEXT,
                text TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """
        )
        self.cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.retweet_table_name} (
                retweet_id TEXT PRIMARY KEY,
                original_tweet_id TEXT,
                user_id TEXT,
                retweeted_at TEXT,
                text TEXT,
                FOREIGN KEY (original_tweet_id) REFERENCES tweets(tweet_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """
        )
        self.conn.commit()

    def add_tweet(self, tweet: Tweet, user_id: str):
        try:
            self.cursor.execute(
                f"""
                INSERT OR REPLACE INTO {self.tweet_table_name} (tweet_id, user_id, created_at, text)
                VALUES (?, ?, ?, ?)
            """,
                (tweet.id, user_id, tweet.created_at, tweet.full_text)
            )
            self.conn.commit()
            print(f"Stored tweet {tweet.id}")
        except sqlite3.Error as e:
            print(f"Error adding tweet: {e}")

    def add_retweet(self, tweet: Tweet, user_id: str):
        try:
            retweet = tweet.retweeted_tweet
            self.cursor.execute(
                f"""
                INSERT OR REPLACE INTO {self.retweet_table_name} (retweet_id, original_tweet_id, user_id, retweeted_at, text)
                VALUES (?, ?, ?, ?, ?)
            """,
                (retweet.id, tweet.id, user_id, tweet.created_at, retweet.full_text)
            )
            self.conn.commit()
            print(f"Stored retweet {retweet.id}")
        except sqlite3.Error as e:
            print(f"Error adding retweet: {e}")

    def get_tweets_by_user_id(self, user_id):
        """Retrieves all tweets and retweets for a specific user by user_id."""
        try:
            self.cursor.execute(
                f"""
                SELECT tweet_id, user_id, created_at, text, 'tweet' as type
                FROM {self.tweet_table_name} WHERE user_id = ?
                UNION ALL
                SELECT retweet_id as tweet_id, user_id, retweeted_at as created_at, text, 'retweet' as type
                FROM {self.retweet_table_name} WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id, user_id)
            )
            rows = self.cursor.fetchall()

            # Return a list of dictionaries with an additional 'type' field to distinguish tweets and retweets
            return [
                {
                    "tweet_id": row[0],
                    "user_id": row[1],
                    "created_at": row[2],
                    "text": row[3],
                    "type": row[4],  # 'tweet' or 'retweet'
                }
                for row in rows
            ]
        except sqlite3.Error as e:
            print(f"Error retrieving tweets and retweets: {e}")
            return []