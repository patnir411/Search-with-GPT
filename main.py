from gpt_caller import gpt_call_with_function
from storage import storage
import asyncio
from twitter_scraper import login_to_twitter, scrape_twitter_user

async def main():
    print("Welcome to the GPT API caller with Twitter scraping capability!")
    print("---CURRENT STORAGE CONTENTS---")
    for key in storage.list_all():
        print(f"Deleting key: {key} with value {storage.get(key)}")
        storage.delete(key)
    print("---STORAGE IS RESET---")
    await login_to_twitter()

    print("Type 'exit' to quit the program.")

    while True:
        user_input = input("\nEnter your query (or 'scrape @username' to scrape tweets): ")

        if user_input.lower() == 'exit':
            print("Thank you for using the program. Goodbye!")
            break

        if user_input.lower().startswith('scrape @'):
            username = user_input.split('@')[1]
            tweets = await scrape_twitter_user(username)
            print(f"\nScraped {len(tweets)} tweets from @{username}:")
            count = 0
            for tweet in tweets:
                print(f"tweet no. {count} - {tweet.text}")
                count += 1
        else:
            response = gpt_call_with_function(user_input)
            print("\nGPT Response:")
            print(response)

if __name__ == "__main__":
    asyncio.run(main())