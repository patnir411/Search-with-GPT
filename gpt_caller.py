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
from urllib.parse import urlparse, parse_qs

client = OpenAI(api_key=OPENAI_API_KEY)
ua = UserAgent()

def get_reddit_client():
    return praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent= "python:replitapp:v1.0 (by u/apquestion)"
    )

def num_tokens_from_string(string: str, encoding_name: str = "cl100k_base") -> int:
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string, disallowed_special=()))
    return num_tokens

def scrape_text_from_url(url):
    try:
        if "reddit.com" in url:
            return reddit_search(url)
        else:
            print(f"Manually scraping text from URL: {url}")
            headers = {'User-Agent': ua.random, 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'}
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser').get_text()
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return ""

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
            return f"This appears to be a Reddit URL, but not a specific post. URL: {url}"
    except praw.exceptions.PRAWException as e:
        print(f"Reddit API error: {str(e)}")
        return f"Error accessing Reddit content. Please try again later. URL: {url}"
    except Exception as e:
        print(f"Unexpected error in reddit_search: {str(e)}")
        return f"Unexpected error occurred while processing Reddit content. URL: {url}"

def extract_post_content(reddit, post_id):
    try:
        submission = reddit.submission(id=post_id)

        # Construct the text content
        text = f"Title: {submission.title}\n\n"
        text += f"Author: u/{submission.author.name if submission.author else '[deleted]'}\n"
        text += f"Posted on: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(submission.created_utc))}\n"
        text += f"Score: {submission.score}\n\n"

        if submission.is_self and submission.selftext:
            text += f"Content: {submission.selftext[:500]}...\n\n" if len(submission.selftext) > 500 else f"Content: {submission.selftext}\n\n"
        elif not submission.is_self:
            text += f"Link: {submission.url}\n\n"

        text += "Top Comments:\n"
        submission.comments.replace_more(limit=0)
        for comment in submission.comments.list()[:5]:  # Limit to top 5 comments
            text += f"- u/{comment.author.name if comment.author else '[deleted]'}: {comment.body[:100]}...\n" if len(comment.body) > 100 else f"- u/{comment.author.name if comment.author else '[deleted]'}: {comment.body}\n"

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
            messages=[
                {"role": "system", "content": "Summarize the following information concisely with respect to date and details."},
                {"role": "user", "content": text}
            ]
        ).choices[0].message.content
        summaries.append(summary)

    combined_summary = "\n\n".join(summaries)
    if num_tokens_from_string(combined_summary) > 128000:
        return summarize_results([combined_summary])
    return combined_summary

def web_search_and_summarize(query, num_results=5):
    search_results = web_search(query, num_results)
    scraped_texts = [scrape_text_from_url(result['link']) for result in search_results]
    return summarize_results(scraped_texts)

def gpt_function_call(messages, functions):
    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        functions=functions,
        function_call="auto"
    ).choices[0].message

functions = [{
    "name": "web_search_and_summarize",
    "description": "Search the web for information and summarize the results",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query"},
            "num_results": {"type": "integer", "description": "The number of search results to process"}
        },
        "required": ["query"]
    }
}]

def gpt_call_with_function(user_input):
    current_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    messages = [
        {"role": "system", "content": f"You are a helpful, up-to-date AI assistant. The current date and time is {current_datetime}. Provide concise, accurate answers based on the most recent information available."},
        {"role": "user", "content": user_input}
    ]

    for _ in range(5):
        response = gpt_function_call(messages, functions)

        if response.function_call:
            print(f"Function call args: {response.function_call.arguments}")
            function_args = json.loads(response.function_call.arguments)
            search_summary = web_search_and_summarize(function_args["query"], function_args.get("num_results", 5))
            messages.append({"role": "function", "name": "web_search_and_summarize", "content": search_summary})
        else:
            return response.content

    return "Unable to provide a satisfactory response after multiple attempts."