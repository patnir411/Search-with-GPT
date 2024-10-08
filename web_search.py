import requests
from config import SEARCH_API_KEY, SEARCH_ENGINE_ID

def web_search(query: str, num_results: int = 5) -> list:
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": SEARCH_API_KEY,
        "cx": SEARCH_ENGINE_ID,
        "q": query,
        "num": num_results
    }
    print(f"Web Search: searching {query}")
    response = requests.get(url, params=params)
    results = response.json().get("items", [])
    res = [{"title": item["title"], "link": item["link"], "snippet": item["snippet"]} for item in results]
    links = [{"link": item["link"]} for item in res]
    print(f"Web Search Response: {links}")
    return links