# gpt_caller.py

from openai import OpenAI
from config import OPENAI_API_KEY
from web_search import web_search
from scraper import scrape_text_from_url
import json
import datetime
import tiktoken

client = OpenAI(api_key=OPENAI_API_KEY)


def num_tokens_from_string(string: str,
                           encoding_name: str = "cl100k_base") -> int:
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string, disallowed_special=()))
    return num_tokens


def summarize_results(scraped_texts):
    summaries = []
    for text in scraped_texts:
        if num_tokens_from_string(text) > 20000:
            text = text[:40000]  # Truncate to avoid token limit
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


def web_search_and_summarize(query, num_results=5):
    search_results = web_search(query, num_results)
    scraped_texts = []
    for result in search_results:
        text = scrape_text_from_url(result['link'])
        if not text.startswith(
            ("Error", "Access forbidden", "Page not found")):
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
            function_args = json.loads(response.function_call.arguments)
            query = function_args["query"]

            if query in prev_queries:
                messages.append({
                    "role":
                    "function",
                    "name":
                    "web_search_and_summarize",
                    "content":
                    "This query has already been searched. Please rephrase or ask a different question."
                })
                continue

            prev_queries.append(query)
            search_summary = web_search_and_summarize(
                query, function_args.get("num_results", 5))

            content = f"Previous web search queries: {prev_queries}\nSummarized results: {search_summary}"
            messages.append({
                "role": "function",
                "name": "web_search_and_summarize",
                "content": content
            })
        else:
            return response.content

    # If we've reached this point, use whatever information we have
    messages.append({
        "role":
        "user",
        "content":
        "Please provide the best answer you can based on the information already gathered, even if it's not complete."
    })
    final_response = gpt_function_call(messages, functions)
    return final_response.content
