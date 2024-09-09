from openai import OpenAI
from config import OPENAI_API_KEY
from scraper import scrape_text_from_url
import json
import sqlite3
import datetime
import tiktoken
from twitter_scraper import scrape_twitter_user
from storage import TweetStorage, UserStorage
from web_search import web_search

client = OpenAI(api_key=OPENAI_API_KEY)

def num_tokens_from_string(string: str, encoding_name: str = "cl100k_base") -> int:
    encoding = tiktoken.get_encoding(encoding_name)
    return len(encoding.encode(string, disallowed_special=()))

def answer_query_for_tweets(tweets, query):
    """Summarizes a list of tweets based on a given query."""
    # Access the 'text' field in the dictionaries
    tweet_text = "\n\n".join([tweet['text'] for tweet in tweets])
    summary = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "system",
            "content": f"You are a friendly assistant. Use the tweets as examples and for your context. Answer the query: '{query}'."
        }, {
            "role": "user",
            "content": tweet_text
        }]
    ).choices[0].message.content
    return summary

def summarize_results(scraped_texts):
    summaries = []
    for text in scraped_texts:
        if num_tokens_from_string(text) > 20000:
            text = text[:40000]  # Truncate to avoid token limit
        summary = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "system",
                "content": "You are an expert detail extractor. Given the following text, extract all relevant details. Be detailed on what's relevant."
            }, {
                "role": "user",
                "content": text
            }]
        ).choices[0].message.content
        summaries.append(summary)

    combined_summary = "\n\n".join(summaries)
    if num_tokens_from_string(combined_summary) > 128000:
        return summarize_results([combined_summary])
    return combined_summary

def web_search_and_summarize(query, num_results=5):
    search_results = web_search(query, num_results)
    scraped_texts = []
    for result in search_results:
        text = scrape_text_from_url(result['link'])
        if not text.startswith(("Error", "Access forbidden", "Page not found")):
            scraped_texts.append(text)

    if not scraped_texts:
        return "Unable to retrieve any valid content from the search results."

    return summarize_results(scraped_texts)

def gpt_function_call(messages, functions):
    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        functions=functions,
        function_call="auto"
    ).choices[0].message

# Define the functions that GPT can call
functions = [{
    "name": "scrape_twitter_user",
    "description": "Scrape tweets from a Twitter user and store them in the database. **Only use this function if the user explicitly requests to 'scrape' tweets** from a specific Twitter user. This will gather the most recent tweets from the user's timeline.",
    "parameters": {
        "type": "object",
        "properties": {
            "username": {
                "type": "string",
                "description": "The Twitter username to scrape tweets from."
            }
        },
        "required": ["username"]
    }
}, {
    "name": "get_tweets_and_query_function_call",
    "description": "Retrieve tweets from the database for a specific Twitter user and answer a query regarding those tweets. **Use this function whenever the user mentions Twitter or tweets but does not specifically ask to 'scrape'.** This will use existing tweets stored in the database.",
    "parameters": {
        "type": "object",
        "properties": {
            "username": {
                "type": "string",
                "description": "The Twitter username whose tweets will be retrieved from the database."
            },
            "query": {
                "type": "string",
                "description": "A detailed query based on the user's tweets. For example, 'Create an example of 10 tweets based on these.'"
            }
        },
        "required": ["username", "query"]
    }
}, {
    "name": "web_search_and_summarize",
    "description": "Search the web for information and summarize the result details. **Use this function to gather and summarize information from the web based on a specific search query.**",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query."
            },
            "num_results": {
                "type": "integer",
                "description": "The number of search results to process."
            }
        },
        "required": ["query"]
    }
}]

async def scrape_twitter_user_function_call(username, tweet_storage, user_storage):
    """Function to scrape a Twitter user's tweets and store them."""
    await scrape_twitter_user(username, tweet_storage, user_storage)
    return f"Scraped and stored tweets for user @{username}."

def get_tweets_and_query_function_call(username, query, tweet_storage, user_storage):
    """Function to get a users tweets and answer a query regarding it."""
    print(f"query={query}")
    try:
        # Get the user_id from the username using the user_storage
        print(f"Getting user_id for username: {username}")
        user_storage.cursor.execute(
            f"""
            SELECT user_id FROM {user_storage.table_name} WHERE screen_name = ?
            """,
            (username,)
        )
        result = user_storage.cursor.fetchone()

        if result is None:
            return f"No user found with username @{username}"

        user_id = result[0]
        print(f"Obtained user_id: {user_id}")

        # Retrieve the tweets using the user_id
        tweets = tweet_storage.get_tweets_by_user_id(user_id)
        response = answer_query_for_tweets(tweets, query)
        return response
    except sqlite3.Error as e:
        return f"Error retrieving tweets and retweets: {e}"

def web_search_and_summarize_function_call(query, num_results=5):
    """Function to perform a web search and summarize the results."""
    return web_search_and_summarize(query, num_results)

async def gpt_call_with_function(user_input, tweet_storage, user_storage):
    current_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    messages = [{
        "role": "system",
        "content": f"You are a helpful, up-to-date AI assistant. The current date and time is {current_datetime}. Provide concise, accurate answers based on the most recent information available. You can also perform actions such as scraping Twitter, answering queries given a users tweets, or performing web searches."
    }, {
        "role": "user",
        "content": user_input
    }]

    response = gpt_function_call(messages, functions)

    if response.function_call:
        function_name = response.function_call.name
        function_args = json.loads(response.function_call.arguments)

        if function_name == "scrape_twitter_user":
            response = await scrape_twitter_user_function_call(
                function_args["username"], tweet_storage, user_storage
            )
            return response
        elif function_name == "get_tweets_and_query_function_call":
            return get_tweets_and_query_function_call(
                function_args["username"], function_args["query"], tweet_storage, user_storage
            )
        elif function_name == "web_search_and_summarize":
            return web_search_and_summarize_function_call(
                function_args["query"], function_args.get("num_results", 5)
            )

    return response.content