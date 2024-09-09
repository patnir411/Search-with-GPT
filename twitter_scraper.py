# twitter_scraper.py
import os
import asyncio
from twikit import Client
from config import X_UN, X_PW
from storage import TweetStorage, UserStorage 
import time

USERNAME = X_UN
PASSWORD = X_PW

# Rate limit constants
GET_USER_TWEETS_LIMIT = 50 
GET_USER_TWEETS_RESET_TIME = 15 * 60  # 15 minutes in seconds

client = Client('en-US')

is_logged_in = False

async def login_to_twitter():
    try:
        if not os.path.exists('cookies.json'):
            print("(x) creating new cookies...")
            await client.login(auth_info_1=X_UN,
                               auth_info_2="flirtanaai@gmail.com",
                               password=X_PW)
            client.save_cookies('cookies.json')
        else:
            print("(x) loading past cookies...")
            client.load_cookies('cookies.json')
        print("Successfully logged in to Twitter.")
        is_logged_in = True
    except Exception as e:
        print(f"Failed to log in to Twitter: {e}")
        is_logged_in = False


async def scrape_twitter_user(username, tweet_storage: TweetStorage, user_storage: UserStorage):
    """Scrapes all tweets from a given Twitter user, respecting rate limits."""
    if is_logged_in:
        print("is logged in!")
    else:
        print("NOT LOGGED IN! LOGGING IN")
        await login_to_twitter()
        print("perhaps logged in...")
    try:
        user = await client.get_user_by_screen_name(username)
        print(f"Scraping @{username}...")
        user_storage.add_user(user)

        tweets = await user.get_tweets('Tweets', count=GET_USER_TWEETS_LIMIT)
        request_count = 1  # Track the number of get_user_tweets requests
        last_reset_time = time.time() # Keep track of the last reset time

        while tweets:
            print(f"Obtained tweet batch {request_count}...")
            for tweet in tweets:
                if tweet.retweeted_tweet:
                    tweet_storage.add_retweet(tweet, user.id)
                else:
                    tweet_storage.add_tweet(tweet, user.id)

            if hasattr(tweets, 'next'):
                # Rate limit check
                if request_count >= GET_USER_TWEETS_LIMIT:
                    current_time = time.time()
                    time_since_reset = current_time - last_reset_time
                    if time_since_reset < GET_USER_TWEETS_RESET_TIME:
                        wait_time = GET_USER_TWEETS_RESET_TIME - time_since_reset
                        print(f"Rate limit reached. Waiting for {wait_time:.2f} seconds...")
                        await asyncio.sleep(wait_time)
                        last_reset_time = time.time() # Update the reset time
                    request_count = 0  # Reset the request count after waiting

                request_count += 1
                await asyncio.sleep(1)  # Additional small delay to be safe
                tweets = await tweets.next() 
            else:
                break 

        print(f"Successfully scraped tweets for @{username}")
    except Exception as e:
        print(f"Error scraping tweets: {e}") 