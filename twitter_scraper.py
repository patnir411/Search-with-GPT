import os
from twikit import Client
from config import X_UN, X_PW

USERNAME = X_UN
PASSWORD = X_PW

client = Client('en-US')

async def login_to_twitter():
  try:
      if not os.path.exists('cookies.json'):
          print("(x) creating new cookies...")
          await client.login(
              auth_info_1=USERNAME,
              password=PASSWORD
          )
          client.save_cookies('cookies.json')
      else:
          print("(x) loading past cookies...")
          client.load_cookies('cookies.json')
      print("Successfully logged in to Twitter.")
  except Exception as e:
      print(f"Failed to log in to Twitter: {e}")

async def scrape_twitter_user(username, num=25):
  try:
      user = await client.get_user_by_screen_name(username)
      tweets = await user.get_tweets('Tweets', count=num)
      return tweets
  except Exception as e:
      print(f"Error scraping tweets: {e}")
      return []