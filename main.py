# main.py
import asyncio
from storage import TweetStorage, UserStorage
from twitter_scraper import login_to_twitter, scrape_twitter_user 
from scraper import scrape_website, scrape_domain
from gpt_caller import gpt_call_with_function


async def main():
    print("Welcome to the GPT API caller with Twitter scraping capability!")

    # Initialize database connection 
    tweet_storage = TweetStorage('twitter.db')
    user_storage = UserStorage('twitter.db')
    

    # await login_to_twitter()

    print("Type 'exit' to quit the program.")

    while True:
        user_input = input("\nEnter your query (or 'scrape @username' to scrape tweets): ")

        if user_input.lower() == 'exit':
            print("Thank you for using the program. Goodbye!")
            break

        if user_input.lower().startswith('scrape @'):
            username = user_input.split('@')[1]
            await scrape_twitter_user(username, tweet_storage, user_storage)
        else:
            response = gpt_call_with_function(user_input)
            print("\nGPT Response:")
            print(response)


if __name__ == "__main__":
    asyncio.run(main())