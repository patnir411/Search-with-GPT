# scraper.py

import trafilatura
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import praw
from urllib.parse import urlparse
from config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET
import time

ua = UserAgent()

def get_reddit_client():
    return praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent="python:replitapp:v1.0 (by u/apquestion)"
    )

def reddit_search(url):
    print(f"Extracting content from Reddit URL: {url}")
    reddit = get_reddit_client()
    parsed_url = urlparse(url)
    try:
        if '/comments/' in parsed_url.path:
            post_id = parsed_url.path.split('/')[4]
            return extract_post_content(reddit, post_id)
        else:
            print(f"This appears to be a Reddit URL, but not a specific post. URL: {url}")
            return ""
    except praw.exceptions.PRAWException as e:
        print(f"Error accessing Reddit content. Please try again later. URL: {url}")
        return ""
    except Exception as e:
        print(f"Unexpected error occurred while processing Reddit content. URL: {url}")
        return ""

def extract_post_content(reddit, post_id):
    try:
        submission = reddit.submission(id=post_id)
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
        for comment in submission.comments.list()[:5]:
            text += f"- u/{comment.author.name if comment.author else '[deleted]'}: {comment.body[:100]}...\n" if len(comment.body) > 100 else f"- u/{comment.author.name if comment.author else '[deleted]'}: {comment.body}\n"

        return text
    except praw.exceptions.PRAWException as e:
        print(f"Reddit API error in extract_post_content: {str(e)}")
        return f"Error extracting post content. Post ID: {post_id}"
    except Exception as e:
        print(f"Unexpected error in extract_post_content: {str(e)}")
        return f"Unexpected error occurred while extracting post content. Post ID: {post_id}"

def handle_scraping_error(url, error):
    if isinstance(error, requests.RequestException):
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
            print(f"Scraping URL using Trafilatura: {url}")
            downloaded = trafilatura.fetch_url(url)
            if downloaded is None:
                return f"Failed to download content from URL: {url}"

            content = trafilatura.extract(downloaded)
            if content is None:
                return f"Failed to extract content from URL: {url}"

            return content
    except Exception as e:
        error_message = handle_scraping_error(url, e)
        print(error_message)
        return error_message



def scrape_website(url):
    print(f"Scraping website: {url}")

    try:
        # Download the webpage
        downloaded = trafilatura.fetch_url(url)

        if downloaded is None:
            print(f"Failed to download the webpage: {url}")
            return None

        # Extract the main content
        content = trafilatura.extract(downloaded)

        if content is None:
            print(f"Failed to extract content from: {url}")
            return None

        # Extract metadata
        metadata = trafilatura.extract_metadata(downloaded)

        # Combine metadata and content
        result = {
            'url': url,
            'title': metadata.get('title', ''),
            'author': metadata.get('author', ''),
            'date': metadata.get('date', ''),
            'content': content
        }

        print(f"Successfully scraped: {url}")
        return result

    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return None

def scrape_domain(domain, max_pages=10):
    base_url = f"https://{domain}"
    visited = set()
    to_visit = [base_url]
    results = []

    while to_visit and len(visited) < max_pages:
        url = to_visit.pop(0)
        if url in visited:
            continue

        visited.add(url)
        result = scrape_website(url)

        if result:
            results.append(result)

            # Extract links from the content and add them to to_visit
            links = trafilatura.extract_links(result['content'])
            for link in links:
                parsed = urlparse(link)
                if parsed.netloc == domain and link not in visited:
                    to_visit.append(link)

    print(f"Finished scraping domain: {domain}. Scraped {len(results)} pages.")
    return results