from openai import OpenAI
from config import OPENAI_API_KEY
from web_search import web_search
import json
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

ua = UserAgent()

client = OpenAI(api_key=OPENAI_API_KEY)

def gpt_function_call(messages: list, tools: list):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )
    return response.choices[0].message

def scrape_text_from_url(url: str) -> str:
    """Scrapes the text content from a given URL.
    Args:
        url: The URL to scrape.
    Returns:
        The extracted text content, or an empty string if scraping fails.
    """
    try:
        headers = {
            'User-Agent': ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes
        soup = BeautifulSoup(response.content, 'html.parser')
        text = soup.get_text()
        return text
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return ""

def process_gpt_response(response):
    if response.tool_calls:
        tool_call = response.tool_calls[0]
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)  # Use json.loads

        if function_name == "web_search":
            search_results = web_search(function_args["query"], function_args.get("num_results", 5))
            # Scrape text from the top 3 URLs
            scraped_text = [result['snippet'] for result in search_results]
            for i in range(5):
                if i < len(search_results):
                    scraped_text.append(scrape_text_from_url(search_results[i]['link']))

            combined_text = "\n".join(scraped_text)
            summary = summarize_results(combined_text)
            return summary  # Return the summary

    return response.content

tools = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for information",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "The number of search results to return"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

def summarize_results(formatted_results: str) -> str:
    """Summarizes the formatted search results using GPT-4o-mini.

    Args:
        formatted_results: A string containing the formatted search results.

    Returns:
        A string containing the summary generated by GPT-4o-mini.
    """

    messages = [
        {"role": "system", "content": "Summarize the below"},
        {"role": "user", "content": formatted_results}
    ]
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    return response.choices[0].message.content

def gpt_call_with_function(user_input: str) -> str:
    messages = [{"role": "user", "content": user_input}]
    max_iterations = 5  # Set a limit for loop iterations

    for i in range(max_iterations):
        response = gpt_function_call(messages, tools)
        result = process_gpt_response(response)

        if isinstance(result, str):  # If result is a string (no tool calls)
            return result
        elif isinstance(result, list):  # If result is a list (search results)
            # Append the summary to the conversation history 
            messages.append({"role": "tool", "tool_call_id": response.tool_calls[0].id, "name": "web_search", "content": result})
            continue
        else:
            return "Unexpected response format."  # Handle unexpected response types

    return "Reached maximum iterations. Could not fulfill the request."