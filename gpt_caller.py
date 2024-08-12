from openai import OpenAI
from config import OPENAI_API_KEY, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET
from web_search import web_search
import json
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import datetime
import tiktoken
import praw
import time
from urllib.parse import urlparse
from requests.exceptions import RequestException
from storage import storage

client = OpenAI(api_key=OPENAI_API_KEY)
ua = UserAgent()


def get_reddit_client():
    return praw.Reddit(client_id=REDDIT_CLIENT_ID,
                       client_secret=REDDIT_CLIENT_SECRET,
                       user_agent="python:replitapp:v1.0 (by u/apquestion)")


def num_tokens_from_string(string: str,
                           encoding_name: str = "cl100k_base") -> int:
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string, disallowed_special=()))
    return num_tokens


def reddit_search(url):
    print(f"Extracting content from Reddit URL: {url}")
    reddit = get_reddit_client()
    parsed_url = urlparse(url)

    try:
        if '/comments/' in parsed_url.path:
            # It's a post URL
            post_id = parsed_url.path.split('/')[4]
            return extract_post_content(reddit, post_id)
        else:
            # It's another type of Reddit URL
            print(
                f"This appears to be a Reddit URL, but not a specific post. URL: {url}"
            )
            return ""
    except praw.exceptions.PRAWException as e:
        print(
            f"Error accessing Reddit content. Please try again later. URL: {url}"
        )
        return ""
    except Exception as e:
        print(
            f"Unexpected error occurred while processing Reddit content. URL: {url}"
        )
        return ""


def extract_post_content(reddit, post_id):
    try:
        submission = reddit.submission(id=post_id)

        # Construct the text content
        text = f"Title: {submission.title}\n\n"
        text += f"Author: u/{submission.author.name if submission.author else '[deleted]'}\n"
        text += f"Posted on: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(submission.created_utc))}\n"
        text += f"Score: {submission.score}\n\n"

        if submission.is_self and submission.selftext:
            text += f"Content: {submission.selftext[:500]}...\n\n" if len(
                submission.selftext
            ) > 500 else f"Content: {submission.selftext}\n\n"
        elif not submission.is_self:
            text += f"Link: {submission.url}\n\n"

        text += "Top Comments:\n"
        submission.comments.replace_more(limit=0)
        for comment in submission.comments.list(
        )[:5]:  # Limit to top 5 comments
            text += f"- u/{comment.author.name if comment.author else '[deleted]'}: {comment.body[:100]}...\n" if len(
                comment.body
            ) > 100 else f"- u/{comment.author.name if comment.author else '[deleted]'}: {comment.body}\n"

        return text

    except praw.exceptions.PRAWException as e:
        print(f"Reddit API error in extract_post_content: {str(e)}")
        return f"Error extracting post content. Post ID: {post_id}"
    except Exception as e:
        print(f"Unexpected error in extract_post_content: {str(e)}")
        return f"Unexpected error occurred while extracting post content. Post ID: {post_id}"


def summarize_results(scraped_texts):
    summaries = []
    for text in scraped_texts:
        if num_tokens_from_string(text) > 20000:
            text = text[:40000]
        summary = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role":
                "system",
                "content":
                "You are an expert detail extractor. Given the following text, extract all relevant details. Be detailed on what's relevant."
            }, {
                "role": "user",
                "content": text
            }]).choices[0].message.content
        summaries.append(summary)

    combined_summary = "\n\n".join(summaries)
    if num_tokens_from_string(combined_summary) > 128000:
        return summarize_results([combined_summary])
    return combined_summary


def handle_scraping_error(url, error):
    if isinstance(error, RequestException):
        if error.response is not None:
            status_code = error.response.status_code
            if status_code == 403:
                return f"Access forbidden (403) for URL: {url}. The website may be blocking automated access."
            elif status_code == 404:
                return f"Page not found (404) for URL: {url}. The content may have been moved or deleted."
            else:
                return f"HTTP error {status_code} occurred while accessing URL: {url}"
        else:
            return f"Network error occurred while accessing URL: {url}. Please check your internet connection."
    else:
        return f"Unexpected error occurred while scraping {url}: {str(error)}"


def scrape_text_from_url(url):
    try:
        if "reddit.com" in url:
            return reddit_search(url)
        else:
            print(f"Manually scraping URL: {url}")
            user_agent = ua.random
            headers = {
                'User-Agent': user_agent,
                'Accept':
                'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Referer': 'https://www.example.com/',
                'Accept-Language': 'en-US,en;q=0.5',
                'Upgrade-Insecure-Requests': '1',
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser').get_text()
    except Exception as e:
        error_message = handle_scraping_error(url, e)
        print(error_message)
        return error_message


def web_search_and_summarize(query, num_results=5):
    search_results = web_search(query, num_results)
    scraped_texts = []
    for result in search_results:
        text = scrape_text_from_url(result['link'])
        if not text.startswith("Error") and not text.startswith(
                "Access forbidden") and not text.startswith("Page not found"):
            scraped_texts.append(text)

    if not scraped_texts:
        return "Unable to retrieve any valid content from the search results."

    return summarize_results(scraped_texts)


def gpt_function_call(messages, functions):
    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        functions=functions,
        function_call="auto").choices[0].message


functions = [{
    "name": "web_search_and_summarize",
    "description":
    "Search the web for information and summarize the result details",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query"
            },
            "num_results": {
                "type": "integer",
                "description": "The number of search results to process"
            }
        },
        "required": ["query"]
    }
}]


def gpt_call_with_function(user_input):
    current_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    messages = [{
        "role":
        "system",
        "content":
        f"You are a helpful, up-to-date AI assistant. The current date and time is {current_datetime}. Provide concise, accurate answers based on the most recent information available. When necessary, you may search the web to retrieve additional and up-to-date information. Ensure you are not repeating the same search query, avoiding redundant queries from those contained in 'Previous web search queries'."
    }, {
        "role": "user",
        "content": user_input
    }]

    prev_queries = []
    for attempt in range(5):
        response = gpt_function_call(messages, functions)

        if response.function_call:
            print(f"Function call args: {response.function_call.arguments}")
            function_args = json.loads(response.function_call.arguments)
            query = function_args["query"]
            prev_queries.append(query)
            search_summary = web_search_and_summarize(
                query, function_args.get("num_results", 5))
            content = f"Previous web search queries: {prev_queries}\nSummarized results: {search_summary}"
            messages.append({
                "role": "function",
                "name": "web_search_and_summarize",
                "content": content
            })
            storage.add(query, search_summary)
        else:
            print("Messages array:", messages)
            return response.content

    # If we've reached this point, use whatever information we have
    messages.append({
        "role":
        "user",
        "content":
        "Please provide the best answer you can based on the information already gathered, even if it's not complete."
    })
    final_response = gpt_function_call(messages, functions)
    print("Messages array:", messages)
    return final_response.content
