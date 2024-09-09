import asyncio
from storage import TweetStorage, UserStorage
from gpt_caller import gpt_call_with_function


async def main():
    print("Welcome to the GPT API caller with Twitter scraping and web search capability!")

    # Initialize database connection
    tweet_storage = TweetStorage('twitter.db')
    user_storage = UserStorage('twitter.db')

    print("Type 'exit' to quit the program.")

    while True:
        user_input = input("\nEnter your query (e.g., 'scrape @username', 'answer query on tweets for @username', or 'web search <query>'): ")

        if user_input.lower() == 'exit':
            print("Thank you for using the program. Goodbye!")
            break

        response = await gpt_call_with_function(user_input, tweet_storage, user_storage)
        print("\nGPT Response:")
        print(response)


if __name__ == "__main__":
    asyncio.run(main())